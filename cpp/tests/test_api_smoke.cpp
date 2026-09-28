#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include <drogon/HttpAppFramework.h>
#include <thread>
#include <chrono>

// Starts the Drogon event loop on a background thread for the duration of this one test
// case, hits it with a real HTTP client, and shuts it down -- proves the Drogon dependency
// actually links and an app can listen and respond, before any later task builds on it.
TEST_CASE("Drogon app starts and answers a request", "[api][smoke]") {
    drogon::app().addListener("127.0.0.1", 18080);
    drogon::app().registerHandler(
        "/healthz",
        [](const drogon::HttpRequestPtr&,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("ok");
            callback(resp);
        },
        {drogon::Get});

    std::thread server_thread([]() { drogon::app().run(); });
    std::this_thread::sleep_for(std::chrono::milliseconds(300));  // let the loop start

    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18080");
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setPath("/healthz");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    REQUIRE(response->getBody() == "ok");

    drogon::app().getLoop()->queueInLoop([]() { drogon::app().quit(); });
    server_thread.join();
}
