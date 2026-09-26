#pragma once
#include <functional>
#include <vector>

namespace pareto_nbd {

struct NelderMeadResult {
    std::vector<double> x;
    double fval;
    int iterations;
};

// Minimizes `objective` starting from `x0` using the Nelder-Mead simplex
// method (Nelder & Mead 1965): standard reflection/expansion/contraction/
// shrink coefficients (1, 2, 0.5, 0.5), and the same initial-simplex
// construction and default tolerances as
// scipy.optimize.minimize(method="Nelder-Mead") — a 5% step per dimension
// (or 0.00025 if that coordinate is exactly 0), xatol=1e-4, fatol=1e-4,
// maxiter=200*n. Not expected to walk an identical convergence path to
// SciPy's implementation, only to converge near the same optimum.
NelderMeadResult nelder_mead(
    const std::function<double(const std::vector<double>&)>& objective,
    const std::vector<double>& x0);

}  // namespace pareto_nbd
