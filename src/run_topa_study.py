"""
Explicit Top-A% customer-identification task (Simon 2025's task 3), surfaced as its own result.

Simon evaluates the identification of the top 10%/20% of the customer base as a distinct managerial
task; our draft folded it into the count and profit analyses. Here we report it directly. For each
method we rank the held-out customers by their predicted future purchasing and take the top A%, then
measure (i) the HIT RATE---the fraction of the model's Top-A% that are truly in the Top-A% (equal to
precision and recall at k, since the two sets are the same size)---and (ii) the VALUE CAPTURED---the
realised future purchases of the predicted Top-A% as a share of the oracle Top-A%.

Because identification is about the *ordering* of customers rather than the calibration of intervals,
it is a useful counterpoint to the calibration map: a model whose intervals miscalibrate on dense
data may still rank customers well.

Methods: BTYD (Pareto/NBD, MCMC), heuristic (Simon eq.13), Poisson-GBM. Evaluated on a common
held-out split. Saves results/topa_study_summary.csv; prints the table.

Run:  python src/run_topa_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_profit_study import _predictive_means                   # noqa: E402
from run_ml_study import build_providers                         # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 8
FRACS = [0.10, 0.20]
# Olist is excluded (1.6% active cannot support a top decile); all other real cohorts are included.
DATASETS = ["Simulated", "CDNow", "Grocery", "OnlineRetailII", "Dunnhumby", "Ta-Feng"]


def topa_metrics(pred_score, y_true, frac):
    """Hit rate and realised-value capture of the predicted Top-`frac` vs the oracle Top-`frac`."""
    n = len(y_true)
    k = max(1, int(round(frac * n)))
    pred_top = np.argsort(-pred_score, kind="stable")[:k]
    true_top = np.argsort(-y_true, kind="stable")[:k]
    hit = len(np.intersect1d(pred_top, true_top)) / k
    captured = y_true[pred_top].sum() / max(y_true[true_top].sum(), 1e-9)
    return hit, captured


def main():
    providers = build_providers()
    methods = ["BTYD", "heuristic", "PoissonGBM"]
    rows = []
    for name in DATASETS:
        get = providers[name]
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            y = df[f"x_star_{h}"].to_numpy(float)
            n = len(df)
            rng = np.random.default_rng(2000 + seed)
            idx = rng.permutation(n)
            n_test = int(round(0.3 * n))
            test_idx, train_idx = np.sort(idx[:n_test]), np.sort(idx[n_test:])
            y_test = y[test_idx]
            means = _predictive_means(df, h, test_idx, train_idx, seed=7000 + seed)
            for m in methods:
                for frac in FRACS:
                    hit, cap = topa_metrics(means[m], y_test, frac)
                    rows.append(dict(dataset=name, seed=seed, method=m, frac=frac,
                                     hit_rate=hit, captured=cap))
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    raw.to_csv(RES / "topa_study_raw.csv", index=False)
    summ = raw.groupby(["dataset", "method", "frac"]).agg(
        hit_rate=("hit_rate", "mean"), captured=("captured", "mean")).reset_index()
    summ.to_csv(RES / "topa_study_summary.csv", index=False)

    for frac in FRACS:
        print(f"\n=== Top-{int(frac*100)}% identification (hit rate | value captured), mean over seeds ===")
        print(f"  {'dataset':16s}" + "".join(f"{m:>22s}" for m in methods))
        for ds in DATASETS:
            cells = ""
            for m in methods:
                r = summ[(summ.dataset == ds) & (summ.method == m) & (summ.frac == frac)]
                if r.empty:
                    cells += f"{'-':>22s}"
                else:
                    cells += f"{r.hit_rate.iloc[0]:>11.2f}{r.captured.iloc[0]:>11.2f}"
            print(f"  {ds:16s}{cells}")
    print("\n(each cell: hit rate | value captured; 1.00 = oracle)")
    print(f"[saved] {RES/'topa_study_summary.csv'}")


if __name__ == "__main__":
    main()
