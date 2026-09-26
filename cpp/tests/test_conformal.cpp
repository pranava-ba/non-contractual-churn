#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <vector>
#include "pareto_nbd/conformal.hpp"

TEST_CASE("randomized_pit matches the Python reference", "[conformal]") {
    std::vector<std::vector<double>> pred = {
        {0, 1, 2, 5},
        {1, 1, 3, 6},
        {1, 2, 2, 4},
        {2, 2, 2, 5},
        {0, 3, 1, 7},
        {1, 1, 2, 5},
    };
    std::vector<double> y = {1.0, 2.0, 2.0, 5.0};
    std::vector<double> tie_break = {0.3, 0.6, 0.9, 0.1};

    auto pit = pareto_nbd::randomized_pit(pred, y, tie_break);

    std::vector<double> expected = {
        0.4833333333333333, 0.7, 0.7666666666666666, 0.21666666666666667,
    };
    REQUIRE(pit.size() == expected.size());
    for (size_t i = 0; i < expected.size(); ++i) {
        REQUIRE(pit[i] == Catch::Approx(expected[i]).epsilon(1e-9));
    }
}
