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

drogon::HttpResponsePtr PostUpload(const std::string& csv_body, const std::string& query = "") {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads" + query);
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
    // The shared fixture registers /uploads against kTestJobQueueKey (never the production
    // queue a live worker consumes), so that is where this job id must have landed.
    auto dequeued = pareto_nbd::DequeueJob(redis, 2, pareto_nbd::kTestJobQueueKey);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == job_id);
}

TEST_CASE("POST /uploads accepts a CSV larger than Drogon's 1 MB default body limit",
          "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    // 60k rows (~1.9 MB) -- the size the final review saw rejected with 413 before the body
    // limit was raised (api_main.cpp / test_server_fixture.cpp's setClientMaxBodySize).
    std::string csv = "customer_id,transaction_date,amount\n";
    for (int i = 0; i < 60000; ++i) {
        csv += "cust-" + std::to_string(i % 20000) + ",2024-0" + std::to_string(1 + i % 9) +
               "-1" + std::to_string(i % 10) + ",12.50\n";
    }
    REQUIRE(csv.size() > 1024 * 1024);

    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads");
    req->setBody(csv);
    auto [result, response] = client->sendRequest(req, 30.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    std::string job_id = nlohmann::json::parse(response->getBody())["job_id"].get<std::string>();

    // Drain this job from the test queue so it can't be mistaken for a later test's job.
    auto dequeued = pareto_nbd::DequeueJob(redis, 2, pareto_nbd::kTestJobQueueKey);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == job_id);
}

namespace {

// Deletes the test queue key on construction and destruction, so a test that deliberately
// breaks it (below) can never leave it broken for later tests or later runs.
struct TestQueueKeyReset {
    explicit TestQueueKeyReset(drogon::nosql::RedisClientPtr r) : redis(std::move(r)) { Del(); }
    ~TestQueueKeyReset() {
        try {
            Del();
        } catch (...) {
        }
    }
    void Del() {
        redis->execCommandSync<std::string>(
            [](const drogon::nosql::RedisResult& r) { return r.getStringForDisplaying(); },
            "DEL %s", pareto_nbd::kTestJobQueueKey.c_str());
    }
    drogon::nosql::RedisClientPtr redis;
};

}  // namespace

TEST_CASE("POST /uploads returns 503 and marks the job failed when enqueueing fails",
          "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id;
    {
        TestQueueKeyReset reset(redis);
        // Turn the fixture's queue key into a plain string: the handler's RPUSH then gets a
        // real WRONGTYPE error reply from Redis -- the same failure path a dropped Redis
        // connection takes -- without having to stop the shared Redis server.
        redis->execCommandSync<std::string>(
            [](const drogon::nosql::RedisResult& r) { return r.getStringForDisplaying(); },
            "SET %s %s", pareto_nbd::kTestJobQueueKey.c_str(), "not-a-list");

        auto response = PostUpload(
            "customer_id,transaction_date,amount\nA,2024-01-01,10.0\nA,2024-01-08,5.0\n");
        REQUIRE(response->getStatusCode() == drogon::k503ServiceUnavailable);
        auto body = nlohmann::json::parse(response->getBody());
        REQUIRE(body.contains("error"));
        REQUIRE(body.contains("job_id"));
        job_id = body["job_id"].get<std::string>();
    }

    // The already-inserted jobs row is marked failed with a reason, not left 'queued' forever.
    auto rows =
        db->execSqlSync("SELECT status, error_reason FROM jobs WHERE id = $1::uuid", job_id);
    REQUIRE(rows.size() == 1);
    REQUIRE(rows[0]["status"].as<std::string>() == "failed");
    REQUIRE_FALSE(rows[0]["error_reason"].isNull());
}

TEST_CASE("POST /uploads stores the requested fit_mode and defaults to auto", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    const std::string csv =
        "customer_id,transaction_date,amount\n"
        "A,2024-01-01,10.0\n"
        "A,2024-01-08,5.0\n";

    auto fast = PostUpload(csv, "?fit_mode=fast");
    REQUIRE(fast->getStatusCode() == drogon::k200OK);
    auto r1 = db->execSqlSync("SELECT fit_mode FROM jobs WHERE id = $1::uuid",
                              nlohmann::json::parse(fast->getBody())["job_id"].get<std::string>());
    REQUIRE(r1[0]["fit_mode"].as<std::string>() == "fast");

    auto dflt = PostUpload(csv);
    REQUIRE(dflt->getStatusCode() == drogon::k200OK);
    auto r2 = db->execSqlSync("SELECT fit_mode FROM jobs WHERE id = $1::uuid",
                              nlohmann::json::parse(dflt->getBody())["job_id"].get<std::string>());
    REQUIRE(r2[0]["fit_mode"].as<std::string>() == "auto");

    // Drain the two ids this test pushed, so they don't leak to tests that dequeue next.
    REQUIRE(pareto_nbd::DequeueJob(redis, 2, pareto_nbd::kTestJobQueueKey).has_value());
    REQUIRE(pareto_nbd::DequeueJob(redis, 2, pareto_nbd::kTestJobQueueKey).has_value());
}

TEST_CASE("POST /uploads rejects an unknown fit_mode", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto response = PostUpload("customer_id,transaction_date\n"
                               "A,2024-01-01\n",
                               "?fit_mode=bogus");

    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
    REQUIRE(nlohmann::json::parse(response->getBody())["error"] ==
            "fit_mode must be one of: auto, fast, mcmc");
}
