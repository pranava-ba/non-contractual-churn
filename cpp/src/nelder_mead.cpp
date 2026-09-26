#include "pareto_nbd/nelder_mead.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>

namespace pareto_nbd {
namespace {

constexpr double kAlpha = 1.0;  // reflection
constexpr double kGamma = 2.0;  // expansion
constexpr double kRho = 0.5;    // contraction
constexpr double kSigma = 0.5;  // shrink

std::vector<double> add_scaled(const std::vector<double>& a, const std::vector<double>& b,
                                double scale) {
    std::vector<double> out(a.size());
    for (size_t i = 0; i < a.size(); ++i) out[i] = a[i] + scale * b[i];
    return out;
}

std::vector<double> subtract(const std::vector<double>& a, const std::vector<double>& b) {
    std::vector<double> out(a.size());
    for (size_t i = 0; i < a.size(); ++i) out[i] = a[i] - b[i];
    return out;
}

}  // namespace

NelderMeadResult nelder_mead(
    const std::function<double(const std::vector<double>&)>& objective,
    const std::vector<double>& x0) {
    const size_t n = x0.size();
    const double xatol = 1e-4;
    const double fatol = 1e-4;
    const int maxiter = 200 * static_cast<int>(n);

    std::vector<std::vector<double>> simplex(n + 1, x0);
    for (size_t i = 0; i < n; ++i) {
        double step = (x0[i] != 0.0) ? 0.05 * x0[i] : 0.00025;
        simplex[i + 1][i] += step;
    }

    std::vector<double> fvals(n + 1);
    for (size_t i = 0; i <= n; ++i) fvals[i] = objective(simplex[i]);

    auto sort_simplex = [&]() {
        std::vector<size_t> order(n + 1);
        std::iota(order.begin(), order.end(), 0);
        std::sort(order.begin(), order.end(), [&](size_t a, size_t b) { return fvals[a] < fvals[b]; });
        std::vector<std::vector<double>> new_simplex(n + 1);
        std::vector<double> new_fvals(n + 1);
        for (size_t i = 0; i <= n; ++i) {
            new_simplex[i] = simplex[order[i]];
            new_fvals[i] = fvals[order[i]];
        }
        simplex = new_simplex;
        fvals = new_fvals;
    };

    sort_simplex();

    int iter = 0;
    while (iter < maxiter) {
        double x_spread = 0.0;
        for (size_t i = 1; i <= n; ++i) {
            double d = 0.0;
            for (size_t j = 0; j < n; ++j) d = std::max(d, std::abs(simplex[i][j] - simplex[0][j]));
            x_spread = std::max(x_spread, d);
        }
        double f_spread = 0.0;
        for (size_t i = 1; i <= n; ++i) f_spread = std::max(f_spread, std::abs(fvals[i] - fvals[0]));
        if (x_spread <= xatol && f_spread <= fatol) break;

        std::vector<double> centroid(n, 0.0);
        for (size_t i = 0; i < n; ++i)
            for (size_t j = 0; j < n; ++j) centroid[j] += simplex[i][j];
        for (size_t j = 0; j < n; ++j) centroid[j] /= static_cast<double>(n);

        std::vector<double> xr = add_scaled(centroid, subtract(centroid, simplex[n]), kAlpha);
        double fr = objective(xr);

        if (fr < fvals[0]) {
            std::vector<double> xe = add_scaled(centroid, subtract(xr, centroid), kGamma);
            double fe = objective(xe);
            if (fe < fr) {
                simplex[n] = xe;
                fvals[n] = fe;
            } else {
                simplex[n] = xr;
                fvals[n] = fr;
            }
        } else if (fr < fvals[n - 1]) {
            simplex[n] = xr;
            fvals[n] = fr;
        } else {
            bool shrink = false;
            if (fr < fvals[n]) {
                std::vector<double> xc = add_scaled(centroid, subtract(xr, centroid), kRho);
                double fc = objective(xc);
                if (fc <= fr) {
                    simplex[n] = xc;
                    fvals[n] = fc;
                } else {
                    shrink = true;
                }
            } else {
                std::vector<double> xc = add_scaled(centroid, subtract(simplex[n], centroid), kRho);
                double fc = objective(xc);
                if (fc < fvals[n]) {
                    simplex[n] = xc;
                    fvals[n] = fc;
                } else {
                    shrink = true;
                }
            }
            if (shrink) {
                for (size_t i = 1; i <= n; ++i) {
                    simplex[i] = add_scaled(simplex[0], subtract(simplex[i], simplex[0]), kSigma);
                    fvals[i] = objective(simplex[i]);
                }
            }
        }

        sort_simplex();
        ++iter;
    }

    return {simplex[0], fvals[0], iter};
}

}  // namespace pareto_nbd
