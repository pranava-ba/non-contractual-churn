#include "pareto_nbd/clv.hpp"

#include <cmath>

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

}  // namespace pareto_nbd
