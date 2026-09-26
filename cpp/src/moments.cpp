#include "pareto_nbd/moments.hpp"

namespace pareto_nbd {

std::pair<double, double> moments_to_gamma(double mean, double cv) {
    double shape = 1.0 / (cv * cv);
    double rate = shape / mean;
    return {shape, rate};
}

}  // namespace pareto_nbd
