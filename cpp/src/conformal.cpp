#include "pareto_nbd/conformal.hpp"

namespace pareto_nbd {

std::vector<double> randomized_pit(const std::vector<std::vector<double>>& pred,
                                    const std::vector<double>& y,
                                    const std::vector<double>& tie_break) {
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

}  // namespace pareto_nbd
