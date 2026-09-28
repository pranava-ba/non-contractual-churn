#include <drogon/drogon.h>

int main() {
    drogon::app().addListener("0.0.0.0", 8080);
    drogon::app().registerHandler(
        "/healthz",
        [](const drogon::HttpRequestPtr&,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("ok");
            callback(resp);
        },
        {drogon::Get});
    drogon::app().run();
    return 0;
}
