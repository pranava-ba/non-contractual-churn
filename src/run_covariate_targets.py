"""
Does the covariate null (RFM already carries the signal) generalise beyond value to counts and churn?

The main text shows demographics add nothing over RFM for the monetary target (Section: CLV). A
referee will ask whether that is value-specific. We repeat the test on the two other targets that
have an ML forecaster---the purchase count and the active/churn probability---on the same 801
Dunnhumby households that carry demographics (age, income, marital status, home ownership, household
composition, children). For each target we compare an RFM-only ML forecaster with an RFM+demographics
one, over many splits, with a paired Wilcoxon on the difference.

Saves results/covariate_targets_summary.csv; prints the table.  Run: python src/run_covariate_targets.py
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
from covariate_benchmark import load_demographics                   # noqa: E402
from ml_benchmark import rfm_features, poisson_gbm_forecast         # noqa: E402
from score import score_forecast                                   # noqa: E402
from churn import ece, churn_scores                                # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 10


def compare(seed: int, test_frac: float = 0.3):
    from sklearn.ensemble import HistGradientBoostingClassifier
    cohort, h = load_summary("Dunnhumby")
    demo = load_demographics()
    df = cohort.merge(demo, on="cust", how="inner").reset_index(drop=True)
    demo_cols = [c for c in demo.columns if c != "cust"]

    y = df[f"x_star_{h}"].to_numpy(float)
    active = (y > 0).astype(int)
    n = len(df)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test, train = np.sort(idx[:n_test]), np.sort(idx[n_test:])

    X_rfm = rfm_features(df)
    X_full = np.hstack([X_rfm, df[demo_cols].to_numpy(float)])
    out = {}
    for tag, X in [("RFM", X_rfm), ("RFM+demo", X_full)]:
        # counts
        pred = poisson_gbm_forecast(X[train], y[train], X[test], seed=seed + 1)
        sc = score_forecast(pred, y[test], np.random.default_rng(seed + 2))
        # churn
        a_tr = active[train]
        if a_tr.min() == a_tr.max():
            p = np.full(len(test), float(a_tr.mean()))
        else:
            clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                                 min_samples_leaf=30, l2_regularization=1.0,
                                                 random_state=seed)
            clf.fit(X[train], a_tr)
            p = clf.predict_proba(X[test])[:, 1]
        cs = churn_scores(p, active[test])
        out[tag] = dict(count_pit_ks=sc["pit_ks"], count_CRPS=sc["CRPS"],
                        churn_ece=cs["ece"], churn_brier=cs["brier"])
    return out, len(df)


def main():
    rows = []
    N = 0
    t = time.time()
    for seed in range(SEEDS):
        res, N = compare(seed)
        for tag in ("RFM", "RFM+demo"):
            rows.append(dict(seed=seed, features=tag, **res[tag]))
    raw = pd.DataFrame(rows)
    raw.to_csv(RES / "covariate_targets_summary.csv", index=False)

    print(f"Covariate value on the Dunnhumby demographic subset (N={N}, {SEEDS} seeds, {time.time()-t:.0f}s)")
    print(f"  {'metric':14s}{'RFM':>10s}{'RFM+demo':>12s}{'wilcoxon p':>12s}")
    for metric in ["count_pit_ks", "count_CRPS", "churn_ece", "churn_brier"]:
        a = raw[raw.features == "RFM"][metric].to_numpy()
        b = raw[raw.features == "RFM+demo"][metric].to_numpy()
        p = 1.0 if np.allclose(a, b) else stats.wilcoxon(a, b).pvalue
        print(f"  {metric:14s}{a.mean():>10.3f}{b.mean():>12.3f}{p:>12.3f}")
    print("\nHigh p-values => demographics add nothing over RFM for that target (covariate null holds).")
    print(f"[saved] {RES/'covariate_targets_summary.csv'}")


if __name__ == "__main__":
    main()
