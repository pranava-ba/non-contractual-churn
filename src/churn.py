"""
Phase 2, Step 9: churn / active-customer calibration.

The paper's title foregrounds churn; this scores it directly. Each model implies, for every
customer, a probability of being *active* in the forecast window -- P(x* > 0) = P(not churned and
buys). We ask whether that probability is calibrated as a classifier: among customers the model
says are 30% likely to be active, do ~30% actually buy? We measure the Brier score and the expected
calibration error (ECE, from a reliability curve), comparing structural Pareto/NBD's implied
P(active) against a trained ML classifier on RFM features.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml_benchmark import rfm_features                              # noqa: E402


def ece(p, outcome, n_bins: int = 10) -> float:
    """Expected calibration error: weighted gap between predicted prob and observed rate per bin."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, n_bins - 1)
    N = len(p)
    e = 0.0
    for b in range(n_bins):
        m = idx == b
        if m.any():
            e += m.sum() / N * abs(p[m].mean() - outcome[m].mean())
    return float(e)


def churn_scores(p_active, outcome) -> dict:
    o = np.asarray(outcome, float)
    p = np.clip(np.asarray(p_active, float), 0.0, 1.0)
    return {"brier": float(np.mean((p - o) ** 2)), "ece": ece(p, o),
            "p_active_mean": float(p.mean()), "active_rate": float(o.mean())}


def compare_churn(df, horizon: int, test_frac: float = 0.3, seed: int = 0, mcmc_draws: int = 1500):
    """Brier + ECE of the active-customer probability: structural BTYD vs. an ML classifier."""
    from estimate import fit_mcmc
    from score import spp_predict
    from sklearn.ensemble import HistGradientBoostingClassifier

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    n = len(df)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test_idx, train_idx = np.sort(idx[:n_test]), np.sort(idx[n_test:])

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    p_btyd = (pred[:, test_idx] > 0).mean(axis=0)         # implied P(active) from the predictive

    X = rfm_features(df)
    a_train = (y[train_idx] > 0).astype(int)
    if a_train.min() == a_train.max():
        p_ml = np.full(len(test_idx), float(a_train.mean()))
    else:
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                             min_samples_leaf=30, l2_regularization=1.0,
                                             random_state=seed)
        clf.fit(X[train_idx], a_train)
        p_ml = clf.predict_proba(X[test_idx])[:, 1]

    o = y[test_idx] > 0
    return {"BTYD": churn_scores(p_btyd, o), "ML": churn_scores(p_ml, o), "_n_test": len(test_idx)}


if __name__ == "__main__":
    from empirical import load_cdnow, load_grocery, elog_to_summary
    from datasets import load_summary

    cases = [("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26),
             ("Grocery", elog_to_summary(load_grocery(), 52, 26), 26),
             ("OnlineRetailII", *load_summary("OnlineRetailII"))]
    print(f"{'dataset':15s}{'method':6s}{'Brier':>8s}{'ECE':>8s}{'P(act)':>8s}{'actual':>8s}")
    for name, df, h in cases:
        res = compare_churn(df, h, seed=1)
        for m in ["BTYD", "ML"]:
            s = res[m]
            print(f"{name:15s}{m:6s}{s['brier']:>8.3f}{s['ece']:>8.3f}"
                  f"{s['p_active_mean']:>8.3f}{s['active_rate']:>8.3f}")
