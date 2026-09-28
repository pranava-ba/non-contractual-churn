#pragma once
#include <utility>

namespace pareto_nbd {

// Converts a target (mean, coefficient of variation) to a Gamma(shape, rate)
// parameterization: shape = 1/CV^2, rate = shape/mean. Mirrors
// simulate.moments_to_gamma in the Python implementation exactly.
std::pair<double, double> moments_to_gamma(double mean, double cv);

}  // namespace pareto_nbd
