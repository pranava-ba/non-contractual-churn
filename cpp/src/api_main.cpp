#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <memory>
#include <string>

#include "pareto_nbd/db.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"

namespace {

// Drogon's HttpResponse::newHttpJsonResponse(...) takes a JsonCpp Json::Value, a different
// JSON library from the nlohmann::json this project uses everywhere else (ingest.cpp,
// tests). Building the response this way -- a plain string body with the JSON content type
// set explicitly -- keeps every handler on one JSON library instead of mixing two.
drogon::HttpResponsePtr JsonResponse(const nlohmann::json& body, drogon::HttpStatusCode code) {
    auto resp = drogon::HttpResponse::newHttpResponse();
    resp->setStatusCode(code);
    resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
    resp->setBody(body.dump());
    return resp;
}

}  // namespace

int main() {
    drogon::app().addListener("0.0.0.0", 8080);

    drogon::app().registerHandler(
        "/healthz",
        [](const drogon::HttpRequestPtr&,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("ok");
            callback(resp);
        },
        {drogon::Get});

    // POST /uploads: the entire request body IS the raw CSV file (no multipart/form-data
    // parsing in this MVP -- that's a Phase-5 frontend-integration concern if the browser's
    // file input ever needs it, not blocking this endpoint's core logic).
    //
    // Flow: validate synchronously via ingest_csv's LoadRawTable path so a bad upload never
    // even reaches the job queue (spec Sec6) -> store the raw bytes under a fresh
    // server-generated key (never derived from the request body or any client-supplied
    // header -- Task 3's review flagged path-traversal risk in UploadStorage if a key were
    // ever attacker-influenced, and this handler is the first real caller of storage->Put)
    // -> insert a `jobs` row (status='queued') -> enqueue the job id in Redis for the worker
    // (Task 6) to pick up -> return the job id.
    //
    // ingest_csv is deliberately called twice across this phase's full flow -- once here
    // (validation only, result discarded) and once for real in the worker. Parsing a CSV is
    // cheap relative to the AmortizedModel/Gamma-Gamma stages, and keeping validation
    // synchronous in the request path matters more than saving one parse pass.
    static auto storage = std::make_shared<pareto_nbd::LocalDiskStorage>("./data/uploads");
    static auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    static auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);

    drogon::app().registerHandler(
        "/uploads",
        [](const drogon::HttpRequestPtr& req,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            std::string body(req->getBody());
            if (body.empty()) {
                callback(
                    JsonResponse({{"error", "empty request body"}}, drogon::k400BadRequest));
                return;
            }

            // Server-generated key -- the only caller-controlled input is the raw CSV bytes
            // stored *at* this key, never the key itself.
            std::string key = "uploads/" + drogon::utils::getUuid() + ".csv";
            storage->Put(key, body);

            try {
                pareto_nbd::ingest_csv(storage->GetPath(key));
            } catch (const pareto_nbd::IngestError& e) {
                callback(JsonResponse({{"error", std::string(e.what())}},
                                       drogon::k400BadRequest));
                return;
            }

            auto rows = db->execSqlSync(
                "INSERT INTO jobs (business_id, status, upload_path) "
                "VALUES ($1::uuid, 'queued', $2) RETURNING id",
                pareto_nbd::kDefaultBusinessId, key);
            std::string job_id = rows[0]["id"].as<std::string>();

            pareto_nbd::EnqueueJob(redis, job_id);

            callback(JsonResponse({{"job_id", job_id}}, drogon::k200OK));
        },
        {drogon::Post});

    drogon::app().run();
    return 0;
}
