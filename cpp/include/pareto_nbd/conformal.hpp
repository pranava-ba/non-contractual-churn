#pragma once
#include <vector>

namespace pareto_nbd {

// Randomized PIT for count forecasts (Czado, Gneiting & Held 2009),
// mirroring score.randomized_pit exactly except that the tie-breaking
// uniform draws are passed in as `tie_break` (one per customer) instead
// of generated from an RNG internally — this makes the function pure and
// exactly golden-file testable; a caller generates `tie_break` itself
// (e.g. via std::uniform_real_distribution) before calling this.
// pred: (J x N) predictive draws. y: (N,) truths. tie_break: (N,) in [0,1).
std::vector<double> randomized_pit(const std::vector<std::vector<double>>& pred,
                                    const std::vector<double>& y,
                                    const std::vector<double>& tie_break);

}  // namespace pareto_nbd
