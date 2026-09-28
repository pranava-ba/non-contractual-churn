#include <catch2/catch_test_macros.hpp>
#include <string>
#include "pareto_nbd/ingest.hpp"

TEST_CASE("ingest_csv smoke test: reads the sample fixture without throwing", "[ingest]") {
    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");
    REQUIRE(features.customer_id.size() == 3);   // customers A, B, C
}
