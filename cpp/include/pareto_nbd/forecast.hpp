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
//
// This overload recomputes p_alive internally -- use it only when the caller does not
// already need p_alive separately. A caller (e.g. the worker) that needs both p_alive and
// expected_purchases for the same customer should call p_alive() once and pass the result
// to the overload below instead, to avoid paying the (potentially expensive, series-based)
// p_alive computation twice.
double expected_purchases(const ParetoNbdParams& params, double x, double t_x, double T,
                          double horizon);

// Same as above, but skips the internal p_alive(...) recomputation and uses
// precomputed_p_alive directly (the value the caller already obtained from a separate
// p_alive(params, x, t_x, T) call). x, t_x, T and params are still validated, and a
// non-finite result still throws ForecastOverflowError -- only the expensive hypergeometric
// series inside p_alive is skipped.
double expected_purchases(const ParetoNbdParams& params, double x, double t_x, double T,
                          double horizon, double precomputed_p_alive);

// Cheap O(1) check for whether p_alive/expected_purchases would hit ForecastOverflowError
// for this (params, t_x) combination, without running the full hypergeometric series.
//
// alpha and beta are POPULATION-level parameters (identical for every customer in a
// cohort), and the overflow condition is driven almost entirely by them and t_x -- x only
// enters the series' convergence rate as a minor secondary correction. t_x = 0 is the
// hardest-to-converge case (every zero-repeat customer in a cohort shares it), so callers
// (the worker) should check this ONCE per cohort with t_x = 0 rather than letting every
// affected customer independently pay the full series-cap cost before throwing.
//
// Implementation note: this reuses the exact convergence-ratio bound log_series()'s loop
// relies on internally (see forecast.cpp) -- term_n <= z^n and running sum >= 1 -- solved in
// closed form for the term count needed to converge, instead of iterating. Because both of
// those bounds are conservative (the real series converges at least as fast and the real
// running sum is at least 1), WouldOverflow==false is a rigorous guarantee that p_alive will
// not throw for ANY x at this t_x; WouldOverflow==true is the conservative direction for an
// O(1) pre-filter (it may rarely flag a customer that, with the exact x-dependent
// correction, would not actually have overflowed) but never misses a real overflow.
bool WouldOverflow(const ParetoNbdParams& params, double t_x);

}  // namespace pareto_nbd
