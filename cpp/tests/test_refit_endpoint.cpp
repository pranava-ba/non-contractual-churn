#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>
#include <string>
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "test_server_fixture.hpp"

namespace {
drogon::HttpResponsePtr PostRefit(const std::string& id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/jobs/" + id + "/refit");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}
std::string InsertJob(drogon::orm::DbClientPtr db, const std::string& status) {
    return db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, $2, 'uploads/x.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId, status)[0]["id"].as<std::string>();
}
}  // namespace

TEST_CASE("POST /jobs/{id}/refit queues an mcmc job linked to the source", "[api][refit]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    std::string src = InsertJob(db, "done");

    auto resp = PostRefit(src);
    if (resp->getStatusCode() == drogon::k503ServiceUnavailable) { SKIP("Redis not reachable"); }
    REQUIRE(resp->getStatusCode() == drogon::k200OK);
    std::string new_id = nlohmann::json::parse(resp->getBody())["job_id"];
    REQUIRE(new_id != src);

    auto row = db->execSqlSync(
        "SELECT status, fit_mode, source_job_id::text AS src, upload_path FROM jobs WHERE id=$1::uuid", new_id);
    REQUIRE(row[0]["status"].as<std::string>() == "queued");
    REQUIRE(row[0]["fit_mode"].as<std::string>() == "mcmc");
    REQUIRE(row[0]["src"].as<std::string>() == src);
    REQUIRE(row[0]["upload_path"].as<std::string>() == "uploads/x.csv");

    // The new job was pushed onto the test queue. Consume it so it can't leak to later tests.
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    auto dequeued = pareto_nbd::DequeueJob(redis, 2, pareto_nbd::kTestJobQueueKey);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == new_id);
}

TEST_CASE("POST /jobs/{id}/refit rejects bad, unknown and unfinished jobs", "[api][refit]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    REQUIRE(PostRefit("not-a-uuid")->getStatusCode() == drogon::k400BadRequest);
    REQUIRE(PostRefit("00000000-0000-0000-0000-000000000099")->getStatusCode() == drogon::k404NotFound);
    for (const char* st : {"queued", "running", "failed"}) {
        REQUIRE(PostRefit(InsertJob(db, st))->getStatusCode() == drogon::k409Conflict);
    }
}
