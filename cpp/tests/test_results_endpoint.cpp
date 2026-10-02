#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <map>
#include <string>

#include "pareto_nbd/db.hpp"
#include "test_server_fixture.hpp"

// Exercises the real GET /jobs/{id}/results handler end to end over genuine HTTP, against the
// single shared drogon::app() instance test_server_fixture.cpp's Catch2 global listener starts
// once for this whole test binary (see test_uploads_endpoint.cpp for the full history of why
// this shared-server pattern replaced each file starting its own server). That fixture already
// called pareto_nbd::RegisterApiRoutes, so /jobs/{id}/results is already registered with its
// own db client -- this file duplicates none of the handler's logic.

namespace {

drogon::HttpResponsePtr GetResults(const std::string& job_id,
                                    const std::string& page = "",
                                    const std::string& page_size = "") {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/results");
    if (!page.empty()) req->setParameter("page", page);
    if (!page_size.empty()) req->setParameter("page_size", page_size);
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

drogon::HttpResponsePtr GetResultsWith(const std::string& job_id,
                                        const std::map<std::string, std::string>& params) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/results");
    for (const auto& [k, v] : params) req->setParameter(k, v);
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

}  // namespace

TEST_CASE("GET /jobs/{id}/results paginates forecast_results for a done job", "[api][results]") {
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
    // scope each customer id by this run's fresh job_id so repeated runs never collide.
    // Each row gets a distinct data_quality flag so the response is checked to carry the
    // per-row value through, not a constant.
    const char* kQualities[] = {"ok", "clv_unavailable", "forecast_unavailable"};
    for (int i = 0; i < 3; ++i) {
        auto cust_rows = db->execSqlSync(
            "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
            "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
            pareto_nbd::kDefaultBusinessId, "cust-" + job_id + "-" + std::to_string(i), job_id);
        db->execSqlSync(
            "INSERT INTO forecast_results "
            "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, "
            "clv_upper, model_params, data_quality) "
            "VALUES ($1::uuid, $2::uuid, 1.0, 0.5, 10.0, 8.0, 12.0, '{}'::jsonb, $3)",
            job_id, cust_rows[0]["id"].as<std::string>(), std::string(kQualities[i]));
    }

    // page_size (2) smaller than the total row count (3): confirms `total` reflects the full
    // count, not just the size of the returned page.
    auto response = GetResults(job_id, "1", "2");
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["job_id"] == job_id);
    REQUIRE(body["page"] == 1);
    REQUIRE(body["page_size"] == 2);
    REQUIRE(body["total"] == 3);
    REQUIRE(body["customers"].size() == 2);

    // Second page picks up the remaining row.
    auto response2 = GetResults(job_id, "2", "2");
    REQUIRE(response2->getStatusCode() == drogon::k200OK);
    auto body2 = nlohmann::json::parse(response2->getBody());
    REQUIRE(body2["total"] == 3);
    REQUIRE(body2["customers"].size() == 1);
    REQUIRE(body2["customers"][0]["customer_id"] == "cust-" + job_id + "-2");
    REQUIRE(body2["customers"][0]["data_quality"] == "forecast_unavailable");

    const auto& customer = body["customers"][0];
    REQUIRE(customer["customer_id"] == "cust-" + job_id + "-0");
    REQUIRE(customer["expected_purchases"] == 1.0);
    REQUIRE(customer["p_alive"] == 0.5);
    REQUIRE(customer["clv_point"] == 10.0);
    REQUIRE(customer["clv_lower"] == 8.0);
    REQUIRE(customer["clv_upper"] == 12.0);
    // spec §6: the per-row data-quality flag reaches the client.
    REQUIRE(customer["data_quality"] == "ok");
    REQUIRE(body["customers"][1]["data_quality"] == "clv_unavailable");
}

TEST_CASE("GET /jobs/{id}/results returns 404 for an unknown job and for a not-done job",
          "[api][results]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto response = GetResults("00000000-0000-0000-0000-000000000099");
    REQUIRE(response->getStatusCode() == drogon::k404NotFound);

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'queued', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string queued_job_id = job_rows[0]["id"].as<std::string>();

    auto response2 = GetResults(queued_job_id);
    REQUIRE(response2->getStatusCode() == drogon::k404NotFound);
}

