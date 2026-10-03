#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <string>

#include "pareto_nbd/db.hpp"
#include "test_server_fixture.hpp"

// Real HTTP against the shared test server (see test_results_endpoint.cpp for why).

namespace {

drogon::HttpResponsePtr GetSummary(const std::string& job_id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/summary");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

std::string MakeDoneJob(const drogon::orm::DbClientPtr& db) {
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    return rows[0]["id"].as<std::string>();
}

void AddRow(const drogon::orm::DbClientPtr& db, const std::string& job_id, int idx,
            double expected, double p_alive, double clv, double lower, double upper,
            const std::string& quality) {
    auto cust = db->execSqlSync(
        "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
        "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
        pareto_nbd::kDefaultBusinessId, "cust-" + job_id + "-" + std::to_string(idx), job_id);
    db->execSqlSync(
        "INSERT INTO forecast_results (job_id, customer_id, expected_purchases, p_alive, "
        "clv_point, clv_lower, clv_upper, model_params, data_quality) "
        "VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, '{}'::jsonb, $8)",
        job_id, cust[0]["id"].as<std::string>(), expected, p_alive, clv, lower, upper, quality);
}

}  // namespace

TEST_CASE("GET /jobs/{id}/summary aggregates a done job, excluding placeholder rows",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = MakeDoneJob(db);
    //             idx  exp   p_alive clv   lo    hi    quality
    AddRow(db, job_id, 0, 1.0, 0.55,  10.0, 8.0,  12.0, "ok");
    AddRow(db, job_id, 1, 3.0, 1.0,   30.0, 30.0, 30.0, "ok");
    AddRow(db, job_id, 2, 0.5, 0.25,  0.0,  0.0,  0.0,  "insufficient_history");
    AddRow(db, job_id, 3, 0.0, 0.0,   0.0,  0.0,  0.0,  "forecast_unavailable");

    auto response = GetSummary(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());

    REQUIRE(body["job_id"] == job_id);
    REQUIRE(body["n_customers"] == 4);
    REQUIRE(body["quality_counts"]["ok"] == 2);
    REQUIRE(body["quality_counts"]["insufficient_history"] == 1);
    REQUIRE(body["quality_counts"]["forecast_unavailable"] == 1);
    REQUIRE_FALSE(body["quality_counts"].contains("clv_unavailable"));

    // Valid-forecast rows are the first three: mean p_alive = (0.55 + 1.0 + 0.25) / 3.
    REQUIRE(body["mean_p_alive"].get<double>() == Catch::Approx(0.6));
    REQUIRE(body["total_expected_purchases"].get<double>() == Catch::Approx(4.5));
    // CLV only counts 'ok' rows.
    REQUIRE(body["total_clv"].get<double>() == Catch::Approx(40.0));
    REQUIRE(body["has_clv_interval"] == true);  // row 0 has lower 8 < upper 12

    // p_alive: 10 bins over [0,1]. 0.25 -> bin 3, 0.55 -> bin 6, 1.0 -> clamped into bin 10.
    const auto& pa = body["histograms"]["p_alive"];
    REQUIRE(pa["edges"].size() == 11);
    REQUIRE(pa["counts"].size() == 10);
    REQUIRE(pa["edges"][0].get<double>() == Catch::Approx(0.0));
    REQUIRE(pa["edges"][10].get<double>() == Catch::Approx(1.0));
    REQUIRE(pa["counts"][2] == 1);
    REQUIRE(pa["counts"][5] == 1);
    REQUIRE(pa["counts"][9] == 1);

    // expected_purchases: valid rows are 1.0, 3.0, 0.5; 20 bins over [0, 3.0] (width 0.15).
    // 0.5 -> bin 4, 1.0 -> bin 7, 3.0 (== max) -> clamped into bin 20.
    const auto& ep = body["histograms"]["expected_purchases"];
    REQUIRE(ep["counts"].size() == 20);
    REQUIRE(ep["edges"][20].get<double>() == Catch::Approx(3.0));
    REQUIRE(ep["counts"][3] == 1);
    REQUIRE(ep["counts"][6] == 1);
    REQUIRE(ep["counts"][19] == 1);

    // clv_point: only the two 'ok' rows (10, 30); 20 bins over [0, 30] (width 1.5).
    const auto& clv = body["histograms"]["clv_point"];
    REQUIRE(clv["counts"][6] == 1);    // 10 / 1.5 = 6.67 -> bin 7
    REQUIRE(clv["counts"][19] == 1);   // 30 == max -> bin 20
}

TEST_CASE("summary reports has_clv_interval=false when every interval is degenerate",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = MakeDoneJob(db);
    AddRow(db, job_id, 0, 1.0, 0.5, 10.0, 10.0, 10.0, "ok");

    auto response = GetSummary(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    REQUIRE(nlohmann::json::parse(response->getBody())["has_clv_interval"] == false);
}

TEST_CASE("summary of a job with no valid-forecast rows has empty-safe histograms",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = MakeDoneJob(db);
    AddRow(db, job_id, 0, 0.0, 0.0, 0.0, 0.0, 0.0, "forecast_unavailable");

    auto response = GetSummary(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["n_customers"] == 1);
    REQUIRE(body["mean_p_alive"].get<double>() == Catch::Approx(0.0));
    REQUIRE(body["histograms"]["expected_purchases"]["edges"][20].get<double>() ==
            Catch::Approx(1.0));  // max <= 0 falls back to range [0, 1]
    for (const auto& c : body["histograms"]["p_alive"]["counts"]) REQUIRE(c == 0);
}

TEST_CASE("summary returns 404 for unknown/not-done jobs and 400 for a malformed id",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    REQUIRE(GetSummary("00000000-0000-0000-0000-000000000099")->getStatusCode() ==
            drogon::k404NotFound);

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'running', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    REQUIRE(GetSummary(rows[0]["id"].as<std::string>())->getStatusCode() ==
            drogon::k404NotFound);

    REQUIRE(GetSummary("not-a-valid-uuid")->getStatusCode() == drogon::k400BadRequest);
}
