#pragma once
#include <array>
#include <vector>

namespace pareto_nbd {

// Forecast-time summary statistics of a cohort. Mirrors
// amortized.cohort_features in the Python implementation exactly, including
// numpy's default (linear-interpolation) quantile method and population
// (ddof=0) standard deviation.
std::array<double, 11> cohort_features(const std::vector<double>& x,
                                        const std::vector<double>& t_x,
                                        const std::vector<double>& T_cal);

}  // namespace pareto_nbd
