#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <algorithm>
#include <fstream>
#include <string>
#include <nlohmann/json.hpp>
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

namespace {

// Finds the CustomerFeatures entry for a given id, or fails the test.
size_t index_of(const pareto_nbd::CustomerFeatures& f, const std::string& cust) {
    auto it = std::find(f.customer_id.begin(), f.customer_id.end(), cust);
    REQUIRE(it != f.customer_id.end());
    return static_cast<size_t>(it - f.customer_id.begin());
}

}  // namespace

TEST_CASE("ingest_csv matches the Python golden file (default as_of)", "[ingest][golden]") {
    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");

    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/ingest_golden.json");
    nlohmann::json golden;
    f >> golden;

    REQUIRE(features.has_monetary);
    REQUIRE(features.customer_id.size() == golden["customers"].size());

    for (const auto& c : golden["customers"]) {
        size_t i = index_of(features, c["cust"].get<std::string>());
        REQUIRE(features.x[i] == Catch::Approx(c["x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.t_x[i] == Catch::Approx(c["t_x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.T_cal[i] == Catch::Approx(c["T_cal"].get<double>()).epsilon(1e-9));
        REQUIRE(features.m_bar[i] == Catch::Approx(c["m_bar"].get<double>()).epsilon(1e-9));
    }
}

TEST_CASE("ingest_csv matches the Python golden file (explicit as_of)", "[ingest][golden]") {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/ingest_golden_as_of.json");
    nlohmann::json golden;
    f >> golden;
    std::string as_of = golden["as_of"].get<std::string>();

    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv", as_of);

    REQUIRE(features.customer_id.size() == golden["customers"].size());
    for (const auto& c : golden["customers"]) {
        size_t i = index_of(features, c["cust"].get<std::string>());
        REQUIRE(features.x[i] == Catch::Approx(c["x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.t_x[i] == Catch::Approx(c["t_x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.T_cal[i] == Catch::Approx(c["T_cal"].get<double>()).epsilon(1e-9));
        REQUIRE(features.m_bar[i] == Catch::Approx(c["m_bar"].get<double>()).epsilon(1e-9));
    }
}
