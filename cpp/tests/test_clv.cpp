#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
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
