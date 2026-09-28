"""
Gear 2 -- the ``paretonbd`` PRESCRIPTIVE module (roadmap `deep_research/GEAR2_ROADMAP.md` §3 item
20): a stable, importable API over the estimator and policy-evaluation machinery built and
validated in Stage A/B (`simulate_intervention.py`, `uplift_estimators_ext.py`,
`run_uplift_study.py`, `run_uplift_dunnhumby.py`, `run_uplift_hillstrom.py`). See `docs/uplift.md`
for the narrative write-up and findings this wraps.

Four public entry points:
  estimate_uplift(X, T, Y, Xte, method=...)        -> (cate_hat, ci_or_None)
  target_policy(score, margin=, cost=, budget=)     -> 0/1 targeting decision
  dr_policy_value(...) / oracle_policy_value(...)   -> realised policy value (real / synthetic data)
  qini_auc(...) / qini_curve(...)                   -> targeting quality on randomized data

`structural_btyd_cate` and `conformal_ite` are re-exported for discoverability, but keep their own
(BTYD-specific / generic-X) data contracts -- see their docstrings in `uplift_estimators_ext.py`.

Requires the `causal` optional-dependency group for anything beyond `target_policy`,
`dr_policy_value` and `oracle_policy_value` (those three are pure numpy).
"""
from __future__ import annotations

import numpy as np

from uplift_estimators_ext import structural_btyd_cate, conformal_ite  # noqa: F401  (re-export)

METHODS = ("t_learner", "x_learner", "dr_learner", "causal_forest", "conformal_ite")
LIBRARIES = ("econml", "causalml")


def _rf_reg():
    from run_uplift_study import _rf_reg as _r
    return _r()


def _rf_clf():
    from run_uplift_study import _rf_clf as _c
    return _c()


