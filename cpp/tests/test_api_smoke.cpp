#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>

#include "test_server_fixture.hpp"

// Proves the shared drogon::app() instance (started once for this whole test binary by
// test_server_fixture.cpp's Catch2 global listener, which already called RegisterApiRoutes
// and so already registered /healthz) is actually up and serving real HTTP requests. This
// test case no longer starts, listens on, or stops its own drogon::app() -- see Task 6.5's
// test_server_fixture.cpp for why a second per-test-case lifecycle isn't safe.
TEST_CASE("Drogon app starts and answers a request", "[api][smoke]") {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setPath("/healthz");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    REQUIRE(response->getBody() == "ok");
}
