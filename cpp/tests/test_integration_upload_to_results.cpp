#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <string>

#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"
#include "pareto_nbd/worker.hpp"
#include "test_server_fixture.hpp"

// End-to-end integration test for spec §7: "an end-to-end test that uploads a known small
// cohort through the real API -> worker -> results path and checks the response shape and a
// few known forecast values." Every test before this task exercised one layer at a time
// (worker logic directly in test_worker.cpp, each endpoint alone in Tasks 7-10) -- this is
// the only test in the whole plan that chains a real POST /uploads, a real Redis dequeue, an
// in-process worker pass, and the real GET /jobs/{id}, /jobs/{id}/results and
// /jobs/{id}/export.csv handlers together, over genuine HTTP for every API call.
//
// Drives every HTTP call against the single shared drogon::app() instance
// test_server_fixture.cpp's Catch2 global listener starts once for this whole test binary --
// same established pattern as Tasks 7-10's endpoint tests (test_uploads_endpoint.cpp,
// test_jobs_endpoint.cpp, test_results_endpoint.cpp, test_export_endpoint.cpp). No
// addListener/run()/quit() in this file; that fixture already called RegisterApiRoutes, so
// every route this test touches is already live with its own storage/db/redis clients.
//
// Worker simulation: per this task's brief, a second `worker` process is not spawned here --
// spawning worker_main as a real subprocess is possible but adds process-lifecycle complexity
// for marginal extra coverage. Instead this test dequeues the job id itself via the real
// pareto_nbd::DequeueJob (proving the real POST /uploads -> EnqueueJob -> DequeueJob path
// actually round-trips through Redis, not just that EnqueueJob didn't throw) and then calls
// pareto_nbd::ProcessOneJob directly in-process, exactly what worker_main's loop would do
// after its own DequeueJob call returned this id. This is a documented simplification, not a
// silently-accepted gap: the worker's own internal correctness (overflow handling,
// data_quality classification, CLV fitting) is already covered in depth by test_worker.cpp
// (Tasks 6a-6c); this test's job is to prove the real HTTP/Redis plumbing around it.
//
// Fixture choice: reuses the exact small cohort test_worker.cpp's first test case already
// uses (customer A: 3 transactions / 2 repeat purchases; customer B: a single transaction),
// rather than inventing a new one. That keeps this test's "known forecast values" check
// anchored to behavior already proven correct: A has x>0 so scores data_quality='ok', B has
// a single transaction (x==0) so scores data_quality='insufficient_history' -- asserted here
// both indirectly (through the real GET /jobs/{id}/results and /jobs/{id}/export.csv HTTP
// responses) and directly against the database, the same way test_worker.cpp and
// test_results_endpoint.cpp already do.

namespace {

constexpr const char* kCohortCsv =
    "customer_id,transaction_date,amount\n"
    "A,2024-01-01,10.0\nA,2024-01-08,5.0\nA,2024-01-22,8.0\n"
    "B,2024-01-01,3.0\n";

drogon::HttpResponsePtr Get(const std::string& path) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath(path);
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

}  // namespace

