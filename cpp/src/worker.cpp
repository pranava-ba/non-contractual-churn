#include "pareto_nbd/worker.hpp"

#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/clv.hpp"
#include "pareto_nbd/cohort_features.hpp"
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/ingest.hpp"

#include <nlohmann/json.hpp>

#include <cmath>
#include <iostream>

namespace pareto_nbd {
namespace {

// Forecast horizon for E[repeat purchases in (T, T+horizon]]. Not yet job-configurable --
// this is a single hardcoded default for this phase. 26 weeks (~half a year) is a
// reasonable general-purpose planning horizon and matches the horizon used throughout
// models/forecast_golden.json's non-degenerate cases. A later phase is expected to make
// this a per-job parameter (e.g. supplied on upload) rather than a library-wide constant.
constexpr double kForecastHorizonWeeks = 26.0;

// Best-effort: marking a job failed can itself fail -- e.g. job_id isn't even a syntactically
// valid UUID (a malformed id pushed onto the queue makes the ::uuid cast throw), or the DB
// connection is the very thing that broke. Either way, the failure is logged and swallowed
// here: ProcessOneJob's contract is that it never throws, and a worker process that exits
// over one bad job stops processing every other job too.
void MarkFailedBestEffort(drogon::orm::DbClientPtr db, const std::string& job_id,
                          const std::string& reason) noexcept {
    try {
        db->execSqlSync(
            "UPDATE jobs SET status = 'failed', error_reason = $2, completed_at = now() "
            "WHERE id = $1::uuid",
            job_id, reason);
    } catch (const std::exception& e) {
        std::cerr << "worker: could not mark job '" << job_id << "' failed (" << e.what()
                  << "); original failure: " << reason << "\n";
    } catch (...) {
        std::cerr << "worker: could not mark job '" << job_id
                  << "' failed (unknown error); original failure: " << reason << "\n";
    }
}

void ProcessOneJobUnguarded(const std::string& job_id, drogon::orm::DbClientPtr db,
                            UploadStorage& storage);

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
        // combination is beyond the fast series path's reach (ForecastOverflowError) -- a
        // genuine NUMERICAL failure where the closed-form math cannot be evaluated. Per
        // Task 10 / spec §6, every customer still gets exactly one forecast_results row:
        // this case is flagged 'forecast_unavailable' with placeholder 0.0 figures (never
        // fabricated/meaningful numbers -- data_quality is the signal to ignore them)
        // rather than silently omitting the row. This is distinct from the
        // 'insufficient_history' flag below, which is a STATISTICAL data-sufficiency
        // signal for x==0 customers whose forecast CAN be computed.
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
                // Same documented, intentional 'forecast_unavailable' flag as the
                // pre-filtered branch above.
            }
        }

        // data_quality: 'ok' for a normal, fully-scored forecast; 'insufficient_history'
        // for a scored-but-low-confidence x==0 (single-transaction) customer per spec §6;
        // 'forecast_unavailable' when the closed-form math itself could not be evaluated
        // (ForecastOverflowError, including the cohort-level pre-filtered case above) --
        // no real forecast numbers exist for this customer, so p_alive/expected_purchases/
        // clv_point are 0.0 placeholders, not real figures.
        std::string data_quality;
        if (!scored) {
            data_quality = "forecast_unavailable";
            p_alive_value = 0.0;
            expected_purchases_value = 0.0;
        } else if (cohort.x[i] == 0.0) {
            data_quality = "insufficient_history";
        } else {
            data_quality = "ok";
        }

        double clv_point = (scored && have_clv) ? nu[i] * expected_purchases_value : 0.0;
        // No conformal interval is fitted in this phase: lower/upper collapse to the point.
        double clv_lower = clv_point;
        double clv_upper = clv_point;

        // posterior_mean_nu returns NaN when the fitted Gamma-Gamma posterior shape is <= 1
        // (q <= 1 for an x==0 customer, p*x+q <= 1 for an x>0 one -- the Inverse-Gamma mean
        // is undefined there, see clv.hpp). NaN must never reach forecast_results: Postgres
        // accepts it into DOUBLE PRECISION, after which it serializes as JSON null (breaking
        // clients reading a number) and as the literal "nan" in the CSV export. Write 0.0
        // placeholders instead and flag the row 'clv_unavailable' -- but only when it would
        // otherwise be 'ok': 'insufficient_history'/'forecast_unavailable' are more specific
        // reasons (and already tell the client not to trust the row), so they are kept.
        if (!std::isfinite(clv_point) || !std::isfinite(clv_lower) || !std::isfinite(clv_upper)) {
            clv_point = 0.0;
            clv_lower = 0.0;
            clv_upper = 0.0;
            if (data_quality == "ok") {
                data_quality = "clv_unavailable";
            }
        }

        nlohmann::json model_params{{"r", params.r}, {"alpha", params.alpha},
                                     {"s", params.s}, {"beta", params.beta}};
        if (have_clv) {
            model_params["gamma_gamma"] = {{"p", gg.p}, {"q", gg.q}, {"v", gg.v}};
        }

        db->execSqlSync(
            "INSERT INTO forecast_results "
            "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, model_params, data_quality) "
            "VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8::jsonb, $9) "
            "ON CONFLICT (job_id, customer_id) DO NOTHING",
            job_id, customer_id, expected_purchases_value, p_alive_value, clv_point,
            clv_lower, clv_upper, model_params.dump(), data_quality);
    }
}

void ProcessOneJob(const std::string& job_id, drogon::orm::DbClientPtr db, UploadStorage& storage) {
    if (!db) {
        std::cerr << "worker: no database client, cannot process job '" << job_id << "'\n";
        return;
    }
    // EVERY step -- the 'running' status update, the upload_path lookup, ingestion, model
    // load/inference, forecasting, CLV and the Postgres writes -- runs inside this one
    // try/catch. Before this, the status update and the SELECT ran outside any try, so a
    // malformed job id on the queue (::uuid cast error) escaped ProcessOneJob and killed the
    // whole worker process. Per spec Sec6 an unexpected exception marks the job failed with a
    // reason (best-effort -- see MarkFailedBestEffort), never crashes the worker.
    try {
        ProcessOneJobUnguarded(job_id, db, storage);
    } catch (const std::exception& e) {
        std::cerr << "worker: job '" << job_id << "' failed: " << e.what() << "\n";
        MarkFailedBestEffort(db, job_id, e.what());
    } catch (...) {
        std::cerr << "worker: job '" << job_id << "' failed with a non-standard exception\n";
        MarkFailedBestEffort(db, job_id, "internal error");
    }
}

namespace {

void ProcessOneJobUnguarded(const std::string& job_id, drogon::orm::DbClientPtr db,
                            UploadStorage& storage) {
    db->execSqlSync("UPDATE jobs SET status = 'running' WHERE id = $1::uuid", job_id);

    auto job_rows = db->execSqlSync("SELECT upload_path FROM jobs WHERE id = $1::uuid", job_id);
    if (job_rows.empty()) { return; }  // job vanished; nothing sensible to do
    std::string csv_path = storage.GetPath(job_rows[0]["upload_path"].as<std::string>());

    CustomerFeatures cohort;
    try {
        cohort = ingest_csv(csv_path);
    } catch (const IngestError& e) {
        // A bad upload is an expected, user-facing failure -- recorded with ingest's own
        // message. Anything else thrown from here on propagates to ProcessOneJob's catch-all.
        MarkFailedBestEffort(db, job_id, e.what());
        return;
    }

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
}

}  // namespace

}  // namespace pareto_nbd
