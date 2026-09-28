"""Numerical smoke tests for the Phase 2 modules (ML benchmark, conformal, amortized, CLV,
churn, BG/NBD). Kept fast: small synthetic inputs, MLE not MCMC, tiny neural nets."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulate import DatasetParams, simulate_dataset


def _small_supervised(seed=0, n=200, k=5):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = rng.poisson(np.exp(0.3 * X[:, 0]))            # non-negative counts
    return X, y.astype(float)


def test_rfm_and_forecasters_shapes_and_nonneg():
    from ml_benchmark import (rfm_features, poisson_gbm_forecast,
                              hurdle_gbm_forecast, quantile_gbm_forecast)
    df = simulate_dataset(DatasetParams(0.2, 1.2, 0.1, 1.0, N=150, T=52.0),
                          rng=np.random.default_rng(1))
    feats = rfm_features(df)
    assert feats.shape == (150, 5)

    Xtr, ytr = _small_supervised(0, 200)
    Xte, _ = _small_supervised(1, 60)
    for fn in (poisson_gbm_forecast, hurdle_gbm_forecast, quantile_gbm_forecast):
        pred = fn(Xtr, ytr, Xte, n_draws=100, seed=0)
        assert pred.shape == (100, 60)
        assert np.all(pred >= 0) and np.all(pred == np.round(pred))


def test_churn_ece_and_scores():
    from churn import ece, churn_scores
    rng = np.random.default_rng(0)
    o = (rng.uniform(size=2000) < 0.3).astype(float)
    # a forecast equal to the true rate everywhere is calibrated -> small ECE
    assert ece(np.full(2000, o.mean()), o) < 0.05
    # a forecast that equals the outcome is perfectly calibrated and has Brier 0
    s = churn_scores(o, o)
    assert s["brier"] == pytest.approx(0.0, abs=1e-9)
    assert set(s) == {"brier", "ece", "p_active_mean", "active_rate"}


def test_conformal_recalibration_shape_and_identity():
    from conformal import recalibrate_samples
    rng = np.random.default_rng(0)
    pred_cal = rng.poisson(1.5, size=(200, 300))
    y_cal = rng.poisson(1.5, size=300).astype(float)
    pred_test = rng.poisson(1.5, size=(200, 120))
    out = recalibrate_samples(pred_cal, y_cal, pred_test, n_out=150, seed=0)
    assert out.shape == (150, 120)
    assert np.all(out >= 0)


def test_amortized_features():
    from amortized import cohort_features, FEATURE_NAMES
    df = simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=120, T=48.0),
                          rng=np.random.default_rng(2))
    f = cohort_features(df)
    assert f.shape == (len(FEATURE_NAMES),)
    assert np.all(np.isfinite(f))


def test_clv_features_and_ziln():
    pytest.importorskip("torch", reason="torch not installed (optional deep-ZILN dependency)")
    from clv_benchmark import clv_features, ziln_clv_predict
    rng = np.random.default_rng(0)
    df = simulate_dataset(DatasetParams(0.2, 1.2, 0.1, 1.0, N=150, T=52.0), rng=rng)
    df["m_bar"] = np.where(df["x"] > 0, rng.uniform(5, 50, len(df)), 0.0)
    X = clv_features(df)
    assert X.shape == (150, 8)

    Xtr, cnt = _small_supervised(3, 250)
    spend = cnt * rng.uniform(5, 20, len(cnt))                # zero-inflated CLV target
    Xte, _ = _small_supervised(4, 80)
    pred = ziln_clv_predict(Xtr, spend, Xte, n_draws=100, seed=0, epochs=100)
    assert pred.shape == (100, 80)
    assert np.all(pred >= 0)


def test_bgnbd_fit_and_predict():
    from estimate_bgnbd import fit_bgnbd, bgnbd_predict
    df = simulate_dataset(DatasetParams(0.15, 1.2, 0.08, 1.0, N=600, T=52.0),
                          rng=np.random.default_rng(5))
    bg = fit_bgnbd(df)
    assert bg.r > 0 and bg.alpha > 0 and bg.a > 0 and bg.b > 0
    assert 0.5 * 0.15 < bg.r / bg.alpha < 1.5 * 0.15          # recovers E(lambda)
    pred = bgnbd_predict(df, bg, 26, n_draws=100, seed=1)
    assert pred.shape == (100, 600)
    assert np.all(pred >= 0) and np.all(pred == np.round(pred))


# ------------------------- Tier-1 gap-closure modules -------------------------- #

def test_conformal_ml_shapes_and_repair(seed=0):
    """M3: conformal wrapper on the ML forecasters returns raw+recal scores for every method,
    and recalibration does not worsen an already-miscalibrated PoissonGBM on simulated data."""
    from conformal import compare_conformal_ml
    df = simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=700, T=52.0),
                          rng=np.random.default_rng(1))
    res = compare_conformal_ml(df, 26, ml_methods=("PoissonGBM",), seed=seed,
                               mcmc_draws=600, mcmc_burn=150, mcmc_thin=3)
    for tag in ("BTYD_raw", "BTYD_recal", "PoissonGBM_raw", "PoissonGBM_recal"):
        assert (tag, "all") in res
        assert res[(tag, "all")]["pit_ks"] >= 0.0
    # recal must not blow up coverage/PIT (repair or leave alone, never destroy)
    assert res[("PoissonGBM_recal", "all")]["pit_ks"] <= res[("PoissonGBM_raw", "all")]["pit_ks"] + 0.05


def test_noise_floor_ordering():
    """T3: total(est) >= counting-noise floor(true_indiv); the floor is strictly positive."""
    from run_noise_floor import one
    r = one(N=600, seed=701)
    assert r["CRPS_true_indiv"] > 0
    assert r["CRPS_est"] >= r["CRPS_true_indiv"] - 1e-6
    assert r["nMAE_est"] >= r["nMAE_true_indiv"] - 1e-6


def test_timevarying_promo_covariate():
    """G2: the promo simulator yields the designed 25% calendar and a valid covariate column."""
    from covariate_timevarying import simulate_promo_cohort, promo_active
    ts = np.linspace(0, 96, 9600)
    assert abs(promo_active(ts).mean() - 0.25) < 0.02          # 2w promo / 8w cycle
    df = simulate_promo_cohort(DatasetParams(0.15, 1.3, 0.08, 1.2, N=200, T=52.0), 26, seed=1)
    assert {"x", "x_star_26", "promo_fc", "e_resp"} <= set(df.columns)
    assert (df["promo_fc"] >= 0).all() and df["x_star_26"].sum() > 0


def test_laplace_cov_pd_and_predict_shape():
    """E4: Laplace covariance is positive-definite; the predictive has the right shape + support."""
    from laplace import laplace_predict, laplace_cov
    from estimate import fit_mle
    df = simulate_dataset(DatasetParams(0.15, 1.2, 0.08, 1.0, N=500, T=52.0),
                          rng=np.random.default_rng(3))
    mle = fit_mle(df)
    Sigma = laplace_cov(df, mle["logparams"])
    assert Sigma.shape == (4, 4)
    assert np.allclose(Sigma, Sigma.T, atol=1e-8)
    assert np.all(np.linalg.eigvalsh(Sigma) > 0)              # PD by eigen-repair
    pred, _ = laplace_predict(df, 26, n_draws=150, seed=1)
    assert pred.shape[1] == len(df)
    assert np.all(pred >= 0) and np.all(pred == np.round(pred))


# ------------------------------ Tier-2 modules -------------------------------- #

def test_pareto_frontier_dominance():
    """V3: the frontier keeps only points not dominated on both cost and accuracy."""
    from run_cost_benchmark import pareto_frontier
    costs = np.array([0.0, 1.0, 2.0, 3.0])
    accs = np.array([1.0, 0.5, 0.6, 0.4])           # idx2 (2.0,0.6) dominated by idx1 (1.0,0.5)
    front = pareto_frontier(costs, accs)
    assert front == {0, 1, 3}
    assert 2 not in front


def test_profit_and_topa_capture():
    """V2: profit rewards contacting realised buyers; a perfect ranker captures 100% of oracle."""
    from run_profit_study import profit_for, topa_capture
    y = np.array([0.0, 0.0, 3.0, 1.0])
    perfect = y.copy()                               # a ranker that equals the truth
    # contact-all at c=1.0: profit = sum(M*y - c) = (0-1)+(0-1)+(3-1)+(1-1) = 0
    assert profit_for(np.ones_like(y), y, 1.0, 1.0) == pytest.approx(0.0)
    # a good ranker only contacts the true buyers -> non-negative
    assert profit_for(perfect, y, 1.0, 1.0) >= profit_for(np.ones_like(y), y, 1.0, 1.0)
    assert topa_capture(perfect, y, 0.5) == pytest.approx(1.0)   # top-2 by truth = top-2 realised


def test_discount_factor_limits():
    """G5: per-customer discount -> 1 as rate->0, and is in (0,1) for a positive rate."""
    from run_clv_discount import discount_factor
    L = np.array([0.0, 13.0, 26.0, 52.0])
    assert np.allclose(discount_factor(L, 0.0), 1.0)
    D = discount_factor(L, 0.02)
    assert D[0] == pytest.approx(1.0)                # L=0 -> factor 1 (no active window)
    assert np.all((D > 0) & (D <= 1.0)) and D[3] < D[1]  # longer overlap -> more discounting


def test_sens_prec_bounds():
    """F4: sensitivity/precision helper is correct on a hand-checked case."""
    from run_active_def_study import _sens_prec
    p = np.array([0.9, 0.8, 0.2, 0.1])
    truth = np.array([True, False, True, False])
    sens, prec = _sens_prec(p, truth, thr=0.5)      # predict active = [T,T,F,F]
    assert sens == pytest.approx(0.5)               # 1 of 2 true-actives caught
    assert prec == pytest.approx(0.5)               # 1 of 2 predicted-actives correct


def test_mcmc_accepts_custom_prior():
    """E5: the Gibbs sampler runs under an overridden hyper-prior and returns valid draws."""
    from estimate import fit_mcmc
    df = simulate_dataset(DatasetParams(0.15, 1.2, 0.08, 1.0, N=250, T=52.0),
                          rng=np.random.default_rng(4))
    mc = fit_mcmc(df, n_draws=200, burn_in=60, thin=2, seed=1,
                  hyper=dict(ar=4.0, br=4.0, as_=4.0, bs=4.0))
    assert mc.pop_draws.shape[1] == 4
    assert np.all(mc.pop_draws > 0)


# ------------------------------ Tier-3 modules -------------------------------- #

def test_hmc_sampler_runs_and_augments():
    """E1: HMC returns valid log-param draws with non-zero acceptance; augmentation has right shape."""
    from hmc import hmc_sample, augmented_draws_from_theta
    df = simulate_dataset(DatasetParams(0.15, 1.2, 0.08, 1.0, N=300, T=52.0),
                          rng=np.random.default_rng(4))
    draws, acc = hmc_sample(df, n_samples=25, warmup=25, seed=1)
    assert draws.shape == (25, 4) and 0.0 < acc <= 1.0
    lam, mu, tau = augmented_draws_from_theta(df, draws, n_draws=50, burn_in=30, seed=2)
    assert lam.shape[1] == len(df) and np.all(lam > 0)


def test_dependent_cohort_recovers_correlation():
    """G4: the dependent DGP produces the requested sign of log-lambda/log-mu correlation."""
    from run_dependence_stress import simulate_dependent_cohort
    b = dict(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, N=1500, T=52.0)
    neg = simulate_dependent_cohort(-0.6, 1, **b).attrs["true_corr"]
    pos = simulate_dependent_cohort(0.6, 1, **b).attrs["true_corr"]
    assert neg < -0.3 and pos > 0.3


def test_seasonal_multiplier_and_cohort():
    """D2: the seasonal multiplier is non-negative and averages to 1; the cohort simulates."""
    from run_seasonality_stress import seasonal_mult, simulate_seasonal_cohort
    t = np.linspace(0, 104, 5000)
    assert np.all(seasonal_mult(t, 1.0) >= 0) and abs(seasonal_mult(t, 1.0).mean() - 1.0) < 0.02
    df = simulate_seasonal_cohort(0.6, 1, E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2,
                                  N=200, T=52.0)
    assert df["x_star_26"].sum() > 0 and {"x", "T_cal"} <= set(df.columns)


def test_segment_tenure_bounds():
    """F3: retention is a probability and expected tenure >= 1 period."""
    from run_rolling_study import segment_tenure
    from empirical import load_cdnow
    r = segment_tenure("CDNow", load_cdnow(), window_weeks=13, n_windows=6)
    assert 0.0 <= r["retention"] <= 1.0 and r["exp_tenure_periods"] >= 1.0


def test_censoring_keeps_acquisitions():
    """D3: censoring drops repeat events but never a customer's first (acquisition) event."""
    from run_censoring_stress import censor_repeat_cal
    from empirical import load_cdnow
    e = load_cdnow()
    ec = censor_repeat_cal(e, 39, 0.30, 1)
    assert len(ec) < len(e)
    assert set(e["cust"].unique()) == set(ec["cust"].unique())   # every customer still present


