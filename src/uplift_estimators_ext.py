"""
Gear 2, Stage A — the two novelty-bearing estimators, added to the harness (run_uplift_study.py):

  1. structural_btyd_cate  -- a MODEL-BASED uplift: estimate a per-arm (and per-RFM-bucket) dropout
     rate by method-of-moments, plug into the Pareto/NBD closed-form expected-outcome, and difference.
     The causal analogue of Gear 1's structural forecaster. It captures effect heterogeneity only
     through lambda and coarse buckets, so we expect it to recover the ATE / homogeneous case well but
     to miss fine effect heterogeneity that the black-box learners catch -- the structural-vs-black-box
     contrast, echoing Gear 1.

  2. conformal_ite         -- split-conformal prediction intervals for the individual treatment effect
     (Lei & Candes 2021 style: conformalize each potential-outcome regression, combine conservatively).
     The REPAIR for the overconfident causal-forest intervals -> should restore >= nominal coverage,
     the payoff of the calibration-of-effects differentiator.

Both are import-light (numpy/scipy/sklearn + LightGBM via run_uplift_study._rf_reg) and return the same
(cate_hat, ci_or_None) contract the harness expects.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from sklearn.model_selection import train_test_split

from simulate_intervention import _expected_count


def _lam_hat(x, T_cal):
    return np.clip(x / np.maximum(T_cal, 1e-6), 1e-3, None)


def _solve_mu(lam_bucket, mean_future_count, h):
    """Method-of-moments: find mu s.t. mean_i E[count | lam_i, mu, h] == observed mean future count.
    E[count] = (lam/mu)(1-e^{-mu h}) is decreasing in mu, so a 1-D root solve is well posed."""
    if mean_future_count <= 1e-9:
        return 5.0                                   # ~everyone dropped: high dropout
    def gap(mu):
        return _expected_count(lam_bucket, mu, h).mean() - mean_future_count
    lo, hi = 1e-3, 5.0
    if gap(lo) < 0:      # even minimal dropout under-predicts -> lambda too small; clamp
        return lo
    if gap(hi) > 0:
        return hi
    return brentq(gap, lo, hi, maxiter=100)


def structural_btyd_cate(df_tr, df_te, horizon, outcome="clv", n_buckets=4):
    """Structural (parametric) CATE. Fits per-(arm, frequency-bucket) dropout by MoM on the factual
    future counts, then differences the Pareto/NBD closed-form expected outcome. Returns (cate_hat, None)."""
    h = float(horizon)
    xtr, Ttr = df_tr["x"].to_numpy(float), df_tr["T"].to_numpy(int)
    lam_tr = _lam_hat(xtr, df_tr["T_cal"].to_numpy(float))
    yc_tr = df_tr["y_count"].to_numpy(float)
    # frequency buckets from the TRAIN distribution
    edges = np.quantile(xtr, np.linspace(0, 1, n_buckets + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    b_tr = np.clip(np.digitize(xtr, edges[1:-1]), 0, n_buckets - 1)
    mu = {0: np.full(n_buckets, np.nan), 1: np.full(n_buckets, np.nan)}
    for a in (0, 1):
        for b in range(n_buckets):
            m = (Ttr == a) & (b_tr == b)
            mu[a][b] = _solve_mu(lam_tr[m], yc_tr[m].mean(), h) if m.sum() >= 20 else np.nan
    # fill empty buckets with the arm's pooled estimate
    for a in (0, 1):
        pooled = _solve_mu(lam_tr[Ttr == a], yc_tr[Ttr == a].mean(), h)
        mu[a] = np.where(np.isnan(mu[a]), pooled, mu[a])
    # mean spend per purchase (for CLV) from observed data
    tot_c = df_tr["y_count"].sum()
    nu = (df_tr["y_clv"].sum() / tot_c) if tot_c > 0 else 1.0

    xte = df_te["x"].to_numpy(float)
    lam_te = _lam_hat(xte, df_te["T_cal"].to_numpy(float))
    b_te = np.clip(np.digitize(xte, edges[1:-1]), 0, n_buckets - 1)
    mu0 = mu[0][b_te]; mu1 = mu[1][b_te]
    cate_count = _expected_count(lam_te, mu1, h) - _expected_count(lam_te, mu0, h)
    cate = cate_count * nu if outcome == "clv" else cate_count
    return cate, None


def conformal_ite(Xtr, Ttr, Ytr, Xte, base_reg, alpha=0.10, seed=0):
    """Split-conformal ITE intervals (Lei & Candes 2021, naive combine). Conformalize each arm's
    outcome regression on a held-out calibration split; the ITE interval is the (conservative)
    difference of the two potential-outcome bands. Returns (cate_hat, (lo, hi))."""
    idx = np.arange(len(Xtr))
    fit, cal = train_test_split(idx, test_size=0.5, random_state=seed, stratify=Ttr)

    def arm(a):
        m = base_reg()
        sel = fit[Ttr[fit] == a]
        m.fit(Xtr[sel], Ytr[sel])
        cs = cal[Ttr[cal] == a]
        resid = np.abs(Ytr[cs] - m.predict(Xtr[cs]))
        # finite-sample conformal quantile
        n = len(resid); q = min(1.0, np.ceil((n + 1) * (1 - alpha)) / max(n, 1))
        hw = np.quantile(resid, q) if n else 0.0
        return m, hw

    m1, hw1 = arm(1)
    m0, hw0 = arm(0)
    p1, p0 = m1.predict(Xte), m0.predict(Xte)
    cate = p1 - p0
    hw = hw1 + hw0                                    # conservative combine
    return cate, (cate - hw, cate + hw)
