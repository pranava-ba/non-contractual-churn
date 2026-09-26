#include "pareto_nbd/clv.hpp"

#include <cmath>

#include "pareto_nbd/nelder_mead.hpp"

namespace pareto_nbd {

std::vector<double> posterior_mean_nu(const std::vector<double>& x,
                                       const std::vector<double>& m_obs,
                                       const GammaGammaParams& params) {
    std::vector<double> out(x.size());
    for (size_t i = 0; i < x.size(); ++i) {
        double shape, scale;
        if (x[i] > 0.0) {
            shape = params.p * x[i] + params.q;
            scale = params.p * x[i] * m_obs[i] + params.v;
        } else {
            shape = params.q;
            scale = params.v;
        }
        out[i] = scale / (shape - 1.0);
    }
    return out;
}

std::vector<std::vector<double>> predict_clv_distribution(
    const std::vector<std::vector<double>>& pred_x_star,
    const std::vector<std::vector<double>>& nu_draws,
    double discount_rate) {
    double dfactor = std::exp(-discount_rate);
    std::vector<std::vector<double>> out(pred_x_star.size());
    for (size_t d = 0; d < pred_x_star.size(); ++d) {
        out[d].resize(pred_x_star[d].size());
        for (size_t i = 0; i < pred_x_star[d].size(); ++i) {
            out[d][i] = pred_x_star[d][i] * nu_draws[d][i] * dfactor;
        }
    }
    return out;
}

namespace {

double gamma_gamma_neg_loglik(const std::vector<double>& log_params,
                               const std::vector<double>& x_val,
                               const std::vector<double>& m_val) {
    double p = std::exp(log_params[0]);
    double q = std::exp(log_params[1]);
    double v = std::exp(log_params[2]);

    double ll = 0.0;
    for (size_t i = 0; i < x_val.size(); ++i) {
        double xi = x_val[i];
        double mi = m_val[i];
        ll += std::lgamma(p * xi + q) - std::lgamma(p * xi) - std::lgamma(q)
              + q * std::log(v) + (p * xi - 1.0) * std::log(mi)
              + (p * xi) * std::log(p * xi)
              - (p * xi + q) * std::log(p * xi * mi + v);
    }
    return -ll;
}

}  // namespace

GammaGammaParams fit_gamma_gamma(const std::vector<double>& x, const std::vector<double>& m_obs) {
    std::vector<double> x_val, m_val;
    for (size_t i = 0; i < x.size(); ++i) {
        if (x[i] > 0.0 && m_obs[i] > 0.0) {
            x_val.push_back(x[i]);
            m_val.push_back(m_obs[i]);
        }
    }

    auto objective = [&](const std::vector<double>& log_params) {
        return gamma_gamma_neg_loglik(log_params, x_val, m_val);
    };

    std::vector<double> x0 = {std::log(2.0), std::log(2.0), std::log(10.0)};
    auto result = nelder_mead(objective, x0);

    return {std::exp(result.x[0]), std::exp(result.x[1]), std::exp(result.x[2])};
}

}  // namespace pareto_nbd
