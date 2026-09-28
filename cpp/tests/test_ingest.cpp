#include <catch2/catch_test_macros.hpp>
#include <string>
#include "pareto_nbd/ingest.hpp"

TEST_CASE("ingest_csv smoke test: reads the sample fixture without throwing", "[ingest]") {
    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");
    REQUIRE(features.customer_id.size() == 3);   // customers A, B, C
}

TEST_CASE("ingest_csv rejects a missing required column", "[ingest][errors]") {
    REQUIRE_THROWS_AS(
        pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_bad_missing_column.csv"),
        pareto_nbd::IngestError);
}

TEST_CASE("ingest_csv rejects an empty transaction log", "[ingest][errors]") {
    REQUIRE_THROWS_AS(
        pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_bad_empty.csv"),
        pareto_nbd::IngestError);
}

TEST_CASE("ingest_csv rejects a nonexistent file", "[ingest][errors]") {
    REQUIRE_THROWS_AS(pareto_nbd::ingest_csv("does_not_exist.csv"), pareto_nbd::IngestError);
}

TEST_CASE("ingest_csv detects the optional amount column", "[ingest]") {
    auto with_money = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");
    REQUIRE(with_money.has_monetary);

    auto without_money = pareto_nbd::ingest_csv(
        std::string(PROJECT_MODELS_DIR) + "/ingest_sample_no_money.csv");
    REQUIRE_FALSE(without_money.has_monetary);
}
