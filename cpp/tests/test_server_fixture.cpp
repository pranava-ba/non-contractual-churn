#include "test_server_fixture.hpp"

#include <catch2/reporters/catch_reporter_event_listener.hpp>
#include <catch2/reporters/catch_reporter_registrars.hpp>
#include <drogon/drogon.h>

#include <chrono>
#include <memory>
#include <thread>

#include "pareto_nbd/api_routes.hpp"
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd::test {

std::string TestServerBaseUrl() { return "http://127.0.0.1:18080"; }

}  // namespace pareto_nbd::test

namespace {

// Catch2 global listener that starts ONE shared drogon::app() instance before any test case
// in this binary runs, and stops it once after the whole run finishes.
//
// Why this exists: drogon::app() is a process-wide singleton that cannot safely go through a
// second addListener/run()/quit() cycle within one process -- confirmed empirically two
// different ways while building Task 5's upload endpoint test: calling run() a second time in
// the same file segfaulted, and running a second cycle after another test file's cycle had
// already completed instead hit a trantor FATAL, "EventLoop cannot be moved when running".
// Task 5 worked around this by calling its handler directly as a plain callable, bypassing
// real HTTP and duplicating handler logic between api_main.cpp and the test file -- flagged in
// review as a real gap (no endpoint had true HTTP/TCP-level coverage) and a maintenance risk.
//
// The fix: register every route exactly once (via pareto_nbd::RegisterApiRoutes, now shared
// between api_main.cpp and this fixture) onto the ONE drogon::app() instance this listener
// starts in testRunStarting and stops in testRunEnded. Every HTTP-endpoint test case in this
// binary then drives real requests against pareto_nbd::test::TestServerBaseUrl() instead of
// starting its own server.
class SharedServerListener : public Catch::EventListenerBase {
public:
    using Catch::EventListenerBase::EventListenerBase;

    void testRunStarting(Catch::TestRunInfo const&) override {
        auto storage =
            std::make_shared<pareto_nbd::LocalDiskStorage>("./data/test_server_uploads");
        auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
        auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);

        pareto_nbd::RegisterApiRoutes(storage, db, redis);
        drogon::app().addListener("127.0.0.1", 18080);

        server_thread_ = std::thread([]() { drogon::app().run(); });
        // Let the loop actually start listening before any test case tries to connect --
        // same 300ms wait Task 1's original smoke test used.
        std::this_thread::sleep_for(std::chrono::milliseconds(300));
    }

    void testRunEnded(Catch::TestRunStats const&) override {
        drogon::app().getLoop()->queueInLoop([]() { drogon::app().quit(); });
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

private:
    std::thread server_thread_;
};

}  // namespace

CATCH_REGISTER_LISTENER(SharedServerListener)
