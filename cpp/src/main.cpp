#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/cohort_features.hpp"
#include "pareto_nbd/version.hpp"

// Demo entry point: loads one of the fixed sample cohorts used by the test
// suite (models/amortizer_golden.json) and runs it through the same
// pipeline the tests check — raw per-customer purchase history in,
// Pareto/NBD parameters out — printed in plain terms instead of pass/fail
// assertions.
int main() {
    std::cout << "pareto-nbd-inference v" << pareto_nbd::version() << "\n\n";

    const std::string models_dir = PROJECT_MODELS_DIR;

    pareto_nbd::AmortizedModel model(models_dir + "/amortizer_mlp.onnx",
                                      models_dir + "/amortizer_scalers.json");

    std::ifstream f(models_dir + "/amortizer_golden.json");
    nlohmann::json cases;
    f >> cases;

    const auto& c = cases[0];
    std::vector<double> x = c["x"].get<std::vector<double>>();
    std::vector<double> t_x = c["t_x"].get<std::vector<double>>();
    std::vector<double> T_cal = c["T_cal"].get<std::vector<double>>();

    std::cout << "Sample cohort: " << x.size() << " customers, "
              << T_cal[0] << "-week calibration period\n";
    std::cout << "(this is real per-customer transaction data: each customer's\n"
              << " purchase count, time of last purchase, and observation window)\n\n";

    auto features = pareto_nbd::cohort_features(x, t_x, T_cal);
    auto params = model.predict(features);

    std::cout << std::fixed << std::setprecision(4);
    std::cout << "Estimated Pareto/NBD parameters (from the C++ model):\n";
    std::cout << "  r     = " << params.r     << "   \\\n";
    std::cout << "  alpha = " << params.alpha << "    } shape the purchase-rate distribution across customers\n";
    std::cout << "  s     = " << params.s     << "   \\\n";
    std::cout << "  beta  = " << params.beta  << "    } shape the dropout-rate distribution across customers\n\n";

    std::cout << "Python's answer for the same cohort, for comparison:\n";
    std::cout << "  r     = " << c["r"].get<double>() << "\n";
    std::cout << "  alpha = " << c["alpha"].get<double>() << "\n";
    std::cout << "  s     = " << c["s"].get<double>() << "\n";
    std::cout << "  beta  = " << c["beta"].get<double>() << "\n\n";

    std::cout << "These four numbers are the whole Pareto/NBD model for this cohort.\n"
              << "Turning them into a per-customer forecast (expected future purchases,\n"
              << "probability still active, CLV) is Phase 2 of the plan — not built yet.\n";

    return 0;
}
