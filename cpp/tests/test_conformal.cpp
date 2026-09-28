#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <stdexcept>
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

TEST_CASE("randomized_pit throws on invalid input", "[conformal]") {
    std::vector<std::vector<double>> pred = {{0, 1, 2, 5}, {1, 1, 3, 6}};
    std::vector<double> y = {1.0, 2.0, 2.0, 5.0};
    std::vector<double> tie_break_wrong_size = {0.3, 0.6};
    std::vector<double> tie_break_ok = {0.3, 0.6, 0.9, 0.1};
    std::vector<std::vector<double>> pred_row_mismatch = {{0, 1, 2, 5}, {1, 1, 3}};

    REQUIRE_THROWS_AS(pareto_nbd::randomized_pit(pred, y, tie_break_wrong_size), std::invalid_argument);
    REQUIRE_THROWS_AS(
        pareto_nbd::randomized_pit(std::vector<std::vector<double>>{}, y, tie_break_ok),
        std::invalid_argument);
    REQUIRE_THROWS_AS(pareto_nbd::randomized_pit(pred_row_mismatch, y, tie_break_ok), std::invalid_argument);
}

TEST_CASE("apply_conformal_warp matches the Python reference", "[conformal]") {
    std::vector<double> u = {0.1, 0.9, 0.3, 0.5, 0.7, 0.2, 0.95, 0.05, 0.6, 0.4};
    std::vector<double> p = {0.25, 0.75, 0.5};
    std::vector<std::vector<double>> pred_test = {
        {1, 2, 3}, {4, 5, 6}, {7, 8, 9}, {10, 11, 12}, {13, 14, 15},
    };

    auto out = pareto_nbd::apply_conformal_warp(u, p, pred_test);

    std::vector<std::vector<double>> expected = {
        {4.0, 5.0, 6.0}, {10.0, 11.0, 12.0}, {7.0, 8.0, 9.0},
    };
    REQUIRE(out.size() == expected.size());
    for (size_t k = 0; k < expected.size(); ++k) {
        REQUIRE(out[k].size() == expected[k].size());
        for (size_t i = 0; i < expected[k].size(); ++i) {
            REQUIRE(out[k][i] == Catch::Approx(expected[k][i]).epsilon(1e-9));
        }
    }
}

TEST_CASE("apply_conformal_warp throws on invalid input", "[conformal]") {
    std::vector<double> u = {0.1, 0.9, 0.3, 0.5, 0.7};
    std::vector<double> p_ok = {0.25, 0.75};
    std::vector<double> p_out_of_range = {0.25, 1.5};
    std::vector<double> p_negative = {-0.1, 0.5};
    std::vector<std::vector<double>> pred_test = {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}};
    std::vector<std::vector<double>> pred_test_empty = {};

    REQUIRE_THROWS_AS(
        pareto_nbd::apply_conformal_warp(std::vector<double>{}, p_ok, pred_test), std::invalid_argument);
    REQUIRE_THROWS_AS(pareto_nbd::apply_conformal_warp(u, p_ok, pred_test_empty), std::invalid_argument);
    REQUIRE_THROWS_AS(pareto_nbd::apply_conformal_warp(u, p_out_of_range, pred_test), std::invalid_argument);
    REQUIRE_THROWS_AS(pareto_nbd::apply_conformal_warp(u, p_negative, pred_test), std::invalid_argument);
}
