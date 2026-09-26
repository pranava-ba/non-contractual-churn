#pragma once
#include <vector>

namespace pareto_nbd {

struct GammaGammaParams {
    double p;
    double q;
    double v;
};

// Analytical posterior mean of a customer's mean transaction value nu_i,
// given fitted Gamma-Gamma parameters. Mirrors the formula used in
// clv.py's sample_posterior_nu docstring: shape = p*x_i+q (or q if x_i==0),
// scale = p*x_i*m_obs_i+v (or v if x_i==0), posterior mean = scale/(shape-1).
// Pure closed-form arithmetic — no optimizer, no RNG.
std::vector<double> posterior_mean_nu(const std::vector<double>& x,
                                       const std::vector<double>& m_obs,
                                       const GammaGammaParams& params);

// CLV_i = x_star_i * nu_i * exp(-discount_rate), elementwise over an
// (n_draws x N) grid. Mirrors clv.predict_clv_distribution exactly.
std::vector<std::vector<double>> predict_clv_distribution(
    const std::vector<std::vector<double>>& pred_x_star,
    const std::vector<std::vector<double>>& nu_draws,
    double discount_rate);

// Fits (p, q, v) by maximum likelihood via Nelder-Mead, mirroring
// clv.fit_gamma_gamma exactly: filters to customers with x>0 and
// m_obs>0, optimizes the same log-space negative log-likelihood from the
// same x0 = log([2.0, 2.0, 10.0]) starting point. A from-scratch
// optimizer is not expected to land on bit-identical (p,q,v) to SciPy's
// — see the plan's Global Constraints for the tolerance this is checked
// against.
GammaGammaParams fit_gamma_gamma(const std::vector<double>& x, const std::vector<double>& m_obs);

}  // namespace pareto_nbd
