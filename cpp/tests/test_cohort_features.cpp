#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <vector>
#include "pareto_nbd/cohort_features.hpp"

TEST_CASE("cohort_features matches the Python reference", "[cohort_features]") {
    std::vector<double> x     = {0, 1, 2, 0, 3, 1, 0, 5};
    std::vector<double> t_x   = {0.0, 5.0, 12.0, 0.0, 20.0, 8.0, 0.0, 30.0};
    std::vector<double> T_cal(8, 26.0);

    auto f = pareto_nbd::cohort_features(x, t_x, T_cal);

    REQUIRE(f[0] == Catch::Approx(2.0794415416798357));   // log_N
    REQUIRE(f[1] == Catch::Approx(1.5));                   // mean_x
    REQUIRE(f[2] == Catch::Approx(1.6583123951777));       // sd_x
    REQUIRE(f[3] == Catch::Approx(0.375));                 // frac_zero
    REQUIRE(f[4] == Catch::Approx(0.25));                  // frac_one
    REQUIRE(f[5] == Catch::Approx(3.5999999999999996));    // p90_x
    REQUIRE(f[6] == Catch::Approx(15.0));                  // mean_tx_active
    REQUIRE(f[7] == Catch::Approx(26.0));                  // mean_T
    REQUIRE(f[8] == Catch::Approx(0.5769230769230769));    // recency_ratio
    REQUIRE(f[9] == Catch::Approx(0.4230769230769231));    // since_last_ratio
    REQUIRE(f[10] == Catch::Approx(0.625));                // frac_active
}