def test_aggregation_nmae_shrinks_with_k():
    """F2: normalised group-total error falls as the aggregation group grows."""
    from run_aggregation_study import grouped_nmae
    rng = np.random.default_rng(0)
    y = rng.poisson(0.5, size=800).astype(float)
    pm = np.full(800, 0.5)
    e1 = grouped_nmae(pm, y, 1, np.random.default_rng(1))
    e50 = grouped_nmae(pm, y, 50, np.random.default_rng(1))
    assert e50 < e1


def test_ml_hazard_timing_shape_and_support():
    """M2: the discrete-time hazard forecaster returns wait samples within the horizon or inf."""
    from run_ml_timing_study import ml_hazard_timing
    rng = np.random.default_rng(2)
    Xtr = rng.normal(size=(400, 5)); w = rng.exponential(8, 400); w[rng.uniform(size=400) < 0.4] = np.inf
    Xte = rng.normal(size=(80, 5))
    out = ml_hazard_timing(Xtr, w, Xte, 26, n_draws=100, seed=0)
    assert out.shape == (100, 80)
    fin = out[np.isfinite(out)]
    assert np.all((fin > 0) & (fin <= 26))


def test_tost_equivalence_logic():
    """TOST: near-identical samples are declared equivalent; a large offset is not."""
    from tost import tost_diff
    rng = np.random.default_rng(0)
    tight = rng.normal(0.0, 0.01, size=60)                # centred, tiny spread -> within +/-0.05
    r_eq = tost_diff(tight, margin=0.05)
    assert r_eq["equivalent"] and r_eq["p_tost"] < 0.05
    offset = rng.normal(0.2, 0.01, size=60)               # mean 0.2, well outside +/-0.05
    r_ne = tost_diff(offset, margin=0.05)
    assert not r_ne["equivalent"]
    assert r_eq["ci_lo"] < r_eq["mean"] < r_eq["ci_hi"]   # 90% CI brackets the mean


