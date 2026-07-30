"""
Phase 2, Steps 4+2 (full): multi-seed Pareto/NBD-vs-ML calibration study across all datasets,
now with three ML comparators of increasing flexibility:
  - PoissonGBM   : gradient boosting with a Poisson predictive (Step 1)
  - HurdleGBM    : zero-inflated hurdle -- P(active) classifier x positive count (ZILN analog)
  - QuantileGBM  : distribution-free quantile regression (no parametric assumption)

For each dataset we repeat the fair comparison over many random train/test splits (reals: one
fixed cohort, resampled split + estimation noise; Simulated: a fresh cohort per seed as a control
where BTYD should win on its home turf), aggregate mean +/- sd, and run a paired Wilcoxon signed-
rank test of each ML method against BTYD across seeds.

Saves results/ml_study_raw.csv and results/ml_study_summary.csv, and prints the headline table.

Run:  python src/run_ml_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset               # noqa: E402
from empirical import load_cdnow, load_grocery, elog_to_summary    # noqa: E402
from datasets import load_summary, REGISTRY                        # noqa: E402
from ml_benchmark import compare_all                               # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 15
MCMC_DRAWS = 1500
METRICS = ["CRPS", "pit_ks", "cov95", "cov50", "nMAE"]
ML_METHODS = ["PoissonGBM", "HurdleGBM", "QuantileGBM"]
ALL_METHODS = ["BTYD"] + ML_METHODS
ORDER = ["Simulated", "CDNow", "Grocery", "OnlineRetailII", "Olist", "Dunnhumby", "Ta-Feng"]


def build_providers():
    """name -> get(seed) -> (cohort_df, horizon). Reals reuse one cohort; Simulated is fresh."""
    provs = {}
    provs["Simulated"] = lambda seed: (
        simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=1500, T=52.0),
                         rng=np.random.default_rng(seed)), 26)
    cdnow = elog_to_summary(load_cdnow(), 39, 26)
    grocery = elog_to_summary(load_grocery(), 52, 26)
    provs["CDNow"] = lambda seed, d=cdnow: (d, 26)
    provs["Grocery"] = lambda seed, d=grocery: (d, 26)
    for name in REGISTRY:
        df, h = load_summary(name)
        provs[name] = lambda seed, d=df, hh=h: (d, hh)
    return provs


def main():
    print("Loading datasets...", flush=True)
    providers = build_providers()
    rows = []
    for name, get in providers.items():
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            res = compare_all(df, h, seed=1000 + seed, mcmc_draws=MCMC_DRAWS)
            for key, s in res.items():
                if isinstance(key, tuple):
                    method, cond = key
                    for metric in METRICS:
                        rows.append(dict(dataset=name, N=len(df), seed=seed,
                                         method=method, cond=cond, metric=metric, value=s[metric]))
            pd.DataFrame(rows).to_csv(RES / "ml_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    # ---- aggregate + paired Wilcoxon (each ML method vs BTYD, across seeds) ----- #
    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, cond, metric), g in raw.groupby(["dataset", "cond", "metric"]):
        w = g.pivot_table(index="seed", columns="method", values="value")
        if "BTYD" not in w:
            continue
        btyd = w["BTYD"].to_numpy()
        for method in ALL_METHODS:
            if method not in w:
                continue
            v = w[method].to_numpy()
            if method == "BTYD":
                p = np.nan
            else:
                diff = v - btyd
                p = 1.0 if np.allclose(diff, 0) else stats.wilcoxon(v, btyd).pvalue
            summary.append(dict(dataset=dataset, cond=cond, metric=metric, method=method,
                                mean=v.mean(), sd=v.std(ddof=1), vs_BTYD_p=p, n_seeds=len(w)))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "ml_study_summary.csv", index=False)

    # ---- headline table: per dataset, CRPS + PIT-KS for all methods (all customers) ---- #
    def row(dataset, metric):
        r = sm[(sm.dataset == dataset) & (sm["cond"] == "all") & (sm.metric == metric)]
        vals = {m: r[r.method == m]["mean"].iloc[0] for m in ALL_METHODS if (r.method == m).any()}
        best = min(vals, key=vals.get)
        cells = "".join(f"{vals[m]:>10.3f}" + ("*" if m == best else " ") for m in ALL_METHODS)
        return f"{dataset:15s}{metric:8s}{cells}   best={best}"

    print("\n=== Multi-seed study: BTYD vs ML (mean over seeds, all customers; * = best) ===")
    print(f"{'dataset':15s}{'metric':8s}" + "".join(f"{m:>11s}" for m in ALL_METHODS))
    for ds in ORDER:
        if ((sm.dataset == ds).any()):
            print(row(ds, "CRPS"))
            print(row(ds, "pit_ks"))
    print(f"\n[saved] {RES/'ml_study_raw.csv'} and {RES/'ml_study_summary.csv'}")


if __name__ == "__main__":
    main()
