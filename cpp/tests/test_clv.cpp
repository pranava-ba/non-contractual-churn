#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <cmath>
#include <stdexcept>
#include <vector>
#include "pareto_nbd/clv.hpp"
#include <fstream>
#include <nlohmann/json.hpp>

TEST_CASE("posterior_mean_nu matches the Python reference", "[clv]") {
    std::vector<double> x     = {0, 1, 2, 0, 3, 1, 0, 5, 4, 2};
    std::vector<double> m_obs = {0, 10.0, 15.5, 0, 20.0, 8.0, 0, 30.0, 25.0, 12.0};
    pareto_nbd::GammaGammaParams params{2.5, 3.2, 12.0};

    auto mean = pareto_nbd::posterior_mean_nu(x, m_obs, params);

    std::vector<double> expected = {
        5.454545454545454, 7.872340425531915, 12.430555555555557, 5.454545454545454,
        16.701030927835053, 6.808510638297872, 5.454545454545454, 26.3265306122449,
        21.475409836065577, 10.000000000000002,
    };
    REQUIRE(mean.size() == expected.size());
    for (size_t i = 0; i < expected.size(); ++i) {
        REQUIRE(mean[i] == Catch::Approx(expected[i]).epsilon(1e-9));
    }
}

TEST_CASE("posterior_mean_nu returns NaN when the Inverse-Gamma shape is <= 1", "[clv]") {
    // Customer A: inactive (x=0), shape = q = 0.5 <= 1 -> NaN.
    // Customer B: active (x=1), shape = p*x+q = 0.3+0.5 = 0.8 <= 1 -> NaN.
    // Customer C: active (x=5), shape = p*x+q = 1.5+0.5 = 2.0 > 1 -> finite.
    std::vector<double> x     = {0.0, 1.0, 5.0};
    std::vector<double> m_obs = {0.0, 2.0, 2.0};
    pareto_nbd::GammaGammaParams params{0.3, 0.5, 5.0};

    auto mean = pareto_nbd::posterior_mean_nu(x, m_obs, params);

    REQUIRE(mean.size() == 3);
    REQUIRE(std::isnan(mean[0]));
    REQUIRE(std::isnan(mean[1]));
    REQUIRE(mean[2] == Catch::Approx(8.0).epsilon(1e-9));
}

TEST_CASE("posterior_mean_nu throws on invalid input", "[clv]") {
    pareto_nbd::GammaGammaParams params{2.5, 3.2, 12.0};
    REQUIRE_THROWS_AS(pareto_nbd::posterior_mean_nu({}, {}, params), std::invalid_argument);
    REQUIRE_THROWS_AS(
        pareto_nbd::posterior_mean_nu(std::vector<double>{1.0, 2.0}, std::vector<double>{1.0}, params),
        std::invalid_argument);
}

TEST_CASE("predict_clv_distribution matches the Python reference", "[clv]") {
    std::vector<std::vector<double>> pred_x_star = {{1.0, 2.0, 3.0}, {2.0, 1.0, 4.0}};
    std::vector<std::vector<double>> nu_draws    = {{10.0, 5.0, 2.0}, {8.0, 6.0, 3.0}};

    auto out = pareto_nbd::predict_clv_distribution(pred_x_star, nu_draws, 0.1);

    std::vector<std::vector<double>> expected = {
        {9.048374180359595, 9.048374180359595, 5.4290245082157575},
        {14.477398688575352, 5.4290245082157575, 10.858049016431515},
    };
    REQUIRE(out.size() == expected.size());
    for (size_t d = 0; d < expected.size(); ++d) {
        for (size_t i = 0; i < expected[d].size(); ++i) {
            REQUIRE(out[d][i] == Catch::Approx(expected[d][i]).epsilon(1e-9));
        }
    }
}

