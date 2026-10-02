#pragma once
#include <cstddef>
#include <optional>
#include <string>

namespace pareto_nbd {

// How the user asked a job to be fitted. Stored verbatim in jobs.fit_mode.
enum class FitMode { Auto, Fast, Mcmc };
// What the worker actually used. Stored in jobs.fit_method.
enum class FitMethod { Amortized, Mcmc };

// auto = MCMC only for cohorts big enough for it to be meaningful and small enough to be quick.
inline constexpr size_t kAutoMcmcMinCustomers = 50;
inline constexpr size_t kAutoMcmcMaxCustomers = 2000;
// Hard ceiling even for an explicit request: the Gibbs sampler is O(draws x customers) in numpy.
inline constexpr size_t kMcmcMaxCustomers = 20000;

std::optional<FitMode> ParseFitMode(const std::string& s);
std::string ToString(FitMode m);

struct FitDecision {
    FitMethod method;
    std::string note;  // non-empty only when the user asked for MCMC and did not get it
};

FitDecision ChooseFitMethod(FitMode mode, size_t n_customers);

}  // namespace pareto_nbd
