#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

#include <nlohmann/json.hpp>

#include "pareto_nbd/forecast.hpp"

namespace {

// Golden values are exact-arithmetic quantities (closed forms, no MLE fit), so the
// tolerance is tight. Observed agreement is ~1e-12 or better (see task-6b report);
// 1e-10 leaves headroom for compiler/libm differences without hiding real bugs.
constexpr double kRelTol = 1e-10;
// Below this the reference value is denormal/underflowed in double; relative error is
// meaningless there, so require the port to be (numerically) zero as well.
constexpr double kUnderflow = 1e-290;

nlohmann::json load_golden() {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/forecast_golden.json");
    REQUIRE(f.good());
    nlohmann::json golden;
    f >> golden;
    return golden;
}

pareto_nbd::ParetoNbdParams params_of(const nlohmann::json& c) {
    return {c["r"].get<double>(), c["alpha"].get<double>(), c["s"].get<double>(),
            c["beta"].get<double>()};
}

// Relative error of `got` vs `ref`; for an underflowed/zero reference, 0 iff `got` is
// also below the underflow threshold (else +inf, which fails any tolerance).
double rel_err(double got, double ref) {
    if (std::abs(ref) < kUnderflow) {
        return std::abs(got) < kUnderflow ? 0.0 : std::numeric_limits<double>::infinity();
    }
    return std::abs(got - ref) / std::abs(ref);
}

}  // namespace

TEST_CASE("forecast golden file covers the required regimes", "[forecast]") {
    auto golden = load_golden();
    const auto& cases = golden["cases"];
    int overflow = 0, expect_throw = 0, s_near_one = 0, normal = 0;
    for (const auto& c : cases) {
        if (c["is_overflow_case"].get<bool>()) ++overflow;
        if (c["cpp_expect_throw"].get<bool>()) ++expect_throw;
        const double s = c["s"].get<double>();
        if (s != 1.0 && std::abs(s - 1.0) < 1e-5) ++s_near_one;
        if (!c["is_overflow_case"].get<bool>() && !c["cpp_expect_throw"].get<bool>()) ++normal;
    }
    CHECK(normal >= 20);
    CHECK(overflow >= 1);
    CHECK(expect_throw >= 1);
    CHECK(s_near_one >= 1);
}

TEST_CASE("p_alive and expected_purchases match the Python oracle and mpmath", "[forecast]") {
    auto golden = load_golden();
    double max_pa_py = 0, max_pa_mp = 0, max_ep_py = 0, max_ep_mp = 0, max_overflow = 0;
    int checked = 0;
    for (const auto& c : golden["cases"]) {
        if (c["cpp_expect_throw"].get<bool>()) continue;
        const auto prm = params_of(c);
        const double x = c["x"].get<double>(), t_x = c["t_x"].get<double>(),
                     T = c["T"].get<double>(), h = c["horizon"].get<double>();
        INFO("case: " << c["name"].get<std::string>() << " (r=" << prm.r << ", alpha="
                      << prm.alpha << ", s=" << prm.s << ", beta=" << prm.beta << ", x=" << x
                      << ", t_x=" << t_x << ", T=" << T << ", h=" << h << ")");

        const double pa = pareto_nbd::p_alive(prm, x, t_x, T);
        const double ep = pareto_nbd::expected_purchases(prm, x, t_x, T, h);
        CHECK(pa >= 0.0);
        CHECK(pa <= 1.0);
        CHECK(ep >= 0.0);

        const double e_pa_py = rel_err(pa, c["p_alive"].get<double>());
        const double e_pa_mp = rel_err(pa, c["p_alive_mpmath"].get<double>());
        const double e_ep_py = rel_err(ep, c["expected_purchases"].get<double>());
        const double e_ep_mp = rel_err(ep, c["expected_purchases_mpmath"].get<double>());
        INFO("p_alive=" << pa << " (oracle " << c["p_alive"].get<double>() << ", rel " << e_pa_py
                        << "; mpmath rel " << e_pa_mp << ")");
        INFO("expected=" << ep << " (oracle " << c["expected_purchases"].get<double>()
                         << ", rel " << e_ep_py << "; mpmath rel " << e_ep_mp << ")");
        CHECK(e_pa_py <= kRelTol);
        CHECK(e_pa_mp <= kRelTol);
        CHECK(e_ep_py <= kRelTol);
        CHECK(e_ep_mp <= kRelTol);

        max_pa_py = std::max(max_pa_py, e_pa_py);
        max_pa_mp = std::max(max_pa_mp, e_pa_mp);
        max_ep_py = std::max(max_ep_py, e_ep_py);
        max_ep_mp = std::max(max_ep_mp, e_ep_mp);
        if (c["is_overflow_case"].get<bool>()) {
            max_overflow = std::max({max_overflow, e_pa_py, e_pa_mp, e_ep_py, e_ep_mp});
        }
        ++checked;
    }
    std::cout << "[forecast golden] " << checked << " cases; max rel err p_alive vs oracle "
              << max_pa_py << ", vs mpmath " << max_pa_mp << "; expected_purchases vs oracle "
              << max_ep_py << ", vs mpmath " << max_ep_mp
              << "; worst in oracle's hyp2f1-overflow region " << max_overflow << "\n";
    REQUIRE(checked >= 20);
}

