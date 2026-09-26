#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <vector>
#include "pareto_nbd/nelder_mead.hpp"

TEST_CASE("nelder_mead finds the minimum of a simple quadratic", "[nelder_mead]") {
    // f(x, y) = (x - 3)^2 + (y + 2)^2 + 5, minimum at (3, -2), fval 5.
    auto objective = [](const std::vector<double>& v) {
        double dx = v[0] - 3.0;
        double dy = v[1] + 2.0;
        return dx * dx + dy * dy + 5.0;
    };
    auto result = pareto_nbd::nelder_mead(objective, {0.0, 0.0});

    REQUIRE(result.x[0] == Catch::Approx(3.0).margin(1e-3));
    REQUIRE(result.x[1] == Catch::Approx(-2.0).margin(1e-3));
    REQUIRE(result.fval == Catch::Approx(5.0).margin(1e-3));
}
