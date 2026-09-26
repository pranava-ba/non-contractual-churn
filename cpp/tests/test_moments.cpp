#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include "pareto_nbd/moments.hpp"

TEST_CASE("moments_to_gamma matches the Python reference", "[moments]") {
    auto [shape, rate] = pareto_nbd::moments_to_gamma(0.15, 1.3);
    REQUIRE(shape == Catch::Approx(0.5917159763313609).epsilon(1e-9));
    REQUIRE(rate == Catch::Approx(3.944773175542406).epsilon(1e-9));
}