TEST_CASE("extreme alpha/beta ratio throws ForecastOverflowError, not a wrong number",
          "[forecast]") {
    auto golden = load_golden();
    int checked = 0;
    for (const auto& c : golden["cases"]) {
        if (!c["cpp_expect_throw"].get<bool>()) continue;
        const auto prm = params_of(c);
        const double x = c["x"].get<double>(), t_x = c["t_x"].get<double>(),
                     T = c["T"].get<double>(), h = c["horizon"].get<double>();
        INFO("case: " << c["name"].get<std::string>());
        REQUIRE_THROWS_AS(pareto_nbd::p_alive(prm, x, t_x, T), pareto_nbd::ForecastOverflowError);
        REQUIRE_THROWS_AS(pareto_nbd::expected_purchases(prm, x, t_x, T, h),
                          pareto_nbd::ForecastOverflowError);
        REQUIRE_THROWS_WITH(pareto_nbd::p_alive(prm, x, t_x, T),
                            Catch::Matchers::ContainsSubstring("known, documented limitation"));
        ++checked;
    }
    REQUIRE(checked >= 1);
}

TEST_CASE("expected_purchases(precomputed_p_alive) matches the single-argument overload",
          "[forecast]") {
    auto golden = load_golden();
    int checked = 0;
    for (const auto& c : golden["cases"]) {
        if (c["cpp_expect_throw"].get<bool>()) continue;
        const auto prm = params_of(c);
        const double x = c["x"].get<double>(), t_x = c["t_x"].get<double>(),
                     T = c["T"].get<double>(), h = c["horizon"].get<double>();
        const double pa = pareto_nbd::p_alive(prm, x, t_x, T);
        const double ep_one_arg = pareto_nbd::expected_purchases(prm, x, t_x, T, h);
        const double ep_precomputed = pareto_nbd::expected_purchases(prm, x, t_x, T, h, pa);
        INFO("case: " << c["name"].get<std::string>());
        CHECK(ep_precomputed == ep_one_arg);
        ++checked;
    }
    REQUIRE(checked >= 20);

    // Garbage-in/garbage-out guard: the precomputed p_alive is trusted numerically but must
    // still be a valid probability.
    const pareto_nbd::ParetoNbdParams ok{0.7, 5.0, 0.6, 8.0};
    REQUIRE_THROWS_AS(pareto_nbd::expected_purchases(ok, 3, 20.0, 40.0, 13.0, -0.1),
                      std::invalid_argument);
    REQUIRE_THROWS_AS(pareto_nbd::expected_purchases(ok, 3, 20.0, 40.0, 13.0, 1.1),
                      std::invalid_argument);
    REQUIRE_THROWS_AS(
        pareto_nbd::expected_purchases(ok, 3, 20.0, 40.0, 13.0, std::nan("")),
        std::invalid_argument);
}

