// cpp/src/main.cpp
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/clv.hpp"
#include "pareto_nbd/cohort_features.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/version.hpp"

// Demo entry point: reads a real transaction-log CSV (the same fixture the
// test suite golden-checks against) end to end -- Arrow ingestion ->
// amortized Pareto/NBD parameters -> Gamma-Gamma CLV -- printed in plain
// terms instead of pass/fail assertions. This is the first point in the
// build where all three ported stages (Phase 1, Phase 2, Phase 3) run
// together on the same real input.
int main() {
    std::cout << "pareto-nbd-inference v" << pareto_nbd::version() << "\n\n";

    const std::string models_dir = PROJECT_MODELS_DIR;

    auto cohort = pareto_nbd::ingest_csv(models_dir + "/ingest_sample.csv");
    std::cout << "Ingested " << models_dir << "/ingest_sample.csv: "
              << cohort.customer_id.size() << " customers"
              << (cohort.has_monetary ? " (with spend data)\n" : " (no spend data)\n");

    pareto_nbd::AmortizedModel model(models_dir + "/amortizer_mlp.onnx",
                                      models_dir + "/amortizer_scalers.json");
    auto features = pareto_nbd::cohort_features(cohort.x, cohort.t_x, cohort.T_cal);
    auto params = model.predict(features);

    std::cout << std::fixed << std::setprecision(4);
    std::cout << "\nEstimated Pareto/NBD parameters:\n";
    std::cout << "  r=" << params.r << " alpha=" << params.alpha
              << " s=" << params.s << " beta=" << params.beta << "\n";

    if (cohort.has_monetary) {
        auto gg = pareto_nbd::fit_gamma_gamma(cohort.x, cohort.m_bar);
        auto nu = pareto_nbd::posterior_mean_nu(cohort.x, cohort.m_bar, gg);
        std::cout << "\nGamma-Gamma spend model: p=" << gg.p << " q=" << gg.q << " v=" << gg.v << "\n";
        std::cout << "\nPer-customer posterior mean spend per transaction:\n";
        for (size_t i = 0; i < cohort.customer_id.size(); ++i) {
            std::cout << "  " << cohort.customer_id[i] << ": nu=" << nu[i]
                      << "  (observed x=" << cohort.x[i] << ", m_bar=" << cohort.m_bar[i] << ")\n";
        }
    }

    std::cout << "\nTurning this into a full CLV forecast (expected future purchases x\n"
              << "posterior mean spend, with a conformal-calibrated interval) wires\n"
              << "together predict_clv_distribution + the conformal-calibration stage\n"
              << "already ported in Phase 2 -- left as an exercise for the Drogon API\n"
              << "worker (Phase 4), which is where this pipeline actually gets called\n"
              << "per uploaded job rather than on one hardcoded demo file.\n";

    return 0;
}