def estimate_uplift(X, T, Y, Xte, method="causal_forest", library="econml", alpha=0.10, seed=0):
    """Fit a CATE/uplift estimator on (X, T, Y) and score it on Xte.

    `method` in {"t_learner", "x_learner", "dr_learner", "causal_forest", "conformal_ite"}.
    `library` in {"econml", "causalml"} -- only "t_learner"/"x_learner" implement both (the Stage-A
    bake-off found they agree exactly on a matched base learner: rank-corr 1.000); "dr_learner" and
    "causal_forest" are econml-only, "conformal_ite" is library-agnostic (sklearn base learner).

    Returns (cate_hat, ci_or_None): `ci` is a (lo, hi) pair of arrays when the method produces
    intervals (causal_forest, conformal_ite), else None.
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {METHODS}")
    if library not in LIBRARIES:
        raise ValueError(f"unknown library {library!r}; choose from {LIBRARIES}")
    X = np.asarray(X, float)
    T = np.asarray(T, int)
    Y = np.asarray(Y, float)
    Xte = np.asarray(Xte, float)

    if method == "conformal_ite":
        return conformal_ite(X, T, Y, Xte, _rf_reg, alpha=alpha, seed=seed)

    if method == "t_learner":
        if library == "causalml":
            from causalml.inference.meta import BaseTRegressor
            m = BaseTRegressor(learner=_rf_reg(), control_name=0)
            m.fit(X=X, treatment=T, y=Y)
            return m.predict(Xte).ravel(), None
        from econml.metalearners import TLearner
        m = TLearner(models=_rf_reg())
        m.fit(Y, T, X=X)
        return m.effect(Xte), None

    if method == "x_learner":
        if library == "causalml":
            from causalml.inference.meta import BaseXRegressor
            m = BaseXRegressor(learner=_rf_reg(), control_name=0)
            m.fit(X=X, treatment=T, y=Y)
            return m.predict(Xte).ravel(), None
        from econml.metalearners import XLearner
        m = XLearner(models=_rf_reg(), propensity_model=_rf_clf())
        m.fit(Y, T, X=X)
        return m.effect(Xte), None

    if method == "dr_learner":
        if library == "causalml":
            raise ValueError("dr_learner is econml-only (causalml has no DR meta-learner)")
        from econml.dr import DRLearner
        m = DRLearner(model_propensity=_rf_clf(), model_regression=_rf_reg(),
                      model_final=_rf_reg(), cv=3)
        m.fit(Y, T, X=X)
        return m.effect(Xte), None

    # method == "causal_forest"
    if library == "causalml":
        raise ValueError("causal_forest is econml-only in this module (causalml has uplift "
                         "trees/forests under a different API -- not wrapped here)")
    from econml.dml import CausalForestDML
    m = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                        n_estimators=200, min_samples_leaf=20, random_state=seed)
    m.fit(Y, T, X=X)
    lb, ub = m.effect_interval(Xte, alpha=alpha)
    return m.effect(Xte), (lb, ub)


def target_policy(score, margin=None, cost=None, budget=None):
    """Turn an uplift/value score into a binary targeting decision.

    Either a threshold policy -- pi = 1[margin*score - cost > 0], the Gear 2 roadmap's
    `M*tau_hat - c` rule -- via `margin` and `cost`, or a budget-constrained top-k policy (target
    the top `budget` fraction, budget in (0, 1]) via `budget`. Exactly one mode must be given.
    Returns an int 0/1 array, same length as `score`.
    """
    score = np.asarray(score, float)
    if budget is not None:
        if margin is not None or cost is not None:
            raise ValueError("pass either `budget` or (`margin`, `cost`), not both")
        n = len(score)
        k = max(1, int(round(budget * n)))
        pi = np.zeros(n, int)
        pi[np.argsort(-score)[:k]] = 1
        return pi
    if margin is not None and cost is not None:
        return (margin * score - cost > 0).astype(int)
    raise ValueError("target_policy needs either `budget` or both `margin` and `cost`")


def fit_dr_nuisances(Xtr, Ttr, Ytr, Xte):
    """Fit the propensity + per-arm outcome nuisance models a doubly-robust policy value needs, on
    a TRAIN fold, evaluated on Xte. Returns (ehat, m1hat, m0hat), ehat clipped to [0.05, 0.95] for
    overlap. Same fit pattern as `run_uplift_dunnhumby.main` (generalized out of that script)."""
    Xtr = np.asarray(Xtr, float)
    Ttr = np.asarray(Ttr, int)
    Ytr = np.asarray(Ytr, float)
    Xte = np.asarray(Xte, float)
    e = _rf_clf()
    e.fit(Xtr, Ttr)
    ehat = np.clip(e.predict_proba(Xte)[:, 1], 0.05, 0.95)
    m1 = _rf_reg()
    m1.fit(Xtr[Ttr == 1], Ytr[Ttr == 1])
    m1hat = m1.predict(Xte)
    m0 = _rf_reg()
    m0.fit(Xtr[Ttr == 0], Ytr[Ttr == 0])
    m0hat = m0.predict(Xte)
    return ehat, m1hat, m0hat


def dr_policy_value(pi, T, Y, ehat, m1hat, m0hat, cost=0.0):
    """Doubly-robust NET value (revenue minus per-contact cost) of a targeting policy `pi` (0/1 per
    customer) under OBSERVATIONAL, possibly-confounded assignment. `ehat` = P(T=1|X), `m1hat`/
    `m0hat` = E[Y|X,T=1]/E[Y|X,T=0], all fit on a train fold disjoint from the customers `pi`/`T`/
    `Y` are evaluated on (see `fit_dr_nuisances`). `cost` (default 0.0, same units as `Y`) is
    charged per customer with `pi==1` -- a policy that contacts everyone (`pi` all-ones) pays it on
    100% of customers, a budget-constrained policy only on the customers it actually targets, so a
    nonzero cost penalizes untargeted "treat everyone" policies relative to a concentrated one.
    Same formula as `run_uplift_dunnhumby.dr_values`'s `value()` closure, validated there (and in
    `tests/test_gear2.py`) against a synthetic known-nuisance case: with correct nuisances and
    cost=0.0, this recovers the true E[Y | do(pi)] exactly."""
    pi = np.asarray(pi, int)
    T = np.asarray(T, int)
    Y = np.asarray(Y, float)
    ehat = np.asarray(ehat, float)
    m1hat = np.asarray(m1hat, float)
    m0hat = np.asarray(m0hat, float)
    p_obs = np.where(T == 1, ehat, 1 - ehat)
    m_obs = np.where(T == 1, m1hat, m0hat)
    mu_pi = np.where(pi == 1, m1hat, m0hat)
    match = (T == pi).astype(float)
    raw = float(np.mean(mu_pi + match / p_obs * (Y - m_obs)))
    return raw - cost * float(np.mean(pi))


def oracle_policy_value(score, cate_true, budget=0.30):
    """Synthetic-only: the top-`budget` policy's captured true CATE as a fraction of the oracle's
    (1.0 = oracle targeting; can go negative if the policy targets negative-CATE customers). Needs
    the simulator's ground-truth CATE (`simulate_intervention.py`) -- Stage A validation only, not
    usable on real data. Thin re-export of `run_uplift_study.policy_pct_oracle`."""
    from run_uplift_study import policy_pct_oracle
    return policy_pct_oracle(score, cate_true, budget=budget)


def qini_auc(y, uplift, treatment):
    """Qini AUC: targeting quality, unbiased only under RANDOMIZED treatment assignment (use
    `dr_policy_value` for observational data instead). Thin wrapper over `scikit-uplift`'s
    `qini_auc_score` (part of the `causal` optional-dependency group)."""
    from sklift.metrics import qini_auc_score
    return float(qini_auc_score(y, uplift, treatment))


def qini_curve(y, uplift, treatment):
    """Qini curve points for plotting (randomized data only -- see `qini_auc`). Thin wrapper over
    `scikit-uplift`'s `qini_curve`. Returns (x, y) arrays."""
    from sklift.metrics import qini_curve as _qini_curve
    x, y_ = _qini_curve(y, uplift, treatment)
    return np.asarray(x), np.asarray(y_)
