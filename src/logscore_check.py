"""
Logarithmic-score robustness check: confirm that the second proper score (log score)
gives the same MCMC-vs-MLE verdict as the CRPS, on representative datasets. The log
score penalises overconfident tails more sharply than the CRPS, so agreement guards
against a conclusion that depends on the choice of score.

The heuristic is a degenerate point predictive, so it assigns zero probability to any
outcome away from its point and its log score is +inf on the first miss -- itself a stark
illustration that the heuristic carries no usable distribution; we therefore report the
log score only for the two model-based estimators.

Run:  python src/logscore_check.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset
from estimate import fit_mcmc, fit_mle
from score import spp_predict, conditional_individual_draws, crps_samples
from empirical import load_cdnow, load_grocery, elog_to_summary


def log_score(pred, y):
    """Mean negative log predictive mass, sample-estimated with a 1/(2J) floor."""
    J = pred.shape[0]
    floor = 1.0 / (2.0 * J)
    ls = np.empty(y.shape[0])
    for i in range(y.shape[0]):
        p = np.mean(pred[:, i] == y[i])
        ls[i] = -np.log(max(p, floor))
    return ls


def scores(df, horizon, seed):
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=3000, burn_in=1000, thin=5, seed=seed + 1)
    mle = fit_mle(df, seed=seed + 2)
    lam, mu, tau = conditional_individual_draws(
        df, mle["r"], mle["alpha"], mle["s"], mle["beta"], n_draws=400, seed=seed + 3)
    pred = {"MCMC": spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 4)),
            "MLE": spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 5))}
    out = {}
    for m, p in pred.items():
        for cond, mask in [("all", np.ones(len(y), bool)), ("x>0", xcal > 0)]:
            out[(m, cond, "CRPS")] = crps_samples(p[:, mask], y[mask]).mean()
            out[(m, cond, "LogS")] = log_score(p[:, mask], y[mask]).mean()
    return out


def main():
    cases = [("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26, 10),
             ("Grocery", elog_to_summary(load_grocery(), 52, 26), 26, 20),
             ("Sim A (N=800)", simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=800, T=52.0),
                                                rng=np.random.default_rng(1)), 26, 30),
             ("Sim B (N=1200)", simulate_dataset(DatasetParams(0.08, 2.0, 0.10, 1.5, N=1200, T=39.0),
                                                 rng=np.random.default_rng(2)), 26, 40)]
    print(f"{'dataset':16s}{'cond':6s}{'CRPS MCMC':>11s}{'CRPS MLE':>10s}"
          f"{'LogS MCMC':>11s}{'LogS MLE':>10s}")
    for name, df, h, seed in cases:
        s = scores(df, h, seed)
        for cond in ["all", "x>0"]:
            print(f"{name:16s}{cond:6s}{s[('MCMC',cond,'CRPS')]:>11.3f}{s[('MLE',cond,'CRPS')]:>10.3f}"
                  f"{s[('MCMC',cond,'LogS')]:>11.3f}{s[('MLE',cond,'LogS')]:>10.3f}")


if __name__ == "__main__":
    main()
