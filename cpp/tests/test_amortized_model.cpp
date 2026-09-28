#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <array>
#include <fstream>
#include <vector>
#include <nlohmann/json.hpp>
#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/cohort_features.hpp"

TEST_CASE("AmortizedModel matches Python golden-file cases", "[amortized_model]") {
    pareto_nbd::AmortizedModel model(
        std::string(PROJECT_MODELS_DIR) + "/amortizer_mlp.onnx",
        std::string(PROJECT_MODELS_DIR) + "/amortizer_scalers.json");

    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/amortizer_golden.json");
    nlohmann::json cases;
    f >> cases;

    REQUIRE(cases.size() == 3);
    for (const auto& c : cases) {
        // Half 1: predict() alone, from the golden precomputed features.
        std::array<double, 11> features{};
        for (size_t i = 0; i < 11; ++i) features[i] = c["features"][i].get<double>();

        auto pred = model.predict(features);

        REQUIRE(pred.r == Catch::Approx(c["r"].get<double>()).epsilon(1e-4));
        REQUIRE(pred.alpha == Catch::Approx(c["alpha"].get<double>()).epsilon(1e-4));
        REQUIRE(pred.s == Catch::Approx(c["s"].get<double>()).epsilon(1e-4));
        REQUIRE(pred.beta == Catch::Approx(c["beta"].get<double>()).epsilon(1e-4));

        // Half 2: the full raw-data pipeline, cohort_features() -> predict(),
        // cross-checked against the same golden case end to end.
        std::vector<double> x = c["x"].get<std::vector<double>>();
        std::vector<double> t_x = c["t_x"].get<std::vector<double>>();
        std::vector<double> T_cal = c["T_cal"].get<std::vector<double>>();

        auto computed_features = pareto_nbd::cohort_features(x, t_x, T_cal);

        for (size_t i = 0; i < 11; ++i) {
            REQUIRE(computed_features[i] ==
                    Catch::Approx(c["features"][i].get<double>()).epsilon(1e-9));
        }

        auto pred_from_raw = model.predict(computed_features);

        REQUIRE(pred_from_raw.r == Catch::Approx(c["r"].get<double>()).epsilon(1e-4));
        REQUIRE(pred_from_raw.alpha == Catch::Approx(c["alpha"].get<double>()).epsilon(1e-4));
        REQUIRE(pred_from_raw.s == Catch::Approx(c["s"].get<double>()).epsilon(1e-4));
        REQUIRE(pred_from_raw.beta == Catch::Approx(c["beta"].get<double>()).epsilon(1e-4));
    }
}
