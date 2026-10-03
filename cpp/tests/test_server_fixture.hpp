#pragma once
#include <string>

namespace pareto_nbd::test {

// Base URL of the single shared drogon::app() instance this test binary starts once (see
// test_server_fixture.cpp's Catch2 global listener). Every HTTP-endpoint test uses this
// instead of starting its own server.
std::string TestServerBaseUrl();

}  // namespace pareto_nbd::test