TEST_CASE("Full loop: upload -> worker processes -> results are queryable over real HTTP",
          "[integration]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    // Step 1: POST /uploads over real HTTP. The shared fixture registers this route with
    // storage root "./data/test_server_uploads" (test_server_fixture.cpp) -- the
    // LocalDiskStorage this test builds further down to call ProcessOneJob must point at that
    // exact same root, or ProcessOneJob's storage.GetPath(key) won't find the file this
    // upload just wrote.
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto upload_req = drogon::HttpRequest::newHttpRequest();
    upload_req->setMethod(drogon::Post);
    upload_req->setPath("/uploads");
    upload_req->setBody(kCohortCsv);
    auto [upload_result, upload_resp] = client->sendRequest(upload_req, 5.0);
    REQUIRE(upload_result == drogon::ReqResult::Ok);
    REQUIRE(upload_resp->getStatusCode() == drogon::k200OK);
    auto upload_body = nlohmann::json::parse(upload_resp->getBody());
    REQUIRE(upload_body.contains("job_id"));
    std::string job_id = upload_body["job_id"].get<std::string>();

    // Step 2: GET /jobs/{id} immediately after upload -- must show 'queued', since nothing
    // has dequeued or processed it yet.
    {
        auto resp = Get("/jobs/" + job_id);
        REQUIRE(resp->getStatusCode() == drogon::k200OK);
        auto body = nlohmann::json::parse(resp->getBody());
        REQUIRE(body["id"] == job_id);
        REQUIRE(body["status"] == "queued");
        REQUIRE(body["error_reason"].is_null());
    }

    // Step 3: dequeue the real job id from the real Redis queue -- proves POST /uploads's
    // EnqueueJob call actually round-tripped through Redis (same assertion style
    // test_uploads_endpoint.cpp uses), not just that it didn't throw.
    auto dequeued = pareto_nbd::DequeueJob(redis, 5);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == job_id);

    // Simulate the worker: call ProcessOneJob directly in-process, exactly what
    // worker_main's loop would do with this dequeued id (this task's documented
    // simplification -- see file header).
    pareto_nbd::LocalDiskStorage storage("./data/test_server_uploads");
    pareto_nbd::ProcessOneJob(*dequeued, db, storage);

    // Step 4: GET /jobs/{id} again -- confirm status flipped to 'done' with no error reason.
    {
        auto resp = Get("/jobs/" + job_id);
        REQUIRE(resp->getStatusCode() == drogon::k200OK);
        auto body = nlohmann::json::parse(resp->getBody());
        REQUIRE(body["status"] == "done");
        REQUIRE(body["error_reason"].is_null());
    }

    // Direct-DB check of this cohort's known, already-verified classification (same style as
    // test_worker.cpp's first test case, which uses this identical cohort): A has repeat
    // purchases (x>0) so scores data_quality='ok'; B is a single-transaction customer (x==0)
    // so scores data_quality='insufficient_history'. The public results/export endpoints
    // below don't expose data_quality, so this is the only way to confirm that specific,
    // known classification landed correctly after going through the real HTTP+Redis path.
    {
        auto rows = db->execSqlSync(
            "SELECT c.external_customer_id, fr.data_quality, fr.p_alive, fr.expected_purchases "
            "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
            "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id",
            job_id);
        REQUIRE(rows.size() == 2);
        REQUIRE(rows[0]["external_customer_id"].as<std::string>() == "A");
        REQUIRE(rows[0]["data_quality"].as<std::string>() == "ok");
        REQUIRE(rows[1]["external_customer_id"].as<std::string>() == "B");
        REQUIRE(rows[1]["data_quality"].as<std::string>() == "insufficient_history");
        for (const auto& row : rows) {
            double p_alive = row["p_alive"].as<double>();
            REQUIRE(p_alive >= 0.0);
            REQUIRE(p_alive <= 1.0);
            REQUIRE(row["expected_purchases"].as<double>() >= 0.0);
        }
    }

    // Step 5: GET /jobs/{id}/results over real HTTP -- response shape plus the same known
    // per-customer values, this time read back through the public API a Phase-5 frontend
    // would actually call.
    {
        auto resp = Get("/jobs/" + job_id + "/results");
        REQUIRE(resp->getStatusCode() == drogon::k200OK);
        auto body = nlohmann::json::parse(resp->getBody());
        REQUIRE(body["job_id"] == job_id);
        REQUIRE(body["page"] == 1);
        REQUIRE(body["page_size"] == 50);
        REQUIRE(body["total"] == 2);  // customers A and B
        REQUIRE(body["customers"].size() == 2);

        // ORDER BY external_customer_id in the handler puts A before B.
        const auto& a = body["customers"][0];
        const auto& b = body["customers"][1];
        REQUIRE(a["customer_id"] == "A");
        REQUIRE(b["customer_id"] == "B");
        for (const auto& customer : body["customers"]) {
            double p_alive = customer["p_alive"].get<double>();
            REQUIRE(p_alive >= 0.0);
            REQUIRE(p_alive <= 1.0);
            REQUIRE(customer["expected_purchases"].get<double>() >= 0.0);
            REQUIRE(customer["clv_point"].get<double>() >= 0.0);
            // No conformal interval is fitted in this phase (Task 10's note): lower/upper
            // collapse to the point estimate.
            REQUIRE(customer["clv_lower"].get<double>() == customer["clv_point"].get<double>());
            REQUIRE(customer["clv_upper"].get<double>() == customer["clv_point"].get<double>());
        }
    }

    // Step 6: GET /jobs/{id}/export.csv -- closes the loop on the full API surface this plan
    // built (Phase 5's frontend needs this endpoint too, per Task 11's brief), confirming the
    // same two customers come back in CSV form with a real "text/csv" content type.
    {
        auto resp = Get("/jobs/" + job_id + "/export.csv");
        REQUIRE(resp->getStatusCode() == drogon::k200OK);
        REQUIRE(std::string(resp->getHeader("content-type")) == "text/csv");

        std::string body = std::string(resp->getBody());
        REQUIRE(body.find("customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper\n") ==
                0);

        auto a_row = body.find("A,");
        auto b_row = body.find("B,");
        REQUIRE(a_row != std::string::npos);
        REQUIRE(b_row != std::string::npos);
        REQUIRE(a_row < b_row);  // same ORDER BY external_customer_id as /results

        // Exactly 3 lines: header + A + B, nothing extra from a prior run leaking in (every
        // row is scoped to this run's fresh job_id).
        size_t line_count = 0;
        for (char c : body) {
            if (c == '\n') ++line_count;
        }
        REQUIRE(line_count == 3);
    }
}
