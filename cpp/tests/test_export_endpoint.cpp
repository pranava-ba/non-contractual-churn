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

const std::string kHeader =
    "customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper,data_quality\n";

drogon::HttpResponsePtr GetExport(const std::string& job_id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/export.csv");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

std::string InsertJob(const drogon::orm::DbClientPtr& db, const std::string& status) {
    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, $2, 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId, status);
    return job_rows[0]["id"].as<std::string>();
}

void InsertResult(const drogon::orm::DbClientPtr& db, const std::string& job_id,
                  const std::string& external_id, double clv, const std::string& data_quality) {
    auto cust_rows = db->execSqlSync(
        "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
        "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
        pareto_nbd::kDefaultBusinessId, external_id, job_id);
    db->execSqlSync(
        "INSERT INTO forecast_results "
        "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, "
        "model_params, data_quality) "
        "VALUES ($1::uuid, $2::uuid, 1.5, 0.75, $3, $3, $3, '{}'::jsonb, $4)",
        job_id, cust_rows[0]["id"].as<std::string>(), clv, data_quality);
}

}  // namespace

TEST_CASE("GET /jobs/{id}/export.csv streams a CSV of all results", "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = InsertJob(db, "done");

    // external_customer_id is only unique per (business_id, external_customer_id) -- since
    // kDefaultBusinessId and this test's db rows persist across runs (no per-test cleanup),
    // scope the customer id by this run's fresh job_id so repeated runs never collide.
    // 1477186.37 is the exact value the final review saw truncated to "1.47719e+06" by the
    // default ostream precision.
    std::string customer_external_id = "cust-" + job_id;
    InsertResult(db, job_id, customer_external_id, 1477186.37, "insufficient_history");

    auto response = GetExport(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);

    // Content-Type must be exactly "text/csv" -- no stray second content-type header or a
    // leftover default "text/html" (see api_routes.cpp's comment on why setContentTypeString,
    // not addHeader, is required here).
    REQUIRE(std::string(response->getHeader("content-type")) == "text/csv");

    std::string body = std::string(response->getBody());
    REQUIRE(body.find(kHeader) == 0);

    // Exact row: shortest round-trip number formatting (no precision loss) and the per-row
    // data_quality flag in the last column. A plain id needs no quoting.
    REQUIRE(body == kHeader + customer_external_id +
                        ",1.5,0.75,1477186.37,1477186.37,1477186.37,insufficient_history\n");
}

TEST_CASE("GET /jobs/{id}/export.csv quotes/escapes free-text fields and guards against "
          "formula injection",
          "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = InsertJob(db, "done");
    // Ids are scoped by job_id for cross-run uniqueness; the leading character of each is what
    // the formula-injection rule keys on.
    std::string comma_id = "acme, inc \"west\" " + job_id;
    std::string formula_id = "=SUM(A1:A2) " + job_id;
    InsertResult(db, job_id, comma_id, 10.0, "ok");
    InsertResult(db, job_id, formula_id, 20.0, "ok");

    auto response = GetExport(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    std::string body = std::string(response->getBody());

    // Comma + embedded quotes: the field is wrapped in quotes with inner quotes doubled, so
    // column alignment survives (RFC 4180).
    REQUIRE(body.find("\"acme, inc \"\"west\"\" " + job_id + "\",1.5,0.75,10,10,10,ok\n") !=
            std::string::npos);
    // Leading '=': prefixed with a single quote so spreadsheet tools treat it as text.
    REQUIRE(body.find("'=SUM(A1:A2) " + job_id + ",1.5,0.75,20,20,20,ok\n") !=
            std::string::npos);
    // ...and never emitted raw at the start of a field.
    REQUIRE(body.find("\n=SUM") == std::string::npos);

    // Header + exactly two rows: the embedded comma/quotes did not split a row. (Row order is
    // deliberately not asserted -- it depends on the database's collation for punctuation.)
    REQUIRE(body.find(kHeader) == 0);
    REQUIRE(body.size() == kHeader.size() +
                               ("'=SUM(A1:A2) " + job_id + ",1.5,0.75,20,20,20,ok\n").size() +
                               ("\"acme, inc \"\"west\"\" " + job_id + "\",1.5,0.75,10,10,10,ok\n")
                                   .size());
}

TEST_CASE("GET /jobs/{id}/export.csv returns header-only CSV for a done job with no results",
          "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = InsertJob(db, "done");

    auto response = GetExport(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    REQUIRE(std::string(response->getBody()) == kHeader);
}

TEST_CASE("GET /jobs/{id}/export.csv returns 404 for an unknown job and for a not-done job",
          "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto response = GetExport("00000000-0000-0000-0000-000000000099");
    REQUIRE(response->getStatusCode() == drogon::k404NotFound);

    // A queued job, and a failed job that DID write some partial rows before failing: neither
    // may be exported as if it were a complete result set.
    std::string queued_job_id = InsertJob(db, "queued");
    REQUIRE(GetExport(queued_job_id)->getStatusCode() == drogon::k404NotFound);

    std::string failed_job_id = InsertJob(db, "failed");
    InsertResult(db, failed_job_id, "partial-" + failed_job_id, 5.0, "ok");
    REQUIRE(GetExport(failed_job_id)->getStatusCode() == drogon::k404NotFound);
}

TEST_CASE("GET /jobs/{id}/export.csv returns 400 for a malformed id, never touching the database",
          "[api][export]") {
    auto response = GetExport("not-a-valid-uuid");
    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
}
