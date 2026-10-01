#include "pareto_nbd/worker.hpp"

#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/clv.hpp"
#include "pareto_nbd/cohort_features.hpp"
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/ingest.hpp"

#include <nlohmann/json.hpp>

namespace pareto_nbd {
namespace {

// Forecast horizon for E[repeat purchases in (T, T+horizon]]. Not yet job-configurable --
// this is a single hardcoded default for this phase. 26 weeks (~half a year) is a
// reasonable general-purpose planning horizon and matches the horizon used throughout
// models/forecast_golden.json's non-degenerate cases. A later phase is expected to make
// this a per-job parameter (e.g. supplied on upload) rather than a library-wide constant.
constexpr double kForecastHorizonWeeks = 26.0;

void MarkFailed(drogon::orm::DbClientPtr db, const std::string& job_id, const std::string& reason) {
    db->execSqlSync(
        "UPDATE jobs SET status = 'failed', error_reason = $2, completed_at = now() "
        "WHERE id = $1::uuid",
        job_id, reason);
}

}  // namespace

void ScoreCohortAndWriteResults(const std::string& job_id, drogon::orm::DbClientPtr db,
                                 const CustomerFeatures& cohort, const ParetoNbdParams& params) {
    // Checked ONCE per cohort, not per customer. alpha/beta are population-level
    // parameters (identical for every customer in this cohort); t_x=0 is the
    // hardest-to-converge case for the hypergeometric series inside p_alive, and every
    // customer with x==0 repeat purchases has t_x==0 (no repeat purchase means no
    // recency beyond the first). If this is true, every x==0 customer in the cohort
    // would independently burn the full ~1e6-iteration series cap before throwing
    // ForecastOverflowError -- up to 1-2 hours of wasted compute at 1M customers for an
    // extreme alpha/beta ratio. Checking once here and skipping the full p_alive call
    // for those customers directly avoids that cost entirely. See forecast.hpp's
    // WouldOverflow doc for why this is a sound (never-false-negative) pre-filter.
    const bool zero_repeat_would_overflow = WouldOverflow(params, /*t_x=*/0.0);

    GammaGammaParams gg{};
    std::vector<double> nu;
    bool have_clv = false;
    if (cohort.has_monetary) {
        try {
            gg = fit_gamma_gamma(cohort.x, cohort.m_bar);
            nu = posterior_mean_nu(cohort.x, cohort.m_bar, gg);
            have_clv = true;
        } catch (const std::exception&) {
            // A cohort with no x>0 customers at all can't fit Gamma-Gamma (see clv.hpp)
            // -- per spec §6 this is a per-row/per-cohort limitation, not a hard job
            // failure: fall through and write purchase/P(alive) forecasts without a CLV
            // figure.
        }
    }

    for (size_t i = 0; i < cohort.customer_id.size(); ++i) {
        auto cust_rows = db->execSqlSync(
            "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
            "VALUES ($1::uuid, $2, $3::uuid) "
            "ON CONFLICT (business_id, external_customer_id) DO UPDATE SET external_customer_id = EXCLUDED.external_customer_id "
            "RETURNING id",
            kDefaultBusinessId, cohort.customer_id[i], job_id);
        std::string customer_id = cust_rows[0]["id"].as<std::string>();

        // p_alive and expected_purchases are the real closed-form Pareto/NBD quantities
        // (forecast.hpp, Task 6b, independently verified to ~1e-12 relative accuracy). A
        // customer can still fail to score if this particular (alpha, beta, t_x)
        // combination is beyond the fast series path's reach (ForecastOverflowError) --
        // when that happens we deliberately do NOT write a forecast_results row for this
        // customer rather than fabricate a number or fail the whole job. This customer is
        // simply unscored for this job: Task 10 (not yet implemented) will add a
        // data_quality column and more granular per-row flagging so this is visible to
        // API consumers; for now, skipping the row is the documented, intentional
        // behavior, not a silent bug.
        double p_alive_value = 0.0;
        double expected_purchases_value = 0.0;
        bool scored = false;
        if (cohort.x[i] == 0.0 && zero_repeat_would_overflow) {
            // Pre-filtered: this customer is known (via the single cohort-level check
            // above) to overflow without paying the full series cap individually.
        } else {
            try {
                p_alive_value = p_alive(params, cohort.x[i], cohort.t_x[i], cohort.T_cal[i]);
                expected_purchases_value =
                    expected_purchases(params, cohort.x[i], cohort.t_x[i], cohort.T_cal[i],
                                       kForecastHorizonWeeks, p_alive_value);
                scored = true;
            } catch (const ForecastOverflowError&) {
                // Same documented, intentional skip as the pre-filtered branch above.
            }
        }
        if (!scored) { continue; }

        double clv_point = have_clv ? nu[i] * expected_purchases_value : 0.0;

        nlohmann::json model_params{{"r", params.r}, {"alpha", params.alpha},
                                     {"s", params.s}, {"beta", params.beta}};
        if (have_clv) {
            model_params["gamma_gamma"] = {{"p", gg.p}, {"q", gg.q}, {"v", gg.v}};
        }

        db->execSqlSync(
            "INSERT INTO forecast_results "
            "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, model_params) "
            "VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8::jsonb) "
            "ON CONFLICT (job_id, customer_id) DO NOTHING",
            job_id, customer_id, expected_purchases_value, p_alive_value, clv_point,
            clv_point, clv_point, model_params.dump());
    }
}

void ProcessOneJob(const std::string& job_id, drogon::orm::DbClientPtr db, UploadStorage& storage) {
    db->execSqlSync("UPDATE jobs SET status = 'running' WHERE id = $1::uuid", job_id);

    auto job_rows = db->execSqlSync("SELECT upload_path FROM jobs WHERE id = $1::uuid", job_id);
    if (job_rows.empty()) { return; }  // job vanished; nothing sensible to do
    std::string csv_path = storage.GetPath(job_rows[0]["upload_path"].as<std::string>());

    CustomerFeatures cohort;
    try {
        cohort = ingest_csv(csv_path);
    } catch (const IngestError& e) {
        MarkFailed(db, job_id, e.what());
        return;
    }

    // Everything past ingestion (model load/inference, the closed-form forecast, Gamma-Gamma
    // CLV, and the Postgres writes) is wrapped in one try/catch: none of these failure modes
    // are expected in normal operation, but per spec §6 an unexpected exception here must
    // mark the job failed with a user-facing reason, never crash the worker process or
    // propagate a raw stack trace to the caller/process.
    try {
        // The models directory carries the committed ONNX/scaler artifacts (Phase 1) -- reuse
        // the same PROJECT_MODELS_DIR convention the demo/tests already use.
        AmortizedModel model(std::string(PROJECT_MODELS_DIR) + "/amortizer_mlp.onnx",
                              std::string(PROJECT_MODELS_DIR) + "/amortizer_scalers.json");
        auto features = cohort_features(cohort.x, cohort.t_x, cohort.T_cal);
        auto amortized = model.predict(features);
        const ParetoNbdParams params{amortized.r, amortized.alpha, amortized.s, amortized.beta};

        ScoreCohortAndWriteResults(job_id, db, cohort, params);

        db->execSqlSync(
            "UPDATE jobs SET status = 'done', completed_at = now() WHERE id = $1::uuid", job_id);
    } catch (const std::exception& e) {
        MarkFailed(db, job_id, e.what());
    }
}

}  // namespace pareto_nbd
