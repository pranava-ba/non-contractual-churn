#include "pareto_nbd/conformal.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace pareto_nbd {

std::vector<double> randomized_pit(const std::vector<std::vector<double>>& pred,
                                    const std::vector<double>& y,
                                    const std::vector<double>& tie_break) {
    if (pred.empty()) {
        throw std::invalid_argument("randomized_pit: pred must not be empty");
    }
    if (y.size() != tie_break.size()) {
        throw std::invalid_argument("randomized_pit: tie_break.size() must equal y.size()");
    }
    for (size_t j = 0; j < pred.size(); ++j) {
        if (pred[j].size() != y.size()) {
            throw std::invalid_argument("randomized_pit: pred[j].size() must equal y.size()");
        }
    }

    const size_t J = pred.size();
    const size_t N = y.size();
    std::vector<double> out(N);
    for (size_t i = 0; i < N; ++i) {
        size_t below_count = 0, at_count = 0;
        for (size_t j = 0; j < J; ++j) {
            if (pred[j][i] < y[i]) ++below_count;
            if (pred[j][i] == y[i]) ++at_count;
        }
        double below = static_cast<double>(below_count) / static_cast<double>(J);
        double at = static_cast<double>(at_count) / static_cast<double>(J);
        out[i] = below + tie_break[i] * at;
    }
    return out;
}

namespace {

// numpy.quantile's default ("linear") interpolation method, over an
// already-sorted vector. Same formula as cohort_features.cpp's
// quantile_linear, duplicated here since these two files have no shared
// dependency and each is small enough to keep self-contained.
double quantile_linear_sorted(const std::vector<double>& sorted, double q) {
    double h = q * static_cast<double>(sorted.size() - 1);
    size_t lo = static_cast<size_t>(std::floor(h));
    size_t hi = static_cast<size_t>(std::ceil(h));
    if (lo == hi) return sorted[lo];
    double frac = h - static_cast<double>(lo);
    return sorted[lo] + frac * (sorted[hi] - sorted[lo]);
}

}  // namespace

std::vector<std::vector<double>> apply_conformal_warp(
    const std::vector<double>& u, const std::vector<double>& p,
    const std::vector<std::vector<double>>& pred_test) {
    if (u.empty()) {
        throw std::invalid_argument("apply_conformal_warp: u must not be empty");
    }
    if (pred_test.empty()) {
        throw std::invalid_argument("apply_conformal_warp: pred_test must not be empty");
    }
    for (double pk : p) {
        if (pk < 0.0 || pk > 1.0) {
            throw std::invalid_argument("apply_conformal_warp: p values must be in [0.0, 1.0]");
        }
    }

    const size_t J = pred_test.size();
    const size_t N_test = pred_test[0].size();

    // Sort each column (across the J draws) independently.
    std::vector<std::vector<double>> ps(J, std::vector<double>(N_test));
    for (size_t i = 0; i < N_test; ++i) {
        std::vector<double> col(J);
        for (size_t j = 0; j < J; ++j) col[j] = pred_test[j][i];
        std::sort(col.begin(), col.end());
        for (size_t j = 0; j < J; ++j) ps[j][i] = col[j];
    }

    std::vector<double> u_sorted = u;
    std::sort(u_sorted.begin(), u_sorted.end());

    const size_t n_out = p.size();
    std::vector<std::vector<double>> out(n_out);
    for (size_t k = 0; k < n_out; ++k) {
        double w = quantile_linear_sorted(u_sorted, p[k]);
        long idx = std::lrint(w * static_cast<double>(J - 1));
        idx = std::max<long>(0, std::min<long>(idx, static_cast<long>(J) - 1));
        out[k] = ps[static_cast<size_t>(idx)];
    }
    return out;
}

}  // namespace pareto_nbd