TEST_CASE("WouldOverflow agrees with whether p_alive actually throws", "[forecast]") {
    // Known throw-case from models/forecast_golden.json ("C++ limitation: alpha/beta=1e-8,
    // x=0 -> ForecastOverflowError"): extreme alpha/beta ratio at t_x=0.
    const pareto_nbd::ParetoNbdParams overflow_params{0.7, 1e-6, 0.6, 100.0};
    REQUIRE(pareto_nbd::WouldOverflow(overflow_params, 0.0));
    REQUIRE_THROWS_AS(pareto_nbd::p_alive(overflow_params, 0.0, 0.0, 30.0),
                      pareto_nbd::ForecastOverflowError);

    // A normal, comfortably-converging case ("alpha<beta typical" from the same golden file,
    // evaluated at t_x=0 -- the case WouldOverflow's signature checks).
    const pareto_nbd::ParetoNbdParams normal_params{0.7, 5.0, 0.6, 8.0};
    REQUIRE_FALSE(pareto_nbd::WouldOverflow(normal_params, 0.0));
    REQUIRE_NOTHROW(pareto_nbd::p_alive(normal_params, 0.0, 0.0, 30.0));

    // alpha == beta: the series short-circuits (z == 0), never overflows.
    const pareto_nbd::ParetoNbdParams equal_params{0.7, 5.0, 0.6, 5.0};
    REQUIRE_FALSE(pareto_nbd::WouldOverflow(equal_params, 0.0));
    REQUIRE_NOTHROW(pareto_nbd::p_alive(equal_params, 0.0, 0.0, 30.0));

    // Larger t_x makes the same extreme alpha/beta ratio easier to converge (the ratio
    // (min+t_x)/(max+t_x) moves toward 1), so it should stop overflowing well before t_x
    // reaches realistic magnitudes.
    REQUIRE_FALSE(pareto_nbd::WouldOverflow(overflow_params, 25.0));
    REQUIRE_NOTHROW(pareto_nbd::p_alive(overflow_params, 0.0, 25.0, 30.0));
}

TEST_CASE("p_alive / expected_purchases reject invalid input", "[forecast]") {
    const pareto_nbd::ParetoNbdParams ok{0.7, 5.0, 0.6, 8.0};
    using pareto_nbd::expected_purchases;
    using pareto_nbd::p_alive;
    REQUIRE_THROWS_AS(p_alive(ok, 3, 41.0, 40.0), std::invalid_argument);  // t_x > T
    REQUIRE_THROWS_AS(p_alive(ok, -1, 1.0, 40.0), std::invalid_argument);  // x < 0
    REQUIRE_THROWS_AS(p_alive(ok, 3, -1.0, 40.0), std::invalid_argument);  // t_x < 0
    REQUIRE_THROWS_AS(p_alive(ok, std::nan(""), 1.0, 40.0), std::invalid_argument);
    REQUIRE_THROWS_AS(p_alive({-0.7, 5.0, 0.6, 8.0}, 3, 20.0, 40.0), std::invalid_argument);
    REQUIRE_THROWS_AS(p_alive({0.7, 0.0, 0.6, 8.0}, 3, 20.0, 40.0), std::invalid_argument);
    REQUIRE_THROWS_AS(
        p_alive({0.7, 5.0, std::numeric_limits<double>::infinity(), 8.0}, 3, 20.0, 40.0),
        std::invalid_argument);
    REQUIRE_THROWS_AS(expected_purchases(ok, 3, 20.0, 40.0, -1.0), std::invalid_argument);
    REQUIRE_THROWS_AS(expected_purchases(ok, 3, 20.0, 40.0, std::nan("")),
                      std::invalid_argument);
}
