#include "pareto_nbd/cohort_features.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace pareto_nbd {
namespace {

double mean_of(const std::vector<double>& v) {
    if (v.empty()) return 0.0;
    return std::accumulate(v.begin(), v.end(), 0.0) / static_cast<double>(v.size());
}

// numpy.quantile's default ("linear") interpolation method.
double quantile_linear(std::vector<double> v, double q) {
    std::sort(v.begin(), v.end());
    double h = q * static_cast<double>(v.size() - 1);
    size_t lo = static_cast<size_t>(std::floor(h));
    size_t hi = static_cast<size_t>(std::ceil(h));
    if (lo == hi) return v[lo];
    double frac = h - static_cast<double>(lo);
    return v[lo] + frac * (v[hi] - v[lo]);
}

}  // namespace

std::array<double, 11> cohort_features(const std::vector<double>& x,
                                        const std::vector<double>& t_x,
                                        const std::vector<double>& T_cal) {
    if (x.empty()) {
        throw std::invalid_argument("cohort_features: x must not be empty (degenerate cohort)");
    }
    if (t_x.size() != x.size()) {
        throw std::invalid_argument("cohort_features: t_x.size() must equal x.size()");
    }
    if (T_cal.size() != x.size()) {
        throw std::invalid_argument("cohort_features: T_cal.size() must equal x.size()");
    }

    const size_t n = x.size();
    const double mean_x = mean_of(x);

    double sq_diff_sum = 0.0;
    for (double xi : x) sq_diff_sum += (xi - mean_x) * (xi - mean_x);
    const double sd_x = std::sqrt(sq_diff_sum / static_cast<double>(n));

    size_t n_zero = 0, n_one = 0;
    std::vector<double> tx_active, ratio_recency_active, ratio_since_active;
    for (size_t i = 0; i < n; ++i) {
        if (x[i] == 0.0) ++n_zero;
        if (x[i] == 1.0) ++n_one;
        if (x[i] > 0.0) {
            double Ta = std::max(T_cal[i], 1e-9);
            tx_active.push_back(t_x[i]);
            ratio_recency_active.push_back(t_x[i] / Ta);
            ratio_since_active.push_back((T_cal[i] - t_x[i]) / Ta);
        }
    }

    const double frac_active = static_cast<double>(tx_active.size()) / static_cast<double>(n);

    return {
        std::log(static_cast<double>(n)),
        mean_x,
        sd_x,
        static_cast<double>(n_zero) / static_cast<double>(n),
        static_cast<double>(n_one) / static_cast<double>(n),
        quantile_linear(x, 0.9),
        mean_of(tx_active),
        mean_of(T_cal),
        mean_of(ratio_recency_active),
        mean_of(ratio_since_active),
        frac_active,
    };
}

}  // namespace pareto_nbd
