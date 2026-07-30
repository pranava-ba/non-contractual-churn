"""
Phase 2, Step 8: next-purchase-timing study (Extension B) -- Pareto/NBD vs Pareto/GGG.

Simon (2025) reports next-purchase timing as too inaccurate to use; the reason is Pareto/NBD's
memoryless (exponential) inter-purchase assumption. The Pareto/GGG models timing regularity, so it
should forecast the wait to the next purchase better when purchasing is regular. For each dataset
and many seeds we fit both, forecast the wait-time distribution (timing.py), and score it (CRPS,
median absolute error) on the customers who actually buy next.

Datasets: simulated with regularity k in {1, 2, 3} (k=1 is Pareto/NBD), plus CDNow and Grocery
(now carrying the litt statistic and the true next-purchase wait t_next).

Saves results/timing_study_summary.csv and prints the headline table.
Run:  python src/run_timing_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams                                   # noqa: E402
from simulate_misspec import simulate_dataset_ggg                    # noqa: E402
from empirical import load_cdnow, load_grocery, elog_to_summary      # noqa: E402
from estimate import fit_mcmc                                        # noqa: E402
from estimate_ggg import fit_ggg                                     # noqa: E402
from timing import (sample_next_purchase_time_pnbd,                  # noqa: E402
                    sample_next_purchase_time_pggg, score_timing_forecast)

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 12
HORIZON = 26
METRICS = ["timing_CRPS", "timing_MdAE"]


def build_providers():
    provs = {}
    for k in (1.0, 2.0, 3.0):
        provs[f"Sim-k{k:g}"] = (lambda seed, kk=k: simulate_dataset_ggg(
            DatasetParams(0.15, 1.2, 0.08, 1.0, N=800, T=52.0), k=kk,
            rng=np.random.default_rng(seed)))
    cdnow = elog_to_summary(load_cdnow(), 39, HORIZON)
    grocery = elog_to_summary(load_grocery(), 52, HORIZON)
    provs["CDNow"] = lambda seed, d=cdnow: d
    provs["Grocery"] = lambda seed, d=grocery: d
    return provs


def main():
    print("Loading...", flush=True)
    providers = build_providers()
    rows = []
    for name, get in providers.items():
        t = time.time()
        for seed in range(SEEDS):
            df = get(seed)
            true_wait = df[f"t_next_{HORIZON}"].to_numpy(float)
            Tcal = df["T_cal"].to_numpy(float)
            tx = df["t_x"].to_numpy(float)
            mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=seed + 1)
            gg = fit_ggg(df, n_draws=1200, burn_in=400, thin=4, seed=seed + 2)
            w_p = sample_next_purchase_time_pnbd(mc.lam, mc.mu, mc.tau, Tcal, seed=seed + 3)
            w_g = sample_next_purchase_time_pggg(gg.lam, gg.mu, gg.tau, gg.k_draws.mean(),
                                                 Tcal, tx, seed=seed + 4)
            for model, sc in [("PNBD", score_timing_forecast(w_p, true_wait)),
                              ("GGG", score_timing_forecast(w_g, true_wait))]:
                for metric in METRICS:
                    rows.append(dict(dataset=name, seed=seed, model=model,
                                     metric=metric, value=sc[metric]))
            pd.DataFrame(rows).to_csv(RES / "timing_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, metric), g in raw.groupby(["dataset", "metric"]):
        w = g.pivot_table(index="seed", columns="model", values="value")
        if "PNBD" not in w or "GGG" not in w:
            continue
        p_, gv = w["PNBD"].to_numpy(), w["GGG"].to_numpy()
        pval = 1.0 if np.allclose(p_ - gv, 0) else stats.wilcoxon(p_, gv).pvalue
        summary.append(dict(dataset=dataset, metric=metric, PNBD=p_.mean(), GGG=gv.mean(),
                            wilcoxon_p=pval))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "timing_study_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Next-purchase timing: Pareto/NBD vs Pareto/GGG (mean over seeds) ===")
    print(f"{'dataset':12s}{'timing CRPS PNBD':>18s}{'GGG':>9s}{'sig':>4s} | "
          f"{'MdAE PNBD':>11s}{'GGG':>8s}{'sig':>4s}")
    for ds in providers:
        c = sm[(sm.dataset == ds) & (sm.metric == "timing_CRPS")]
        m = sm[(sm.dataset == ds) & (sm.metric == "timing_MdAE")]
        if c.empty:
            continue
        c, m = c.iloc[0], m.iloc[0]
        print(f"{ds:12s}{c.PNBD:>18.2f}{c.GGG:>9.2f}{star(c.wilcoxon_p):>4s} | "
              f"{m.PNBD:>11.2f}{m.GGG:>8.2f}{star(m.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'timing_study_summary.csv'}")


if __name__ == "__main__":
    main()