TEST_CASE("GET /jobs/{id}/results returns 400 for a malformed id, never touching the database",
          "[api][results]") {
    auto response = GetResults("not-a-valid-uuid");
    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["error"] == "invalid job id format");
}

TEST_CASE("GET /jobs/{id}/results sorts, filters by quality, and searches by customer id",
          "[api][results]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    // ids sort lexically a < b < c; clv_point ascending is b (5) < c (20) < a (50).
    struct R { const char* suffix; double p; double clv; const char* q; };
    const R rows[] = {{"a", 0.9, 50.0, "ok"},
                      {"b", 0.1, 5.0, "ok"},
                      {"c", 0.5, 20.0, "insufficient_history"}};
    for (const auto& r : rows) {
        auto cust = db->execSqlSync(
            "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
            "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
            pareto_nbd::kDefaultBusinessId, "Cust-" + job_id + "-" + r.suffix, job_id);
        db->execSqlSync(
            "INSERT INTO forecast_results (job_id, customer_id, expected_purchases, p_alive, "
            "clv_point, clv_lower, clv_upper, model_params, data_quality) "
            "VALUES ($1::uuid, $2::uuid, 1.0, $3, $4, $4, $4, '{}'::jsonb, $5)",
            job_id, cust[0]["id"].as<std::string>(), r.p, r.clv, std::string(r.q));
    }
    auto id_of = [&](const char* s) { return "Cust-" + job_id + "-" + s; };

    auto asc = nlohmann::json::parse(
        GetResultsWith(job_id, {{"sort", "clv_point"}, {"order", "asc"}})->getBody());
    REQUIRE(asc["customers"][0]["customer_id"] == id_of("b"));
    REQUIRE(asc["customers"][2]["customer_id"] == id_of("a"));

    auto desc = nlohmann::json::parse(
        GetResultsWith(job_id, {{"sort", "p_alive"}, {"order", "desc"}})->getBody());
    REQUIRE(desc["customers"][0]["customer_id"] == id_of("a"));
    REQUIRE(desc["customers"][2]["customer_id"] == id_of("b"));

    // Default (no sort params) is unchanged: customer_id ascending.
    auto dflt = nlohmann::json::parse(GetResultsWith(job_id, {})->getBody());
    REQUIRE(dflt["customers"][0]["customer_id"] == id_of("a"));

    // quality filter: total reflects the filter, not the whole job.
    auto only_ok = nlohmann::json::parse(GetResultsWith(job_id, {{"quality", "ok"}})->getBody());
    REQUIRE(only_ok["total"] == 2);
    REQUIRE(only_ok["customers"].size() == 2);

    // q: case-insensitive substring on customer id; this job's ids embed the (unique) job id.
    auto found = nlohmann::json::parse(
        GetResultsWith(job_id, {{"q", "cust-" + job_id + "-C"}})->getBody());
    REQUIRE(found["total"] == 1);
    REQUIRE(found["customers"][0]["customer_id"] == id_of("c"));

    // filters compose with paging.
    auto paged = nlohmann::json::parse(
        GetResultsWith(job_id, {{"quality", "ok"}, {"sort", "clv_point"}, {"order", "desc"},
                                {"page", "2"}, {"page_size", "1"}})->getBody());
    REQUIRE(paged["total"] == 2);
    REQUIRE(paged["customers"].size() == 1);
    REQUIRE(paged["customers"][0]["customer_id"] == id_of("b"));
}

TEST_CASE("GET /jobs/{id}/results rejects invalid sort, order and quality values",
          "[api][results]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    REQUIRE(GetResultsWith(job_id, {{"sort", "p_alive; DROP TABLE jobs"}})->getStatusCode() ==
            drogon::k400BadRequest);
    REQUIRE(GetResultsWith(job_id, {{"order", "sideways"}})->getStatusCode() ==
            drogon::k400BadRequest);
    REQUIRE(GetResultsWith(job_id, {{"quality", "great"}})->getStatusCode() ==
            drogon::k400BadRequest);
}
