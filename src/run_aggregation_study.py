"""
Gap F2: individual-vs-cohort accuracy decomposition.

Simon notes in passing that MLE forecasts are cohort-based while MCMC/heuristic forecasts can be
individual-based, but never measures the accuracy gap as a function of aggregation-group size. We
do: randomly partition customers into groups of size k, sum the predicted and realised x* within
each group, and compute the normalised error of the group totals. Sweeping k from 1 (individual) to
the whole cohort shows where individual-level stochasticity averages out and -- the practical
question -- the group size beyond which the choice of method stops mattering.

Runs on a simulated cohort and CDNow. Saves results/aggregation_summary.csv; prints the table.

Run:  python src/run_aggregation_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import fit_mcmc, fit_mle                              # noqa: E402
from score import spp_predict, conditional_individual_draws        # noqa: E402
from run_study import heuristic_point                              # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
GROUP_SIZES = [1, 2, 5, 10, 25, 100]
SEEDS = 8            # random regroupings per (dataset, k)
HORIZON = 26


def grouped_nmae(pred_mean, y, k, rng):
    """Normalised MAE of group totals for random groups of size k."""
    n = len(y)
    perm = rng.permutation(n)
    n_groups = n // k
    if n_groups < 2:
        return np.nan
    idx = perm[:n_groups * k].reshape(n_groups, k)
    pred_sum = pred_mean[idx].sum(axis=1)
    true_sum = y[idx].sum(axis=1)
    return float(np.abs(pred_sum - true_sum).mean() / max(true_sum.mean(), 1e-9))


def method_means(df, horizon, seed, mcmc_draws=1500):
    Tcal = df["T_cal"].to_numpy(float)
    mle = fit_mle(df, seed=seed)
    lam, mu, tau = conditional_individual_draws(df, mle["r"], mle["alpha"], mle["s"], mle["beta"],
                                                n_draws=400, seed=seed + 1)
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 2)
    return {
        "MCMC": spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 3)).mean(0),
        "MLE": spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 4)).mean(0),
        "heuristic": heuristic_point(df, horizon),
    }


def run_dataset(name, df, horizon):
    y = df[f"x_star_{horizon}"].to_numpy(float)
    means = method_means(df, horizon, seed=1)
    rows = []
    for m, pm in means.items():
        for k in GROUP_SIZES + [len(df)]:
            rng = np.random.default_rng(100 + k)
            vals = [grouped_nmae(pm, y, k, rng) for _ in range(SEEDS)]
            rows.append(dict(dataset=name, method=m, k=k, group_nMAE=float(np.nanmean(vals))))
    return rows


def main():
    from simulate import DatasetParams, simulate_dataset
    from empirical import load_cdnow, elog_to_summary
    t = time.time()
    cases = [("Simulated", simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=3000, T=52.0),
                                            rng=np.random.default_rng(1)), HORIZON),
             ("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26)]
    rows = []
    for name, df, h in cases:
        rows += run_dataset(name, df, h)
    raw = pd.DataFrame(rows)
    raw.to_csv(RES / "aggregation_summary.csv", index=False)

    methods = ["MCMC", "MLE", "heuristic"]
    print(f"=== F2 group-total nMAE vs aggregation size k (mean over regroupings) [{time.time()-t:.0f}s] ===")
    for name, _, _ in cases:
        g = raw[raw.dataset == name]
        ks = sorted(g.k.unique())
        print(f"\n {name}:")
        print(f"  {'k':>6s}" + "".join(f"{m:>12s}" for m in methods))
        for k in ks:
            cells = ""
            for m in methods:
                v = g[(g.method == m) & (g.k == k)]["group_nMAE"]
                cells += f"{v.iloc[0]:>12.3f}" if not v.empty else f"{'-':>12s}"
            label = f"{k}" if k in GROUP_SIZES else f"{k}(all)"
            print(f"  {label:>6s}{cells}")
        # method spread at k=1 vs the largest group
        for kk in [1, ks[-1]]:
            sub = g[g.k == kk].set_index("method")["group_nMAE"]
            print(f"    method spread at k={kk}: {sub.max()-sub.min():.3f}")
    print(f"\n[saved] {RES/'aggregation_summary.csv'}")


if __name__ == "__main__":
    main()
