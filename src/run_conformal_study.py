"""
Phase 2, Step 5 (full): multi-seed before/after study of conformal recalibration of BTYD.

For each dataset and many held-out splits, score the Pareto/NBD predictive raw vs. after
distributional (conformal-style) recalibration, and run a paired Wilcoxon of recal vs. raw across
seeds. Confirms that recalibration restores calibration where BTYD breaks (Online Retail II,
Dunnhumby) without harming the already-calibrated datasets.

Saves results/conformal_study_summary.csv and prints the headline table.

Run:  python src/run_conformal_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conformal import compare_conformal                          # noqa: E402
from run_ml_study import build_providers, ORDER                  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 15
MCMC_DRAWS = 1500
METRICS = ["CRPS", "pit_ks", "cov95", "cov50", "nMAE"]


def main():
    print("Loading datasets...", flush=True)
    providers = build_providers()
    rows = []
    for name, get in providers.items():
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            res = compare_conformal(df, h, seed=2000 + seed, mcmc_draws=MCMC_DRAWS)
            for key, s in res.items():
                if isinstance(key, tuple):
                    method, cond = key
                    for metric in METRICS:
                        rows.append(dict(dataset=name, seed=seed, method=method,
                                         cond=cond, metric=metric, value=s[metric]))
            pd.DataFrame(rows).to_csv(RES / "conformal_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, cond, metric), g in raw.groupby(["dataset", "cond", "metric"]):
        w = g.pivot_table(index="seed", columns="method", values="value")
        if "BTYD_raw" not in w or "BTYD_recal" not in w:
            continue
        r, c = w["BTYD_raw"].to_numpy(), w["BTYD_recal"].to_numpy()
        diff = c - r
        p = 1.0 if np.allclose(diff, 0) else stats.wilcoxon(r, c).pvalue
        summary.append(dict(dataset=dataset, cond=cond, metric=metric,
                            raw_mean=r.mean(), recal_mean=c.mean(),
                            recal_minus_raw=diff.mean(), wilcoxon_p=p, n_seeds=len(w)))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "conformal_study_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Conformalized BTYD: raw -> recalibrated (mean over seeds, all customers) ===")
    print(f"{'dataset':15s}{'PIT-KS raw':>12s}{'PIT-KS recal':>14s}{'sig':>4s} | "
          f"{'CRPS raw':>10s}{'CRPS recal':>12s}{'sig':>4s}")
    for ds in ORDER:
        s = sm[(sm.dataset == ds) & (sm["cond"] == "all")]
        if s.empty:
            continue
        k = s[s.metric == "pit_ks"].iloc[0]; c = s[s.metric == "CRPS"].iloc[0]
        print(f"{ds:15s}{k.raw_mean:>12.3f}{k.recal_mean:>14.3f}{star(k.wilcoxon_p):>4s} | "
              f"{c.raw_mean:>10.3f}{c.recal_mean:>12.3f}{star(c.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'conformal_study_summary.csv'}")


if __name__ == "__main__":
    main()
