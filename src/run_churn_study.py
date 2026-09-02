"""
Phase 2, Step 9 (full): multi-seed churn / active-customer calibration study.

For each dataset and many held-out splits, score the calibration of the active-customer probability
(Brier + ECE) for structural Pareto/NBD vs. a trained ML classifier, and run a paired Wilcoxon
across seeds. Answers: is the model's "still active" probability trustworthy, and does an ML
classifier calibrate it better?

Saves results/churn_study_summary.csv and prints the headline table.
Run:  python src/run_churn_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ml_study import build_providers, ORDER                  # noqa: E402
from churn import compare_churn                                  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 15
MCMC_DRAWS = 1500
METRICS = ["brier", "ece"]


def main():
    print("Loading datasets...", flush=True)
    providers = build_providers()
    rows = []
    for name, get in providers.items():
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            res = compare_churn(df, h, seed=4000 + seed, mcmc_draws=MCMC_DRAWS)
            for method in ["BTYD", "ML"]:
                for metric in METRICS:
                    rows.append(dict(dataset=name, seed=seed, method=method,
                                     metric=metric, value=res[method][metric]))
            pd.DataFrame(rows).to_csv(RES / "churn_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, metric), g in raw.groupby(["dataset", "metric"]):
        w = g.pivot_table(index="seed", columns="method", values="value")
        if "BTYD" not in w or "ML" not in w:
            continue
        b, m = w["BTYD"].to_numpy(), w["ML"].to_numpy()
        p = 1.0 if np.allclose(b - m, 0) else stats.wilcoxon(b, m).pvalue
        summary.append(dict(dataset=dataset, metric=metric, BTYD=b.mean(), ML=m.mean(), wilcoxon_p=p))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "churn_study_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Churn / active-customer calibration: BTYD vs ML classifier (mean over seeds) ===")
    print(f"{'dataset':15s}{'Brier BTYD':>12s}{'Brier ML':>10s}{'sig':>4s} | "
          f"{'ECE BTYD':>10s}{'ECE ML':>9s}{'sig':>4s}")
    for ds in ORDER:
        br = sm[(sm.dataset == ds) & (sm.metric == "brier")]
        ec = sm[(sm.dataset == ds) & (sm.metric == "ece")]
        if br.empty:
            continue
        br, ec = br.iloc[0], ec.iloc[0]
        print(f"{ds:15s}{br.BTYD:>12.3f}{br.ML:>10.3f}{star(br.wilcoxon_p):>4s} | "
              f"{ec.BTYD:>10.3f}{ec.ML:>9.3f}{star(ec.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'churn_study_summary.csv'}")


if __name__ == "__main__":
    main()
