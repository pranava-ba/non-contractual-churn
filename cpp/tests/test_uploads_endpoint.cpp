#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <filesystem>
#include <functional>
#include <memory>
#include <string>

#include "pareto_nbd/db.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"

// Exercises the real POST /uploads handler logic end to end: an HttpRequest in, a Postgres
// `jobs` row and a Redis queue entry out.
//
// api_main.cpp is a standalone executable's main() (not part of the amortized_inference
// library unit_tests links against), so this file duplicates its handler logic exactly --
// same as test_api_smoke.cpp duplicated the /healthz handler -- as a plain callable, rather
// than registering it with drogon::app() and driving it over a live HttpClient connection.
//
// That's a deliberate deviation from the plan's brief (which used drogon::HttpClient against
// a listener on 127.0.0.1:18081): drogon::app() is a process-wide singleton, and this test
// binary's test_api_smoke.cpp already runs one full addListener+run()+quit() cycle on it. A
// second cycle is not supported -- confirmed empirically two different ways: calling run()
// a second time within this file alone segfaulted, and in the full-suite run order (after
// test_api_smoke.cpp's cycle already completed) it instead hit a trantor FATAL, "EventLoop
// cannot be moved when running". Since test_api_smoke.cpp isn't in this task's touched-files
// list, the fix here is to never start a second drogon::app() listener/event loop at all:
// calling the handler directly with a constructed HttpRequestPtr exercises the exact same
// validate -> store -> insert -> enqueue code path. This is safe because every step inside
// the handler (storage->Put, ingest_csv, db->execSqlSync, EnqueueJob) is itself synchronous
// (db.cpp/queue.cpp block on a std::future internally), and because DbClient/RedisClient run
// their own internal I/O threads independent of drogon::app()'s main loop -- proven already
// by test_db.cpp and test_queue.cpp, which exercise Postgres/Redis without ever starting
// drogon::app() at all.

namespace {

using UploadsHandler =
    std::function<void(const drogon::HttpRequestPtr&,
                        std::function<void(const drogon::HttpResponsePtr&)>&&)>;

// Drogon's HttpResponse::newHttpJsonResponse(...) takes a JsonCpp Json::Value, a different
// JSON library from the nlohmann::json this project uses everywhere else. Building the
// response this way -- a plain string body with the JSON content type set explicitly --
// keeps this test on the same JSON library as api_main.cpp.
drogon::HttpResponsePtr JsonResponse(const nlohmann::json& body, drogon::HttpStatusCode code) {
    auto resp = drogon::HttpResponse::newHttpResponse();
    resp->setStatusCode(code);
    resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
    resp->setBody(body.dump());
    return resp;
}

// Mirrors cpp/src/api_main.cpp's POST /uploads handler exactly (validate via ingest_csv,
// store under a server-generated key, insert a `jobs` row, enqueue in Redis).
UploadsHandler MakeUploadsHandler(std::shared_ptr<pareto_nbd::UploadStorage> storage,
                                   drogon::orm::DbClientPtr db,
                                   drogon::nosql::RedisClientPtr redis) {
    return [storage, db, redis](
               const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
        std::string body(req->getBody());
        if (body.empty()) {
            callback(JsonResponse({{"error", "empty request body"}}, drogon::k400BadRequest));
            return;
        }

        // Server-generated key, never derived from the request body or any client-supplied
        // header -- this matters because Task 3's review flagged path-traversal risk in
        // UploadStorage if a key were ever attacker-influenced, and this handler is the
        // first real caller of storage->Put.
        std::string key = "uploads/" + drogon::utils::getUuid() + ".csv";
        storage->Put(key, body);

        try {
            pareto_nbd::ingest_csv(storage->GetPath(key));
        } catch (const pareto_nbd::IngestError& e) {
            callback(
                JsonResponse({{"error", std::string(e.what())}}, drogon::k400BadRequest));
            return;
        }

        auto rows = db->execSqlSync(
            "INSERT INTO jobs (business_id, status, upload_path) "
            "VALUES ($1::uuid, 'queued', $2) RETURNING id",
            pareto_nbd::kDefaultBusinessId, key);
        std::string job_id = rows[0]["id"].as<std::string>();

        pareto_nbd::EnqueueJob(redis, job_id);

        callback(JsonResponse({{"job_id", job_id}}, drogon::k200OK));
    };
}

// Builds a POST /uploads request with the given raw body and invokes handler with it
// synchronously, returning whatever response the callback received. Safe to treat as
// synchronous because every step inside MakeUploadsHandler's lambda blocks on completion
// before returning (see the file comment above) -- the callback always fires before
// handler() returns, so `response` is populated by the time this function returns it.
drogon::HttpResponsePtr CallUploadsHandler(const UploadsHandler& handler,
                                            const std::string& csv_body) {
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads");
    req->setBody(csv_body);

    drogon::HttpResponsePtr response;
    handler(req, [&response](const drogon::HttpResponsePtr& resp) { response = resp; });
    REQUIRE(response != nullptr);
    return response;
}

}  // namespace

TEST_CASE("POST /uploads rejects a CSV with a missing required column", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto tmp_dir = std::filesystem::temp_directory_path() / "pareto_nbd_uploads_test";
    auto storage = std::make_shared<pareto_nbd::LocalDiskStorage>(tmp_dir.string());
    auto handler = MakeUploadsHandler(storage, db, redis);

    auto response =
        CallUploadsHandler(handler, "customer_id,amount\nA,10.0\n");  // no transaction_date

    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["error"].get<std::string>().find("transaction_date") != std::string::npos);
}

TEST_CASE("POST /uploads accepts a valid CSV and returns a job id", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto tmp_dir = std::filesystem::temp_directory_path() / "pareto_nbd_uploads_test";
    auto storage = std::make_shared<pareto_nbd::LocalDiskStorage>(tmp_dir.string());
    auto handler = MakeUploadsHandler(storage, db, redis);

    auto response = CallUploadsHandler(
        handler, "customer_id,transaction_date,amount\nA,2024-01-01,10.0\nA,2024-01-08,5.0\n");

    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body.contains("job_id"));
    std::string job_id = body["job_id"].get<std::string>();

    // the job row exists with status queued...
    auto rows = db->execSqlSync("SELECT status FROM jobs WHERE id = $1::uuid", job_id);
    REQUIRE(rows.size() == 1);
    REQUIRE(rows[0]["status"].as<std::string>() == "queued");

    // ...and the same id was actually pushed onto the Redis queue (not just that
    // EnqueueJob didn't throw).
    auto dequeued = pareto_nbd::DequeueJob(redis, 2);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == job_id);
}
