"""
Gap M3 (full): multi-seed conformal recalibration of the ML forecasters.

Simon (2025) and the cited ML literature give ML *point* forecasts (or a single parametric
predictive), which structurally disadvantages ML in any interval-coverage comparison. This study
wraps every forecaster -- BTYD and each ML method -- in the same distribution-free recalibration
used for Conformalized BTYD, and asks, per dataset and across many splits: does conformal
recalibration repair the ML predictive's coverage (paired Wilcoxon recal vs raw)? The distribution-
free QuantileGBM should already be near-calibrated (warp ~ identity, no harm); the parametric
PoissonGBM should gain where its Poisson assumption is too rigid.

Saves results/conformal_ml_study_summary.csv (+ _raw.csv) and prints the headline table.

Run:  python src/run_conformal_ml_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conformal import compare_conformal_ml                        # noqa: E402
from run_ml_study import build_providers                          # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 8
MCMC_DRAWS = 1200
ML_METHODS = ("PoissonGBM", "QuantileGBM")
BASE_METHODS = ["BTYD", *ML_METHODS]
METRICS = ["CRPS", "pit_ks", "cov95", "cov50", "nMAE", "sharpness_std"]
# representative subset: BTYD-home (Simulated), a calibrated real (CDNow), and the two
# datasets where BTYD's Poisson assumption breaks (Online Retail II, Dunnhumby).
DATASETS = ["Simulated", "CDNow", "OnlineRetailII", "Dunnhumby"]


def main():
    print("Loading datasets...", flush=True)
    providers = build_providers()
    rows = []
    for name in DATASETS:
        get = providers[name]
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            res = compare_conformal_ml(df, h, ml_methods=ML_METHODS,
                                       seed=3000 + seed, mcmc_draws=MCMC_DRAWS)
            for key, s in res.items():
                if isinstance(key, tuple):
                    tag, cond = key                       # tag = "<method>_<raw|recal>"
                    for metric in METRICS:
                        rows.append(dict(dataset=name, seed=seed, tag=tag, cond=cond,
                                         metric=metric, value=s[metric]))
            pd.DataFrame(rows).to_csv(RES / "conformal_ml_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    # ---- aggregate + paired Wilcoxon (recal vs raw, per base method, across seeds) ---- #
    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, cond, metric), g in raw.groupby(["dataset", "cond", "metric"]):
        w = g.pivot_table(index="seed", columns="tag", values="value")
        for method in BASE_METHODS:
            rk, ck = f"{method}_raw", f"{method}_recal"
            if rk not in w or ck not in w:
                continue
            r, c = w[rk].to_numpy(), w[ck].to_numpy()
            diff = c - r
            p = 1.0 if np.allclose(diff, 0) else stats.wilcoxon(r, c).pvalue
            summary.append(dict(dataset=dataset, cond=cond, metric=metric, method=method,
                                raw_mean=r.mean(), recal_mean=c.mean(),
                                recal_minus_raw=diff.mean(), wilcoxon_p=p, n_seeds=len(w)))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "conformal_ml_study_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Conformal recalibration of ML forecasters: raw -> recal "
          "(mean over seeds, all customers) ===")
    print(f"{'dataset':15s}{'method':12s}{'PIT-KS raw':>11s}{'PIT-KS recal':>13s}{'sig':>4s}"
          f"{'cov95 raw':>10s}{'cov95 recal':>12s}")
    for ds in DATASETS:
        for m in BASE_METHODS:
            k = sm[(sm.dataset == ds) & (sm["cond"] == "all") & (sm.metric == "pit_ks")
                   & (sm.method == m)]
            cv = sm[(sm.dataset == ds) & (sm["cond"] == "all") & (sm.metric == "cov95")
                    & (sm.method == m)]
            if k.empty:
                continue
            k = k.iloc[0]; cv = cv.iloc[0]
            print(f"{ds:15s}{m:12s}{k.raw_mean:>11.3f}{k.recal_mean:>13.3f}"
                  f"{star(k.wilcoxon_p):>4s}{cv.raw_mean:>10.3f}{cv.recal_mean:>12.3f}")
    print(f"\n[saved] {RES/'conformal_ml_study_summary.csv'}")


if __name__ == "__main__":
    main()
