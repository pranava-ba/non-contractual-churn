"""
Phase 2, Step 4: run the Pareto/NBD-vs-ML calibration benchmark across all public datasets.

For each dataset, fit BTYD (MCMC) and the Poisson-GBM on a fair train/test customer split and
score both under CRPS / randomized-PIT / coverage. Saves results/ml_benchmark.csv and prints a
table. First pass = one seed per dataset; the paper version repeats over seeds.

Run:  python src/run_ml_benchmark.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import load_cdnow, load_grocery, elog_to_summary   # noqa: E402
from datasets import load_summary, REGISTRY                       # noqa: E402
from ml_benchmark import compare_btyd_vs_gbm                      # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"


def all_datasets():
    yield "CDNow", elog_to_summary(load_cdnow(), 39, 26), 26
    yield "Grocery", elog_to_summary(load_grocery(), 52, 26), 26
    for name in REGISTRY:
        df, h = load_summary(name)
        yield name, df, h


def main():
    rows = []
    for i, (name, df, h) in enumerate(all_datasets()):
        t = time.time()
        res = compare_btyd_vs_gbm(df, h, seed=100 + i)
        for key, s in res.items():
            if isinstance(key, tuple):
                method, cond = key
                rows.append(dict(dataset=name, N=len(df), horizon=h,
                                 n_test=res["_n_test"], pct_active=res["_pct_active_test"],
                                 method=method, cond=cond, **s))
        pd.DataFrame(rows).to_csv(RES / "ml_benchmark.csv", index=False)
        print(f"[{name}] N={len(df)} done ({time.time()-t:.0f}s)", flush=True)

    d = pd.DataFrame(rows)
    print("\n=== BTYD vs GBM — CRPS (accuracy) and PIT-KS (calibration), all customers ===")
    print(f"{'dataset':15s}{'CRPS_BTYD':>10s}{'CRPS_GBM':>10s}{'PITKS_BTYD':>11s}{'PITKS_GBM':>10s}")
    for name in d.dataset.unique():
        g = d[(d.dataset == name) & (d["cond"] == "all")]
        b = g[g.method == "BTYD"].iloc[0]; m = g[g.method == "GBM"].iloc[0]
        print(f"{name:15s}{b['CRPS']:>10.3f}{m['CRPS']:>10.3f}{b['pit_ks']:>11.3f}{m['pit_ks']:>10.3f}")
    print(f"\n[saved] {RES / 'ml_benchmark.csv'}")


if __name__ == "__main__":
    main()
