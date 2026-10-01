#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <string>

#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "test_server_fixture.hpp"

// Exercises the real POST /uploads handler end to end over genuine HTTP: an HTTP request in,
// a Postgres `jobs` row and a Redis queue entry out. Drives the request against the single
// shared drogon::app() instance test_server_fixture.cpp's Catch2 global listener starts once
// for this whole test binary -- that fixture already called pareto_nbd::RegisterApiRoutes, so
// /uploads is already registered with its own storage/db/redis clients.
//
// Earlier versions of this file called a hand-duplicated copy of the handler directly as a
// plain callable, because a second drogon::app() addListener/run()/quit() cycle in this
// process (on top of test_api_smoke.cpp's) wasn't safe -- confirmed empirically to either
// segfault or hit a trantor FATAL depending on test ordering. Task 6.5's shared-server fixture
// fixes that for the whole binary, so this file now does what the original plan intended: a
// real drogon::HttpClient request against a live listener, with zero duplicated handler logic.

namespace {

drogon::HttpResponsePtr PostUpload(const std::string& csv_body) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads");
    req->setBody(csv_body);
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

}  // namespace

TEST_CASE("POST /uploads rejects a CSV with a missing required column", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto response = PostUpload("customer_id,amount\nA,10.0\n");  // no transaction_date

    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["error"].get<std::string>().find("transaction_date") != std::string::npos);
}

TEST_CASE("POST /uploads accepts a valid CSV and returns a job id", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto response = PostUpload(
        "customer_id,transaction_date,amount\nA,2024-01-01,10.0\nA,2024-01-08,5.0\n");

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
