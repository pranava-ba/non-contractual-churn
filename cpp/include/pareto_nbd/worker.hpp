#pragma once
#include <drogon/orm/DbClient.h>
#include <string>
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd {

// Loads the job's CSV, runs the full estimation pipeline (ingest -> amortized Pareto/NBD ->
// closed-form P(alive)/E[x*] -> Gamma-Gamma CLV), writes one forecast_results row per scored
// customer, and marks the job done or failed. Never throws -- all failure modes are caught
// internally and recorded as the job's error_reason (spec §6: worker exceptions mark the job
// failed with a user-facing reason string, never a raw stack trace).
void ProcessOneJob(const std::string& job_id, drogon::orm::DbClientPtr db, UploadStorage& storage);

// The per-cohort scoring + write step ProcessOneJob runs once it has already-ingested
// features and an already-predicted population ParetoNbdParams (from AmortizedModel). Split
// out from ProcessOneJob so tests can exercise the overflow-skip and CLV logic directly with
// hand-picked parameters (e.g. models/forecast_golden.json's known overflow case), without
// depending on the real ONNX model happening to predict that exact (alpha, beta) from some
// crafted CSV. Writes `customers` and `forecast_results` rows for job_id; does not touch the
// job's own status (ProcessOneJob marks it done/failed around this call). Never throws for a
// per-customer ForecastOverflowError -- that customer's forecast_results row is simply
// skipped (see worker.cpp); an unrelated unexpected exception (e.g. a DB error) propagates to
// the caller.
void ScoreCohortAndWriteResults(const std::string& job_id, drogon::orm::DbClientPtr db,
                                 const CustomerFeatures& cohort, const ParetoNbdParams& params);

}  // namespace pareto_nbd
