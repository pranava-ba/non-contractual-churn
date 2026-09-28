"""
Gear 2, Stage A — follow-up studies that close out the benchmark (run after the main factorial):

  1. coverage    high-tree CausalForest + conformal-ITE, to pin down the calibration headline
                 (separate genuine miscalibration from few-tree noise). -> gear2_coverage_summary.csv
  2. regret      a scale-meaningful policy metric (per-customer regret vs oracle) reported alongside
                 the ratio-based policy_pct, which is inflated under sleeping dogs.
  3. ablation    does the BTYD posterior state help the causal model vs raw RFM covariates?
                 CausalForest on [RFM] vs [RFM + P(alive), E[future]]. -> gear2_ablation_summary.csv

Writes to its OWN csvs so it never clobbers results/gear2_uplift_summary.csv.
Run:  python src/run_uplift_extras.py coverage
      python src/run_uplift_extras.py ablation
"""
from __future__ import annotations

import sys
import time
import warnings
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams                                        # noqa: E402
from simulate_intervention import InterventionConfig, simulate_intervention, _expected_count, _p_active  # noqa: E402
from run_uplift_study import (BASE_PARAMS, HORIZON, TARGETS, STRUCTURES, ASSIGNMENTS,  # noqa: E402
                              features, _rf_reg, _rf_clf, RES)
from uplift_estimators_ext import conformal_ite, _lam_hat                 # noqa: E402


def policy_metrics(score, cate_true, budget=0.30):
    """Return (policy_pct, regret_per_customer). Regret = oracle-captured − method-captured true-CATE
    at the same budget, per customer (scale-meaningful, never ratio-inflated). Lower regret = better."""
    n = len(score); k = max(1, int(budget * n))
    captured = cate_true[np.argsort(-score)[:k]].sum()
    oracle = np.sort(cate_true)[::-1][:k].sum()
    pct = captured / oracle if oracle > 1e-9 else np.nan
    return pct, float((oracle - captured) / n)


def btyd_state_features(df):
    """Cheap Pareto/NBD-flavoured posterior state to append to RFM: a P(alive) proxy and an expected
    future-count proxy, from method-of-moments (lambda, mu). Uses the SAME closed forms as the DGP's
    ground truth but with ESTIMATED rates (so it is legitimately available to an estimator)."""
    x = df["x"].to_numpy(float); t_x = df["t_x"].to_numpy(float); T_cal = df["T_cal"].to_numpy(float)
    lam = _lam_hat(x, T_cal)
    # population dropout by MoM: match observed mean recency-gap (T_cal - t_x) to 1/mu
    gap = np.maximum(T_cal - t_x, 1e-6)
    mu = 1.0 / max(gap.mean(), 1e-3)
    mu_i = np.clip(1.0 / gap, 1e-3, 5.0)                     # per-customer recency-implied dropout
    p_alive = np.exp(-mu_i * gap * 0.0 + np.log(_p_active(lam, mu, HORIZON)))  # cohort P(active) proxy
    e_future = _expected_count(lam, mu, HORIZON)
    return np.column_stack([p_alive, e_future, mu_i])


def _cell_coverage(target, structure, assignment, delta, seed, n_trees):
    warnings.filterwarnings("ignore")
    from econml.dml import CausalForestDML
    from sklearn.model_selection import train_test_split
    rng = np.random.default_rng(2000 + seed)
    df = simulate_intervention(DatasetParams(**BASE_PARAMS),
                               InterventionConfig(target, structure, delta, assignment, horizon=HORIZON),
                               rng=rng)
    X = features(df); T = df["T"].to_numpy(int); Y = df["y_clv"].to_numpy(float)
    cate = df["cate_clv"].to_numpy(float)
    tr, te = train_test_split(np.arange(len(df)), test_size=0.3, random_state=seed)
    out = []
    cf = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                         n_estimators=n_trees, min_samples_leaf=20, random_state=0)
    cf.fit(Y[tr], T[tr], X=X[tr]); lb, ub = cf.effect_interval(X[te], alpha=0.10)
    cov = float(np.mean((cate[te] >= lb) & (cate[te] <= ub)))
    pct, reg = policy_metrics(cf.effect(X[te]), cate[te])
    out.append(dict(estimator=f"CausalForest_{n_trees}t", coverage90=cov, policy_pct=pct, regret=reg))
    ch, (clo, chi) = conformal_ite(X[tr], T[tr], Y[tr], X[te], _rf_reg, seed=seed)
    covc = float(np.mean((cate[te] >= clo) & (cate[te] <= chi)))
    pctc, regc = policy_metrics(ch, cate[te])
    out.append(dict(estimator="conformal_ITE", coverage90=covc, policy_pct=pctc, regret=regc))
    for r in out:
        r.update(target=target, structure=structure, assignment=assignment, delta=delta, seed=seed)
    return out


