#pragma once
#include <stdexcept>
#include <string>

namespace pareto_nbd {

// Pareto/NBD population parameters (Fader & Hardie 2005 parameterisation):
// purchase rate lambda ~ Gamma(r, alpha), dropout rate mu ~ Gamma(s, beta).
struct ParetoNbdParams {
    double r;
    double alpha;
    double s;
    double beta;
};

// Thrown when the fast closed-form path cannot evaluate a customer to full double
// precision. This is a known, documented MVP limitation (see forecast.cpp), not a bug:
// it happens only when min(alpha,beta)+t_x is tiny relative to max(alpha,beta)+t_x
// (ratio below ~4e-5, e.g. alpha/beta = 1e-8 for a customer with t_x = 0), where the
// hypergeometric series cannot converge within its term cap, or if the final result
// is non-finite. Callers (the worker) should record such a customer as unscored
// rather than fail the whole cohort.
class ForecastOverflowError : public std::runtime_error {
public:
    explicit ForecastOverflowError(const std::string& msg) : std::runtime_error(msg) {}
};

// Exact closed-form P(customer alive at T | x, t_x, T; params)
// (Schmittlein, Morrison & Colombo 1987). Port of src/forecast_closed_form.py::p_alive.
// x = repeat purchases, t_x = recency, T = observed length (acquisition-relative).
// Throws std::invalid_argument unless params are finite and > 0, x >= 0 and
// 0 <= t_x <= T (all finite); throws ForecastOverflowError as documented above.
double p_alive(const ParetoNbdParams& params, double x, double t_x, double T);

// Exact closed-form E[repeat purchases in (T, T + horizon] | x, t_x, T; params).
// Port of src/forecast_closed_form.py::expected_purchases_exact (NOT the biased
// expected_purchases approximation):
//   p_alive * (r+x)/(alpha+T) * (beta+T)/(s-1) * [1 - ((beta+T)/(beta+T+h))^(s-1)],
// with the s -> 1 removable singularity handled via expm1. Same throws as p_alive,
// plus std::invalid_argument unless horizon is finite and >= 0.
double expected_purchases(const ParetoNbdParams& params, double x, double t_x, double T,
                          double horizon);

}  // namespace pareto_nbd