def test_ml_tuning_forecasters_configurable():
    """Objection-9 study: the config-parameterised GBM forecasters return valid predictive samples."""
    from run_ml_tuning import poisson_gbm, quantile_gbm, CONFIGS
    Xtr, ytr = _small_supervised(0, 300)
    Xte, _ = _small_supervised(1, 90)
    for fn in (poisson_gbm, quantile_gbm):
        pred = fn(Xtr, ytr, Xte, CONFIGS["default"], n_draws=100, seed=0)
        assert pred.shape == (100, 90)
        assert np.all(pred >= 0) and np.all(pred == np.round(pred))


def test_topa_metrics():
    """Top-A%: a perfect ranker scores hit=capture=1; a reversed ranker captures little."""
    from run_topa_study import topa_metrics
    y = np.array([5.0, 4.0, 3.0, 2.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    hit, cap = topa_metrics(y.copy(), y, 0.2)             # predict = truth -> top-2 exact
    assert hit == 1.0 and cap == 1.0
    hit_rev, cap_rev = topa_metrics(-y, y, 0.2)           # reversed ranking -> picks the zeros
    assert hit_rev < 1.0 and cap_rev < hit


def test_seasonal_intensity():
    """Real-seasonality helper: intensity = forecast-window volume / calibration-window volume."""
    from run_seasonality_real import seasonal_intensity
    vol = np.concatenate([np.ones(10), np.full(5, 3.0)])   # calib flat=1, forecast window busy=3
    assert seasonal_intensity(vol, cut_wk=10, horizon=5) == pytest.approx(3.0)
    assert seasonal_intensity(vol, cut_wk=5, horizon=5) == pytest.approx(1.0)   # quiet window


def test_tenure_from_counts():
    """Segment-tenure geometric estimator: perfect retention -> 1.0; full rotation -> tenure 1."""
    from run_rolling_study import _tenure_from_counts
    stable = np.tile(np.array([[5.], [4.], [3.], [2.], [1.]]), (1, 4))   # same top-2 every window
    ret, _ = _tenure_from_counts(stable, 2)
    assert ret == 1.0
    rot = np.zeros((6, 3))
    rot[[0, 1], 0] = [9, 8]; rot[[2, 3], 1] = [9, 8]; rot[[4, 5], 2] = [9, 8]  # top-2 fully rotates
    ret2, ten2 = _tenure_from_counts(rot, 2)
    assert ret2 == 0.0 and ten2 == pytest.approx(1.0)


def test_cap_inf_timing():
    """Timing-stack helper: infinities in the wait samples are replaced by the cap, finites kept."""
    from run_timing_stack import _cap_inf
    w = np.array([[1.0, np.inf], [np.inf, 3.0]])
    out = _cap_inf(w, 50.0)
    assert np.all(np.isfinite(out))
    assert out[0, 1] == 50.0 and out[1, 0] == 50.0 and out[0, 0] == 1.0
