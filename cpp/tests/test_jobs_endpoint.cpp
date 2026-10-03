#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <string>

#include "pareto_nbd/db.hpp"
#include "test_server_fixture.hpp"

// Exercises the real GET /jobs/{id} handler end to end over genuine HTTP, against the single
// shared drogon::app() instance test_server_fixture.cpp's Catch2 global listener starts once
// for this whole test binary (see test_uploads_endpoint.cpp for the full history of why this
// shared-server pattern replaced each file starting its own server). That fixture already
// called pareto_nbd::RegisterApiRoutes, so /jobs/{id} is already registered with its own db
// client -- this file duplicates none of the handler's logic.

namespace {

drogon::HttpResponsePtr GetJob(const std::string& job_id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id);
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

}  // namespace

TEST_CASE("GET /jobs/{id} returns status for a known job, 404 for an unknown one",
          "[api][jobs]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = rows[0]["id"].as<std::string>();

    auto response1 = GetJob(job_id);
    REQUIRE(response1->getStatusCode() == drogon::k200OK);
    auto body1 = nlohmann::json::parse(response1->getBody());
    REQUIRE(body1["id"] == job_id);
    REQUIRE(body1["status"] == "done");
    REQUIRE(body1["error_reason"].is_null());

    auto response2 = GetJob("00000000-0000-0000-0000-000000000099");
    REQUIRE(response2->getStatusCode() == drogon::k404NotFound);
}

TEST_CASE("GET /jobs/{id} returns 400 for a malformed id, never touching the database",
          "[api][jobs]") {
    auto response = GetJob("not-a-valid-uuid");
    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["error"] == "invalid job id format");
}

TEST_CASE("GET /jobs/{id} includes the fit fields", "[api][jobs]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path, fit_mode, fit_method, fit_note) "
        "VALUES ($1::uuid, 'done', 'x', 'mcmc', 'amortized', 'fell back') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    auto body = nlohmann::json::parse(GetJob(rows[0]["id"].as<std::string>())->getBody());
    REQUIRE(body["fit_mode"] == "mcmc");
    REQUIRE(body["fit_method"] == "amortized");
    REQUIRE(body["fit_note"] == "fell back");
    REQUIRE(body["source_job_id"].is_null());
}
