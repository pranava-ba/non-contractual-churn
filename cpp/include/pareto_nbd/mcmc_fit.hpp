#pragma once
#include <string>
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd {

struct McmcFitResult {
    bool ok = false;
    ParetoNbdParams params{};
    std::string draws_key;  // storage key of the saved posterior draws (.npz), empty if none
    std::string note;       // user-facing reason, set when !ok
};

// Fits Pareto/NBD with the Python Gibbs sampler (src/mcmc_cli.py) in a subprocess. Never
// throws for an MCMC-side problem (no Python, timeout, non-zero exit, unparsable or
// non-finite output): returns ok=false with a note so the caller can fall back to the
// amortized fit. Files live under storage keys mcmc/<job_id>_{cohort.csv,fit.json,draws.npz}.
// Env overrides: PARETO_PYTHON, PARETO_MCMC_CLI, PARETO_MCMC_TIMEOUT_S.
McmcFitResult RunMcmcFit(const std::string& job_id, const CustomerFeatures& cohort,
                         UploadStorage& storage);

}  // namespace pareto_nbd
