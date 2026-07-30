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