TEST_CASE("predict_clv_distribution throws on invalid input", "[clv]") {
    std::vector<std::vector<double>> pred_x_star = {{1.0, 2.0}};
    std::vector<std::vector<double>> nu_draws_wrong_rows = {{1.0, 2.0}, {3.0, 4.0}};
    std::vector<std::vector<double>> nu_draws_wrong_cols = {{1.0}};
    REQUIRE_THROWS_AS(
        pareto_nbd::predict_clv_distribution(pred_x_star, nu_draws_wrong_rows, 0.1),
        std::invalid_argument);
    REQUIRE_THROWS_AS(
        pareto_nbd::predict_clv_distribution(pred_x_star, nu_draws_wrong_cols, 0.1),
        std::invalid_argument);
}

TEST_CASE("fit_gamma_gamma matches the Python reference within 5% relative", "[clv]") {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/clv_conformal_golden.json");
    nlohmann::json golden;
    f >> golden;

    std::vector<double> x = golden["x"].get<std::vector<double>>();
    std::vector<double> m_obs = golden["m_obs"].get<std::vector<double>>();

    auto fit = pareto_nbd::fit_gamma_gamma(x, m_obs);

    REQUIRE(fit.p == Catch::Approx(golden["p"].get<double>()).epsilon(0.05));
    REQUIRE(fit.q == Catch::Approx(golden["q"].get<double>()).epsilon(0.05));
    REQUIRE(fit.v == Catch::Approx(golden["v"].get<double>()).epsilon(0.05));
}

TEST_CASE("fit_gamma_gamma throws on invalid input", "[clv]") {
    REQUIRE_THROWS_AS(
        pareto_nbd::fit_gamma_gamma(std::vector<double>{1.0, 2.0}, std::vector<double>{1.0}),
        std::invalid_argument);
    // No customer passes the x>0 && m_obs>0 filter -> nothing to fit on.
    REQUIRE_THROWS_AS(
        pareto_nbd::fit_gamma_gamma(std::vector<double>{0.0, 1.0}, std::vector<double>{0.0, 0.0}),
        std::invalid_argument);
}

TEST_CASE("sample_posterior_nu's empirical mean converges to the analytical posterior mean", "[clv]") {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/clv_conformal_golden.json");
    nlohmann::json golden;
    f >> golden;

    std::vector<double> x = golden["x"].get<std::vector<double>>();
    std::vector<double> m_obs = golden["m_obs"].get<std::vector<double>>();
    pareto_nbd::GammaGammaParams params{
        golden["p"].get<double>(), golden["q"].get<double>(), golden["v"].get<double>()};

    auto analytical = pareto_nbd::posterior_mean_nu(x, m_obs, params);
    auto draws = pareto_nbd::sample_posterior_nu(x, m_obs, params, 20000, 7);

    REQUIRE(draws.size() == 20000);
    REQUIRE(draws[0].size() == x.size());

    // Empirical mean per customer over all draws.
    std::vector<double> empirical_mean(x.size(), 0.0);
    for (const auto& draw : draws) {
        for (size_t i = 0; i < x.size(); ++i) empirical_mean[i] += draw[i];
    }
    for (double& m : empirical_mean) m /= static_cast<double>(draws.size());

    // Check a sample of customers (checking all 500 with per-customer
    // Monte Carlo noise would make this test flaky; the mean absolute
    // relative error across a subset is a stabler statistic).
    double total_rel_err = 0.0;
    size_t count = 0;
    for (size_t i = 0; i < x.size(); i += 25) {  // every 25th customer, ~20 checks
        total_rel_err += std::abs(empirical_mean[i] - analytical[i]) / analytical[i];
        ++count;
    }
    double mean_rel_err = total_rel_err / static_cast<double>(count);
    REQUIRE(mean_rel_err < 0.05);
}

TEST_CASE("sample_posterior_nu throws on invalid input", "[clv]") {
    pareto_nbd::GammaGammaParams params{2.5, 3.2, 12.0};
    REQUIRE_THROWS_AS(
        pareto_nbd::sample_posterior_nu(std::vector<double>{}, std::vector<double>{}, params, 100, 7),
        std::invalid_argument);
    REQUIRE_THROWS_AS(
        pareto_nbd::sample_posterior_nu(std::vector<double>{1.0, 2.0}, std::vector<double>{1.0}, params,
                                         100, 7),
        std::invalid_argument);
}
