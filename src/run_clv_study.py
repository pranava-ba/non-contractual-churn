"""
Phase 2, Step 7 (full): multi-seed probabilistic-CLV study, structural vs. deep.

For each dataset with spend (Online Retail II, Ta-Feng, Dunnhumby) and many held-out splits, score
Pareto/NBD + Gamma-Gamma vs. the deep ZILN on the monetary CLV target (CRPS / PIT / coverage), and
run a paired Wilcoxon of ZILN vs. BTYD+GG across seeds.

Saves results/clv_study_summary.csv and prints the headline table.

Run:  python src/run_clv_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clv_data import load_clv_summary, MONEY_REGISTRY          # noqa: E402
from clv_benchmark import compare_clv                          # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 15
MCMC_DRAWS = 1500
METRICS = ["CRPS", "pit_ks", "cov95", "nMAE"]


def main():
    print("Loading CLV datasets...", flush=True)
    data = {name: load_clv_summary(name) for name in MONEY_REGISTRY}
    rows = []
    for name, (df, h) in data.items():
        t = time.time()
        for seed in range(SEEDS):
            res = compare_clv(df, h, seed=3000 + seed, mcmc_draws=MCMC_DRAWS)
            for key, s in res.items():
                if isinstance(key, tuple):
                    method, cond = key
                    for metric in METRICS:
                        rows.append(dict(dataset=name, seed=seed, method=method,
                                         cond=cond, metric=metric, value=s[metric]))
            pd.DataFrame(rows).to_csv(RES / "clv_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, cond, metric), g in raw.groupby(["dataset", "cond", "metric"]):
        w = g.pivot_table(index="seed", columns="method", values="value")
        if "BTYD+GG" not in w or "ZILN" not in w:
            continue
        b, z = w["BTYD+GG"].to_numpy(), w["ZILN"].to_numpy()
        p = 1.0 if np.allclose(z - b, 0) else stats.wilcoxon(b, z).pvalue
        summary.append(dict(dataset=dataset, cond=cond, metric=metric,
                            BTYD_GG_mean=b.mean(), BTYD_GG_sd=b.std(ddof=1),
                            ZILN_mean=z.mean(), ZILN_sd=z.std(ddof=1), wilcoxon_p=p, n_seeds=len(w)))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "clv_study_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Probabilistic CLV: BTYD+GG vs deep ZILN (mean±sd over seeds, all customers) ===")
    print(f"{'dataset':15s}{'PIT-KS BTYD+GG':>16s}{'PIT-KS ZILN':>13s}{'sig':>4s} | "
          f"{'CRPS BTYD+GG':>14s}{'CRPS ZILN':>12s}{'sig':>4s}")
    for ds in MONEY_REGISTRY:
        s = sm[(sm.dataset == ds) & (sm["cond"] == "all")]
        if s.empty:
            continue
        k = s[s.metric == "pit_ks"].iloc[0]; c = s[s.metric == "CRPS"].iloc[0]
        print(f"{ds:15s}{k.BTYD_GG_mean:>10.3f}±{k.BTYD_GG_sd:<4.2f}{k.ZILN_mean:>9.3f}±{k.ZILN_sd:<4.2f}"
              f"{star(k.wilcoxon_p):>4s} | {c.BTYD_GG_mean:>9.1f}±{c.BTYD_GG_sd:<4.1f}"
              f"{c.ZILN_mean:>8.1f}±{c.ZILN_sd:<4.1f}{star(c.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'clv_study_summary.csv'}")


if __name__ == "__main__":
    main()
