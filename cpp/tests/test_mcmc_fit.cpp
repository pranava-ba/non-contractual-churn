#include <catch2/catch_test_macros.hpp>
#include <cstdlib>
#include <string>
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/mcmc_fit.hpp"
#include "pareto_nbd/storage.hpp"

namespace {
void SetEnv(const char* k, const std::string& v) {
#ifdef _WIN32
    _putenv_s(k, v.c_str());
#else
    setenv(k, v.c_str(), 1);
#endif
}
pareto_nbd::CustomerFeatures TinyCohort() {
    pareto_nbd::CustomerFeatures c;
    c.customer_id = {"A", "B"};
    c.x = {3, 0};
    c.t_x = {10.5, 0};
    c.T_cal = {20, 20};
    return c;
}
const std::string kFake = std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/fake_mcmc_cli.py";
}  // namespace

TEST_CASE("RunMcmcFit returns posterior-mean params from the CLI", "[mcmc_fit]") {
    SetEnv("PARETO_MCMC_CLI", kFake);
    pareto_nbd::LocalDiskStorage storage("./data/test_mcmc_uploads");
    auto r = pareto_nbd::RunMcmcFit("job-ok", TinyCohort(), storage);
    if (!r.ok && r.note.find("could not start") != std::string::npos) { SKIP("python not launchable"); }
    REQUIRE(r.ok);
    REQUIRE(r.params.r == 0.7);
    REQUIRE(r.params.beta == 13.0);
    REQUIRE(r.draws_key == "mcmc/job-ok_draws.npz");
    REQUIRE(storage.Exists(r.draws_key));
}

TEST_CASE("RunMcmcFit reports a note instead of throwing when the CLI fails", "[mcmc_fit]") {
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/does_not_exist.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_mcmc_uploads");
    auto r = pareto_nbd::RunMcmcFit("job-bad", TinyCohort(), storage);
    REQUIRE_FALSE(r.ok);
    REQUIRE(r.note.rfind("High-precision refit unavailable", 0) == 0);
    SetEnv("PARETO_MCMC_CLI", kFake);
}

TEST_CASE("RunMcmcFit reports a timeout note", "[mcmc_fit]") {
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/sleepy_mcmc_cli.py");
    SetEnv("PARETO_MCMC_TIMEOUT_S", "1");
    pareto_nbd::LocalDiskStorage storage("./data/test_mcmc_uploads");
    auto r = pareto_nbd::RunMcmcFit("job-slow", TinyCohort(), storage);
    SetEnv("PARETO_MCMC_TIMEOUT_S", "600");
    SetEnv("PARETO_MCMC_CLI", kFake);
    REQUIRE_FALSE(r.ok);
    REQUIRE(r.note.find("timed out") != std::string::npos);
}