def run_coverage(n_trees=1200, seeds=10):
    cells = list(product(TARGETS, STRUCTURES, ASSIGNMENTS, [0.5], range(seeds)))
    print(f"Coverage study: {len(cells)} cells, CausalForest@{n_trees} trees + conformal-ITE...")
    t0 = time.time()
    rows = Parallel(n_jobs=-1)(delayed(_cell_coverage)(*c[:4], c[4], n_trees) for c in cells)
    res = pd.DataFrame([r for cell in rows for r in cell])
    res.to_csv(RES / "gear2_coverage_summary.csv", index=False)
    print(f"wrote gear2_coverage_summary.csv ({time.time()-t0:.0f}s)\n")
    print("=== coverage90 (nominal 0.90) & regret by estimator x assignment ===")
    print(res.pivot_table(index="estimator", columns="assignment",
                          values="coverage90", aggfunc="mean").round(3).to_string())
    print("\n=== policy_pct & regret overall ===")
    print(res.groupby("estimator")[["policy_pct", "regret"]].mean().round(3).to_string())
    return res


def _cell_ablation(target, structure, assignment, delta, seed):
    warnings.filterwarnings("ignore")
    from econml.dml import CausalForestDML
    from sklearn.model_selection import train_test_split
    rng = np.random.default_rng(3000 + seed)
    df = simulate_intervention(DatasetParams(**BASE_PARAMS),
                               InterventionConfig(target, structure, delta, assignment, horizon=HORIZON),
                               rng=rng)
    Xr = features(df); Xb = np.column_stack([Xr, btyd_state_features(df)])
    T = df["T"].to_numpy(int); Y = df["y_clv"].to_numpy(float); cate = df["cate_clv"].to_numpy(float)
    tr, te = train_test_split(np.arange(len(df)), test_size=0.3, random_state=seed)
    out = []
    for name, X in [("rfm", Xr), ("rfm+btyd", Xb)]:
        cf = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                             n_estimators=200, min_samples_leaf=20, random_state=0)
        cf.fit(Y[tr], T[tr], X=X[tr]); ch = cf.effect(X[te])
        pct, reg = policy_metrics(ch, cate[te])
        rank = float(spearmanr(ch, cate[te]).correlation) if np.std(ch) > 0 else np.nan
        out.append(dict(features=name, rank=rank, policy_pct=pct, regret=reg,
                        target=target, structure=structure, assignment=assignment, delta=delta, seed=seed))
    return out


def run_ablation(seeds=10):
    cells = list(product(TARGETS, STRUCTURES, ASSIGNMENTS, [0.5], range(seeds)))
    print(f"Feature ablation: {len(cells)} cells, CausalForest on RFM vs RFM+BTYD-state...")
    t0 = time.time()
    rows = Parallel(n_jobs=-1)(delayed(_cell_ablation)(*c) for c in cells)
    res = pd.DataFrame([r for cell in rows for r in cell])
    res.to_csv(RES / "gear2_ablation_summary.csv", index=False)
    print(f"wrote gear2_ablation_summary.csv ({time.time()-t0:.0f}s)\n")
    print("=== rank & policy_pct & regret by feature set x structure ===")
    print(res.pivot_table(index="features", columns="structure",
                          values=["rank", "policy_pct"], aggfunc="mean").round(3).to_string())
    return res


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "coverage"
    if what == "coverage":
        run_coverage()
    elif what == "ablation":
        run_ablation()
    else:
        print("usage: run_uplift_extras.py [coverage|ablation]")
