#include <catch2/catch_test_macros.hpp>
#include <chrono>
#include <cstdlib>
#include <string>
#include "pareto_nbd/subprocess.hpp"

namespace {
std::string Py() { const char* p = std::getenv("PARETO_PYTHON"); return p ? p : "python"; }
}

TEST_CASE("RunWithTimeout reports exit codes", "[subprocess]") {
    auto ok = pareto_nbd::RunWithTimeout({Py(), "-c", "import sys; sys.exit(0)"}, 20);
    if (!ok.launched) { SKIP("python not launchable"); }
    REQUIRE_FALSE(ok.timed_out);
    REQUIRE(ok.exit_code == 0);
    auto bad = pareto_nbd::RunWithTimeout({Py(), "-c", "import sys; sys.exit(3)"}, 20);
    REQUIRE(bad.exit_code == 3);
}

TEST_CASE("RunWithTimeout kills a process that exceeds the timeout", "[subprocess]") {
    auto probe = pareto_nbd::RunWithTimeout({Py(), "-c", "pass"}, 20);
    if (!probe.launched) { SKIP("python not launchable"); }
    auto t0 = std::chrono::steady_clock::now();
    auto r = pareto_nbd::RunWithTimeout({Py(), "-c", "import time; time.sleep(60)"}, 1);
    auto secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    REQUIRE(r.launched);
    REQUIRE(r.timed_out);
    REQUIRE(secs < 15.0);
}

TEST_CASE("RunWithTimeout reports launched=false for a missing executable", "[subprocess]") {
    auto r = pareto_nbd::RunWithTimeout({"definitely-not-a-real-binary-xyz"}, 5);
    // POSIX fork succeeds then exec fails with 127, Windows CreateProcess fails outright.
    REQUIRE((!r.launched || r.exit_code == 127));
}

TEST_CASE("RunWithTimeout passes arguments containing spaces and quotes intact", "[subprocess]") {
    auto probe = pareto_nbd::RunWithTimeout({Py(), "-c", "pass"}, 20);
    if (!probe.launched) { SKIP("python not launchable"); }
    auto r = pareto_nbd::RunWithTimeout(
        {Py(), "-c", "import sys; sys.exit(0 if sys.argv[1] == 'a \"b\" c' else 9)", "a \"b\" c"}, 20);
    REQUIRE(r.exit_code == 0);
}
