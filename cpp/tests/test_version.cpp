#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/version.hpp"

TEST_CASE("version reports the expected string", "[version]") {
    REQUIRE(pareto_nbd::version() == "0.1.0");
}
