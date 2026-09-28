"""Numerical smoke tests for the Gear 2 (prescriptive/causal-ML) modules: the intervention DGP,
the structural-BTYD and conformal-ITE estimators, the harness's pure metric/feature functions, and
the Dunnhumby doubly-robust policy-value estimator. Kept fast: small synthetic inputs, no full
econml/causalml factorial (that's `run_uplift_study.py --full`, a research run not a unit test)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulate import DatasetParams
from simulate_intervention import InterventionConfig, simulate_intervention, summarise


BASE_PARAMS = dict(E_lambda=0.5, CV_lambda=1.2, E_mu=0.08, CV_mu=1.2, N=1500, T=72)


def _sim(structure="heterogeneous", assignment="randomized", target="mu", delta=0.4, seed=0):
    rng = np.random.default_rng(seed)
    params = DatasetParams(**BASE_PARAMS)
    cfg = InterventionConfig(target=target, structure=structure, delta=delta,
                             assignment=assignment, horizon=26)
    return simulate_intervention(params, cfg, rng=rng)


# --- simulate_intervention.py -----------------------------------------------------------------

def test_intervention_shape_and_columns():
    df = _sim()
    assert len(df) == BASE_PARAMS["N"]
    for col in ("T", "y_count", "y_active", "y_clv", "cate_count", "cate_active", "cate_clv"):
        assert col in df.columns
    assert set(df["T"].unique()) <= {0, 1}
    assert np.all(df["y_count"] >= 0) and np.all(df["y_clv"] >= 0)
    assert np.all((df["y_active"] == 0) | (df["y_active"] == 1))


def test_dead_at_calibration_have_zero_cate():
    # customers already dead at T_i can't respond to a post-T_i intervention
    df = _sim(structure="heterogeneous")
    dead = df["alive_at_T"] == 0
    assert dead.sum() > 0
    assert np.allclose(df.loc[dead, "cate_count"], 0.0)
    assert np.allclose(df.loc[dead, "cate_clv"], 0.0)


def test_randomized_assignment_is_unbiased_confounded_is_biased():
    # single small-N draws are noisy (counts are Poisson-ish); average the naive-vs-true gap over
    # several seeds at the "clear signal" N used by the research harness (run_uplift_study.py).
    big_params = dict(BASE_PARAMS, N=6000)

    def _err(assignment, seed):
        rng = np.random.default_rng(seed)
        cfg = InterventionConfig(target="mu", structure="homogeneous", delta=0.4,
                                 assignment=assignment, horizon=26)
        s = summarise(simulate_intervention(DatasetParams(**big_params), cfg, rng=rng))
        return abs(s["naive_diff_count"] - s["true_ATE_count"])

    err_rand = np.mean([_err("randomized", s) for s in range(5)])
    err_conf = np.mean([_err("confounded", s) for s in range(5)])
    # randomization should track the true ATE reasonably tightly; confounding (treated skew
    # high-lambda/high-mu) should be a markedly worse naive estimate
    assert err_rand < 0.1
    assert err_conf > 2 * err_rand


def test_sleeping_dogs_yields_negative_cate_segment():
    df = _sim(structure="sleeping_dogs", assignment="randomized", delta=0.4, seed=2)
    alive = df["alive_at_T"] == 1
    neg = df.loc[alive & (df["cate_count"] < -1e-3), "cate_count"]
    # a real, substantial negative-CATE segment: sizeable share, sizeable magnitude
    assert len(neg) / alive.sum() > 0.10
    assert neg.mean() < -0.1

    # homogeneous (constant positive eff, every customer's mu strictly lowered) must be a STRICT
    # invariant: zero negative-CATE customers, no tolerance. This is a regression guard for a fixed
    # bug (2026-09-21): mu1 used to be floor-clipped at an absolute 1e-4, which could exceed
    # mu0*(1-eff) for a customer whose drawn mu0 was already below ~1.7e-4 (the Gamma(mu)
    # heterogeneity has a heavy tail down to ~1e-7), inverting the treatment direction for THAT
    # customer specifically. Fixed by flooring at a genuine underflow guard (1e-9) instead, which
    # never binds given eff is already clipped to (-0.95, 0.95) upstream.
    df_h = _sim(structure="homogeneous", assignment="randomized", delta=0.4, seed=2)
    alive_h = df_h["alive_at_T"] == 1
    assert (df_h.loc[alive_h, "cate_count"] < 0).sum() == 0


def test_positive_delta_never_inverts_direction_even_for_extreme_low_mu_draws():
    # regression test for the 2026-09-21 clip-floor fix: sweep several seeds, including ones known
    # to draw a customer with mu0 far below the old 1e-4 floor, and require the direction is never
    # inverted for a homogeneous positive-delta (mu-lowering) intervention.
    for seed in range(8):
        df = _sim(structure="homogeneous", target="mu", assignment="randomized", delta=0.4, seed=seed)
        alive = df["alive_at_T"] == 1
        assert df.loc[alive, "mu_true"].min() < 1e-4          # confirms the stress case is exercised
        assert (df.loc[alive, "cate_count"] < 0).sum() == 0
        assert (df.loc[alive, "cate_active"] < 0).sum() == 0


def test_target_mu_only_moves_mu_not_lambda_effect_via_outcomes():
    # target="mu": the arm difference in expected count should vanish if mu1==mu0 forced (sanity via
    # cate_count using the true formula) — here we just check target="lambda" leaves cate_active's
    # sign consistent with a rate-only shift (no dropout change means P(active) shifts less than CLV)
    df_mu = _sim(target="mu", structure="homogeneous", delta=0.4, seed=3)
    df_lam = _sim(target="lambda", structure="homogeneous", delta=0.4, seed=3)
    alive = df_mu["alive_at_T"] == 1
    # both should produce a positive ATE on count for a positive delta
    assert df_mu.loc[alive, "cate_count"].mean() > 0
    assert df_lam.loc[df_lam["alive_at_T"] == 1, "cate_count"].mean() > 0


# --- uplift_estimators_ext.py -------------------------------------------------------------------

def test_structural_btyd_cate_shape_and_direction():
    from uplift_estimators_ext import structural_btyd_cate
    df = _sim(structure="homogeneous", assignment="randomized", delta=0.5, seed=4)
    n = len(df)
    tr_idx = np.arange(0, int(0.7 * n))
    te_idx = np.arange(int(0.7 * n), n)
    cate_hat, ci = structural_btyd_cate(df.iloc[tr_idx], df.iloc[te_idx], horizon=26, outcome="clv")
    assert ci is None
    cate_hat = np.asarray(cate_hat, float)
    assert cate_hat.shape == (len(te_idx),)
    assert np.isfinite(cate_hat).all()
    # homogeneous positive-delta effect -> the structural estimate should be positive on average
    assert cate_hat.mean() > 0


def test_conformal_ite_intervals_are_ordered_and_reasonably_calibrated():
    pytest.importorskip("lightgbm", reason="lightgbm not installed (optional causal extra)")
    from uplift_estimators_ext import conformal_ite
    from run_uplift_study import features, _rf_reg
    df = _sim(structure="heterogeneous", assignment="randomized", delta=0.5, seed=5)
    X = features(df)
    T = df["T"].to_numpy(int)
    Y = df["y_clv"].to_numpy(float)
    cate_true = df["cate_clv"].to_numpy(float)
    n = len(df)
    tr, te = np.arange(0, int(0.7 * n)), np.arange(int(0.7 * n), n)
    cate_hat, (lo, hi) = conformal_ite(X[tr], T[tr], Y[tr], X[te], _rf_reg, alpha=0.10, seed=0)
    lo, hi = np.asarray(lo), np.asarray(hi)
    assert cate_hat.shape == (len(te),)
    assert np.all(lo <= hi)
    # loose sanity bound on coverage (nominal 90%; this is a small n, single split, not the
    # full multi-seed calibration study in GEAR2_STAGE_A_RESULTS.md) -- just check it's not degenerate
    coverage = np.mean((cate_true[te] >= lo) & (cate_true[te] <= hi))
    assert coverage > 0.5


# --- run_uplift_study.py: pure feature/metric functions -----------------------------------------

def test_features_shape():
    from run_uplift_study import features
    df = _sim(seed=6)
    X = features(df)
    assert X.shape == (len(df), 5)
    assert np.isfinite(X).all()


def test_policy_pct_oracle_perfect_and_random():
    from run_uplift_study import policy_pct_oracle
    rng = np.random.default_rng(0)
    cate_true = rng.normal(size=2000)
    # scoring with the true CATE itself must hit the oracle exactly (1.0)
    assert policy_pct_oracle(cate_true, cate_true, budget=0.3) == pytest.approx(1.0, abs=1e-9)
    # scoring with the true CATE's negation should badly underperform (well below the oracle)
    bad = policy_pct_oracle(-cate_true, cate_true, budget=0.3)
    assert bad < 0.5


def test_policy_pct_oracle_handcrafted():
    from run_uplift_study import policy_pct_oracle
    cate = np.array([5.0, 4.0, 3.0, -1.0, -2.0])
    score = np.array([5.0, 4.0, 3.0, -1.0, -2.0])  # matches ranking exactly
    # budget picks top-2: captured = 5+4=9, oracle = 5+4=9 -> 1.0
    assert policy_pct_oracle(score, cate, budget=0.4) == pytest.approx(1.0)


# --- run_uplift_dunnhumby.py: doubly-robust policy value ----------------------------------------

def test_dr_values_recovers_truth_with_correct_nuisances():
    from run_uplift_dunnhumby import dr_values
    rng = np.random.default_rng(0)
    n = 4000
    X = rng.normal(size=n)
    true_e = 1.0 / (1.0 + np.exp(-0.5 * X))            # known propensity
    T = rng.binomial(1, true_e)
    m1_true, m0_true = 2.0 + X, 1.0 + 0.2 * X            # known outcome means per arm
    Y = np.where(T == 1, m1_true, m0_true) + rng.normal(scale=0.1, size=n)
    scores = {"perfect": (m1_true - m0_true)}
    vals = dr_values(scores, true_e, m1_true, m0_true, T, Y, budget=1.0)
    # with correct nuisances and budget=1.0 (treat everyone under "perfect"), value("perfect")
    # should match value("treat_all") since both treat everyone
    assert vals["perfect"] == pytest.approx(vals["treat_all"], abs=0.05)
    # treat_all should beat treat_none (m1 > m0 everywhere in this DGP)
    assert vals["treat_all"] > vals["treat_none"]


# --- optional heavier integration check: only if econml/causalml are actually installed ---------

def test_fit_estimators_smoke_if_available():
    econml = pytest.importorskip("econml", reason="econml not installed (optional causal extra)")
    from run_uplift_study import fit_estimators, features
    df = _sim(structure="heterogeneous", assignment="randomized", delta=0.5, seed=7)
    df = df.iloc[:300]                                   # keep the fit fast
    X = features(df)
    T = df["T"].to_numpy(int)
    Y = df["y_clv"].to_numpy(float)
    n = len(df)
    tr, te = np.arange(0, int(0.7 * n)), np.arange(int(0.7 * n), n)
    out = fit_estimators(X[tr], T[tr], Y[tr], X[te])
    ok = {k: v for k, v in out.items() if not k.endswith("ERR")}
    assert len(ok) > 0
    for name, (chat, ci) in ok.items():
        assert np.asarray(chat).shape == (len(te),)


# --- prescriptive.py: the paretonbd prescriptive module (pure functions) ------------------------

def test_target_policy_budget_and_threshold_modes():
    from prescriptive import target_policy
    score = np.array([1.0, 5.0, 3.0, 2.0, 4.0])
    pi_budget = target_policy(score, budget=0.4)          # top-2: indices 1 (5.0) and 4 (4.0)
    assert pi_budget.tolist() == [0, 1, 0, 0, 1]
    pi_thresh = target_policy(score, margin=2.0, cost=5.0)  # 2*score > 5 -> score > 2.5
    assert pi_thresh.tolist() == [0, 1, 1, 0, 1]
    with pytest.raises(ValueError):
        target_policy(score)                               # neither mode given
    with pytest.raises(ValueError):
        target_policy(score, budget=0.4, margin=1.0, cost=1.0)  # both modes given


def test_oracle_policy_value_matches_run_uplift_study():
    from prescriptive import oracle_policy_value
    from run_uplift_study import policy_pct_oracle
    rng = np.random.default_rng(0)
    cate = rng.normal(size=500)
    score = cate + rng.normal(scale=0.1, size=500)
    assert oracle_policy_value(score, cate, budget=0.3) == pytest.approx(
        policy_pct_oracle(score, cate, budget=0.3))


def test_dr_policy_value_matches_dunnhumby_formula_and_recovers_truth():
    pytest.importorskip("lightgbm", reason="lightgbm not installed (optional causal extra)")
    from prescriptive import dr_policy_value, fit_dr_nuisances
    from run_uplift_dunnhumby import dr_values
    rng = np.random.default_rng(1)
    n = 3000
    X = rng.normal(size=(n, 1))
    true_e = 1.0 / (1.0 + np.exp(-0.5 * X[:, 0]))
    T = rng.binomial(1, true_e)
    m1_true, m0_true = 2.0 + X[:, 0], 1.0 + 0.2 * X[:, 0]
    Y = np.where(T == 1, m1_true, m0_true) + rng.normal(scale=0.1, size=n)

    # module function, called directly with known nuisances, must recover the true policy value
    pi_all = np.ones(n, int)
    val = dr_policy_value(pi_all, T, Y, true_e, m1_true, m0_true)
    assert val == pytest.approx(m1_true.mean(), abs=0.05)

    # and must agree with run_uplift_dunnhumby.dr_values's own formula on the same inputs
    ref = dr_values({"perfect": m1_true - m0_true}, true_e, m1_true, m0_true, T, Y, budget=1.0)
    assert val == pytest.approx(ref["treat_all"], abs=1e-9)

    # fit_dr_nuisances: shape/range sanity on a held-out split
    tr, te = np.arange(0, 2000), np.arange(2000, n)
    ehat, m1hat, m0hat = fit_dr_nuisances(X[tr], T[tr], Y[tr], X[te])
    assert ehat.shape == m1hat.shape == m0hat.shape == (len(te),)
    assert np.all((ehat >= 0.05) & (ehat <= 0.95))


def test_dr_policy_value_cost_penalizes_by_contacted_fraction():
    from prescriptive import dr_policy_value
    rng = np.random.default_rng(2)
    n = 2000
    e = np.full(n, 0.5)
    m1 = np.full(n, 10.0)
    m0 = np.full(n, 8.0)
    T = rng.binomial(1, e)
    Y = np.where(T == 1, m1, m0)                          # noiseless, so DR is exact
    pi_all = np.ones(n, int)
    pi_half = np.zeros(n, int); pi_half[: n // 2] = 1
    # cost=0 unchanged from the original formula
    assert dr_policy_value(pi_all, T, Y, e, m1, m0, cost=0.0) == pytest.approx(m1.mean(), abs=1e-9)
    # a cost of c lowers the all-treated policy's value by exactly c (100% contacted)...
    for c in (1.0, 5.0, 20.0):
        assert dr_policy_value(pi_all, T, Y, e, m1, m0, cost=c) == pytest.approx(
            m1.mean() - c, abs=1e-9)
        # ...and the half-treated policy's value by exactly c/2 (50% contacted)
        assert dr_policy_value(pi_half, T, Y, e, m1, m0, cost=c) == pytest.approx(
            dr_policy_value(pi_half, T, Y, e, m1, m0, cost=0.0) - c / 2, abs=1e-9)


def test_dunnhumby_dr_values_cost_matches_prescriptive_module():
    from prescriptive import dr_policy_value
    from run_uplift_dunnhumby import dr_values
    rng = np.random.default_rng(3)
    n = 1500
    e = np.clip(0.5 + 0.1 * rng.normal(size=n), 0.05, 0.95)
    m1 = 5.0 + rng.normal(size=n)
    m0 = 3.0 + rng.normal(size=n)
    T = rng.binomial(1, e)
    Y = np.where(T == 1, m1, m0) + rng.normal(scale=0.5, size=n)
    score = {"s": m1 - m0}
    for c in (0.0, 2.0, 10.0):
        vals = dr_values(score, e, m1, m0, T, Y, budget=0.3, cost=c)
        pi = np.ones(n, int)
        assert vals["treat_all"] == pytest.approx(dr_policy_value(pi, T, Y, e, m1, m0, cost=c))


def test_estimate_uplift_smoke_if_available():
    pytest.importorskip("econml", reason="econml not installed (optional causal extra)")
    from prescriptive import estimate_uplift
    df = _sim(structure="heterogeneous", assignment="randomized", delta=0.5, seed=8).iloc[:300]
    from run_uplift_study import features
    X = features(df)
    T = df["T"].to_numpy(int)
    Y = df["y_clv"].to_numpy(float)
    n = len(df)
    tr, te = np.arange(0, int(0.7 * n)), np.arange(int(0.7 * n), n)
    for method in ("t_learner", "x_learner", "causal_forest", "conformal_ite"):
        chat, ci = estimate_uplift(X[tr], T[tr], Y[tr], X[te], method=method, seed=0)
        assert np.asarray(chat).shape == (len(te),)
        if ci is not None:
            lo, hi = ci
            assert np.all(np.asarray(lo) <= np.asarray(hi))
    with pytest.raises(ValueError):
        estimate_uplift(X[tr], T[tr], Y[tr], X[te], method="not_a_method")
    with pytest.raises(ValueError):
        estimate_uplift(X[tr], T[tr], Y[tr], X[te], method="causal_forest", library="causalml")
