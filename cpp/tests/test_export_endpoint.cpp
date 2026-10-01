#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>

#include <string>

#include "pareto_nbd/db.hpp"
#include "test_server_fixture.hpp"

// Exercises the real GET /jobs/{id}/export.csv handler end to end over genuine HTTP, against
// the single shared drogon::app() instance test_server_fixture.cpp's Catch2 global listener
// starts once for this whole test binary (see test_uploads_endpoint.cpp for the full history
// of why this shared-server pattern replaced each file starting its own server). That fixture
// already called pareto_nbd::RegisterApiRoutes, so /jobs/{id}/export.csv is already registered
// with its own db client -- this file duplicates none of the handler's logic.

namespace {

drogon::HttpResponsePtr GetExport(const std::string& job_id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/export.csv");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

}  // namespace

TEST_CASE("GET /jobs/{id}/export.csv streams a CSV of all results", "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    // external_customer_id is only unique per (business_id, external_customer_id) -- since
    // kDefaultBusinessId and this test's db rows persist across runs (no per-test cleanup),
    // scope the customer id by this run's fresh job_id so repeated runs never collide.
    std::string customer_external_id = "cust-" + job_id;
    auto cust_rows = db->execSqlSync(
        "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
        "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
        pareto_nbd::kDefaultBusinessId, customer_external_id, job_id);
    db->execSqlSync(
        "INSERT INTO forecast_results "
        "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, "
        "model_params) "
        "VALUES ($1::uuid, $2::uuid, 1.5, 0.75, 20.0, 15.0, 25.0, '{}'::jsonb)",
        job_id, cust_rows[0]["id"].as<std::string>());

    auto response = GetExport(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);

    // Content-Type must be exactly "text/csv" -- no stray second content-type header or a
    // leftover default "text/html" (see api_routes.cpp's comment on why setContentTypeString,
    // not addHeader, is required here).
    REQUIRE(std::string(response->getHeader("content-type")) == "text/csv");

    std::string body = std::string(response->getBody());
    REQUIRE(body.find("customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper\n") ==
            0);

    // Don't over-fit to an exact double-formatting guess -- find the row by its known fields
    // and confirm it is comma-separated with no stray quoting.
    auto row_start = body.find(customer_external_id + ",");
    REQUIRE(row_start != std::string::npos);
    auto row_end = body.find('\n', row_start);
    REQUIRE(row_end != std::string::npos);
    std::string row = body.substr(row_start, row_end - row_start);
    REQUIRE(row.find('"') == std::string::npos);

    size_t commas = 0;
    for (char c : row) {
        if (c == ',') ++commas;
    }
    REQUIRE(commas == 5);
}

TEST_CASE("GET /jobs/{id}/export.csv returns header-only CSV for a job with no results",
          "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'queued', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    auto response = GetExport(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    REQUIRE(std::string(response->getBody()) ==
            "customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper\n");
}

TEST_CASE("GET /jobs/{id}/export.csv returns 400 for a malformed id, never touching the database",
          "[api][export]") {
    auto response = GetExport("not-a-valid-uuid");
    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
}
