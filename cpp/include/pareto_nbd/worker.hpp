#pragma once
#include <drogon/orm/DbClient.h>
#include <string>
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd {

// Loads the job's CSV, runs the full estimation pipeline (ingest -> amortized Pareto/NBD ->
// closed-form P(alive)/E[x*] -> Gamma-Gamma CLV), writes one forecast_results row per customer
// (always, regardless of scoring success), and marks the job done or failed. Never throws --
// every step (including the initial status update and upload_path lookup) runs inside one
// catch-all; a failure is recorded as the job's error_reason (spec §6: worker exceptions mark
// the job failed with a user-facing reason string, never a raw stack trace). Marking the job
// failed is itself best-effort: if that also fails (e.g. job_id is not a valid UUID, or the
// database is unreachable) the error is logged to stderr and swallowed.
void ProcessOneJob(const std::string& job_id, drogon::orm::DbClientPtr db, UploadStorage& storage);

// The per-cohort scoring + write step ProcessOneJob runs once it has already-ingested
// features and an already-predicted population ParetoNbdParams (from AmortizedModel). Split
// out from ProcessOneJob so tests can exercise the overflow and CLV logic directly with
// hand-picked parameters (e.g. models/forecast_golden.json's known overflow case), without
// depending on the real ONNX model happening to predict that exact (alpha, beta) from some
// crafted CSV. Writes `customers` and `forecast_results` rows for job_id (one per customer,
// always); does not touch the job's own status (ProcessOneJob marks it done/failed around this
// call). Never throws for a per-customer ForecastOverflowError -- that customer's
// forecast_results row is inserted with data_quality='forecast_unavailable' and placeholder
// 0.0 values (see worker.cpp); additionally, x==0 customers who score successfully get
// data_quality='insufficient_history'. A customer whose Gamma-Gamma CLV is not finite
// (posterior_mean_nu's documented NaN when the posterior shape is <= 1) gets 0.0 CLV
// placeholders and, if they would otherwise have been 'ok', data_quality='clv_unavailable'
// (a more specific existing flag is kept). All others get 'ok'. An unrelated unexpected
// exception (e.g. a DB error) propagates to the caller.
void ScoreCohortAndWriteResults(const std::string& job_id, drogon::orm::DbClientPtr db,
                                 const CustomerFeatures& cohort, const ParetoNbdParams& params);

}  // namespace pareto_nbd
