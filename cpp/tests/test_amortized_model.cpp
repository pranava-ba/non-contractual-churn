#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <array>
#include <fstream>
#include <nlohmann/json.hpp>
#include "pareto_nbd/amortized_model.hpp"

TEST_CASE("AmortizedModel matches Python golden-file cases", "[amortized_model]") {
    pareto_nbd::AmortizedModel model(
        std::string(PROJECT_MODELS_DIR) + "/amortizer_mlp.onnx",
        std::string(PROJECT_MODELS_DIR) + "/amortizer_scalers.json");

    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/amortizer_golden.json");
    nlohmann::json cases;
    f >> cases;

    REQUIRE(cases.size() == 3);
    for (const auto& c : cases) {
        std::array<double, 11> features{};
        for (size_t i = 0; i < 11; ++i) features[i] = c["features"][i].get<double>();

        auto pred = model.predict(features);

        REQUIRE(pred.r == Catch::Approx(c["r"].get<double>()).epsilon(1e-2));
        REQUIRE(pred.alpha == Catch::Approx(c["alpha"].get<double>()).epsilon(1e-2));
        REQUIRE(pred.s == Catch::Approx(c["s"].get<double>()).epsilon(1e-2));
        REQUIRE(pred.beta == Catch::Approx(c["beta"].get<double>()).epsilon(1e-2));
    }
}
