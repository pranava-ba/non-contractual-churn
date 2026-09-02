"""
Extend the next-purchase-timing repair (Table 12) to the dense cohorts.

The headline timing claim---Pareto/GGG overturns the "too inaccurate to use" verdict---is validated
in the main text on one real dataset (Grocery). Those are precisely the dense, regularly-buying
cohorts the mechanism predicts should show the largest Pareto/GGG advantage, so we test them
directly: Dunnhumby, Online Retail~II, and Ta-Feng. Large cohorts are subsampled to keep the GGG
Gibbs sampler tractable; the timing forecast is a per-customer quantity, so a random subsample is a
fair evaluation. Same estimators, sampler, and scorer as `run_timing_study.py`.

Saves results/timing_dense_summary.csv; prints the table.  Run: python src/run_timing_dense.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from datasets import load_summary                                    # noqa: E402
from estimate import fit_mcmc                                        # noqa: E402
from estimate_ggg import fit_ggg                                     # noqa: E402
from timing import (sample_next_purchase_time_pnbd,                  # noqa: E402
                    sample_next_purchase_time_pggg, score_timing_forecast)

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 6
MAX_N = 2500          # subsample cap for the GGG sampler
DATASETS = ["Dunnhumby", "OnlineRetailII", "Ta-Feng"]


def run_one(df, horizon, seed):
    """Subsample, fit Pareto/NBD + Pareto/GGG, score next-purchase timing (MdAE, CRPS)."""
    rng = np.random.default_rng(seed)
    if len(df) > MAX_N:
        df = df.iloc[np.sort(rng.choice(len(df), MAX_N, replace=False))].reset_index(drop=True)
    true_wait = df[f"t_next_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    tx = df["t_x"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=1200, burn_in=400, thin=4, seed=seed + 1)
    gg = fit_ggg(df, n_draws=1000, burn_in=350, thin=4, seed=seed + 2)
    w_p = sample_next_purchase_time_pnbd(mc.lam, mc.mu, mc.tau, Tcal, seed=seed + 3)
    w_g = sample_next_purchase_time_pggg(gg.lam, gg.mu, gg.tau, gg.k_draws.mean(), Tcal, tx, seed=seed + 4)
    return (score_timing_forecast(w_p, true_wait), score_timing_forecast(w_g, true_wait),
            float(gg.k_draws.mean()))


def main():
    rows = []
    for name in DATASETS:
        df, h = load_summary(name)
        t = time.time()
        for seed in range(SEEDS):
            sp, sg, khat = run_one(df, h, seed=13000 + seed)
            for metric in ("timing_MdAE", "timing_CRPS"):
                rows.append(dict(dataset=name, seed=seed, k_hat=khat, metric=metric,
                                 PNBD=sp[metric], GGG=sg[metric]))
            pd.DataFrame(rows).to_csv(RES / "timing_dense_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summ = []
    for (dataset, metric), g in raw.groupby(["dataset", "metric"]):
        p, gv = g["PNBD"].to_numpy(), g["GGG"].to_numpy()
        pval = 1.0 if np.allclose(p - gv, 0) else stats.wilcoxon(p, gv).pvalue
        summ.append(dict(dataset=dataset, metric=metric, k_hat=g["k_hat"].mean(),
                         PNBD=p.mean(), GGG=gv.mean(), wilcoxon_p=pval))
    sm = pd.DataFrame(summ)
    sm.to_csv(RES / "timing_dense_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Next-purchase timing on the dense cohorts: Pareto/NBD vs Pareto/GGG ===")
    print(f"{'dataset':16s}{'k_hat':>7s}{'MdAE PNBD':>11s}{'GGG':>8s}{'sig':>4s} | "
          f"{'CRPS PNBD':>11s}{'GGG':>9s}{'sig':>4s}")
    for ds in DATASETS:
        m = sm[(sm.dataset == ds) & (sm.metric == "timing_MdAE")]
        c = sm[(sm.dataset == ds) & (sm.metric == "timing_CRPS")]
        if m.empty:
            continue
        m, c = m.iloc[0], c.iloc[0]
        print(f"{ds:16s}{m.k_hat:>7.2f}{m.PNBD:>11.2f}{m.GGG:>8.2f}{star(m.wilcoxon_p):>4s} | "
              f"{c.PNBD:>11.2f}{c.GGG:>9.2f}{star(c.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'timing_dense_summary.csv'}")


if __name__ == "__main__":
    main()
