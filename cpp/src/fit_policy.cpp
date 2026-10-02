#include "pareto_nbd/fit_policy.hpp"

namespace pareto_nbd {

std::optional<FitMode> ParseFitMode(const std::string& s) {
    if (s == "auto") return FitMode::Auto;
    if (s == "fast") return FitMode::Fast;
    if (s == "mcmc") return FitMode::Mcmc;
    return std::nullopt;
}

std::string ToString(FitMode m) {
    switch (m) {
        case FitMode::Auto: return "auto";
        case FitMode::Fast: return "fast";
        case FitMode::Mcmc: return "mcmc";
    }
    return "auto";
}

FitDecision ChooseFitMethod(FitMode mode, size_t n) {
    switch (mode) {
        case FitMode::Fast:
            return {FitMethod::Amortized, ""};
        case FitMode::Auto:
            if (n >= kAutoMcmcMinCustomers && n <= kAutoMcmcMaxCustomers)
                return {FitMethod::Mcmc, ""};
            return {FitMethod::Amortized, ""};
        case FitMode::Mcmc:
            if (n <= kMcmcMaxCustomers) return {FitMethod::Mcmc, ""};
            return {FitMethod::Amortized,
                    "Cohort has " + std::to_string(n) + " customers, above the " +
                        std::to_string(kMcmcMaxCustomers) +
                        "-customer limit for the high-precision refit - used the fast estimator instead."};
    }
    return {FitMethod::Amortized, ""};
}

}  // namespace pareto_nbd
