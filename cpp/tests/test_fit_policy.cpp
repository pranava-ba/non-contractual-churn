#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/fit_policy.hpp"

using namespace pareto_nbd;

TEST_CASE("ParseFitMode accepts the three modes and rejects anything else", "[fit_policy]") {
    REQUIRE(ParseFitMode("auto") == FitMode::Auto);
    REQUIRE(ParseFitMode("fast") == FitMode::Fast);
    REQUIRE(ParseFitMode("mcmc") == FitMode::Mcmc);
    REQUIRE_FALSE(ParseFitMode("MCMC").has_value());
    REQUIRE_FALSE(ParseFitMode("").has_value());
    REQUIRE(ToString(FitMode::Mcmc) == "mcmc");
}

TEST_CASE("auto picks MCMC only inside the small-cohort window", "[fit_policy]") {
    REQUIRE(ChooseFitMethod(FitMode::Auto, 3).method == FitMethod::Amortized);        // too tiny
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMinCustomers - 1).method == FitMethod::Amortized);
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMinCustomers).method == FitMethod::Mcmc);
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMaxCustomers).method == FitMethod::Mcmc);
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMaxCustomers + 1).method == FitMethod::Amortized);
    REQUIRE(ChooseFitMethod(FitMode::Auto, 10).note.empty());
}

TEST_CASE("fast never uses MCMC and explicit mcmc honours small cohorts", "[fit_policy]") {
    REQUIRE(ChooseFitMethod(FitMode::Fast, 100).method == FitMethod::Amortized);
    REQUIRE(ChooseFitMethod(FitMode::Mcmc, 3).method == FitMethod::Mcmc);
    REQUIRE(ChooseFitMethod(FitMode::Mcmc, kMcmcMaxCustomers).method == FitMethod::Mcmc);
}

TEST_CASE("explicit mcmc above the hard cap falls back with an explanatory note", "[fit_policy]") {
    auto d = ChooseFitMethod(FitMode::Mcmc, kMcmcMaxCustomers + 1);
    REQUIRE(d.method == FitMethod::Amortized);
    REQUIRE(d.note.find("20000") != std::string::npos);
}
