import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timing import sample_next_purchase_time_pnbd, sample_next_purchase_time_pggg, score_timing_forecast
from clv import fit_gamma_gamma, sample_posterior_nu, predict_clv_distribution, score_clv_forecast


def test_timing_extension():
    lam = np.full((100, 20), 0.1)
    mu = np.full((100, 20), 0.05)
    tau = np.full((100, 20), 100.0)
    T_cal = np.full(20, 52.0)
    t_x = np.full(20, 40.0)
    
    pred_wait = sample_next_purchase_time_pnbd(lam, mu, tau, T_cal, seed=42)
    assert pred_wait.shape == (100, 20)
    
    pred_wait_ggg = sample_next_purchase_time_pggg(lam, mu, tau, k=2.0, T_cal=T_cal, t_x=t_x, seed=42)
    assert pred_wait_ggg.shape == (100, 20)
    
    true_wait = np.full(20, 10.0)
    scores = score_timing_forecast(pred_wait, true_wait)
    assert "timing_CRPS" in scores
    assert np.isfinite(scores["timing_CRPS"])


def test_clv_extension():
    rng = np.random.default_rng(100)
    x = np.array([2, 5, 0, 3, 10])
    m_obs = np.array([15.0, 25.0, 0.0, 10.0, 50.0])
    
    fit = fit_gamma_gamma(x, m_obs)
    assert fit["p"] > 0 and fit["q"] > 0
    
    nu_draws = sample_posterior_nu(x, m_obs, fit["p"], fit["q"], fit["v"], n_draws=50, seed=1)
    assert nu_draws.shape == (50, 5)
    
    pred_x = rng.poisson(lam=2.0, size=(50, 5))
    pred_clv = predict_clv_distribution(pred_x, nu_draws)
    assert pred_clv.shape == (50, 5)
    
    true_clv = np.array([30.0, 100.0, 0.0, 20.0, 400.0])
    scores = score_clv_forecast(pred_clv, true_clv, rng)
    assert "clv_CRPS" in scores
    assert "clv_cov95" in scores


def test_clv_posterior_spend_is_realistic():
    """The posterior mean spend must track observed spend (Inverse-Gamma posterior),
    not its reciprocal. Guards against sampling the mean from a Gamma, which returns
    values ~1/spend -- off by orders of magnitude and anti-correlated with the data."""
    x = np.array([2.0, 5.0, 3.0, 10.0, 6.0])
    m_obs = np.array([15.0, 25.0, 10.0, 50.0, 30.0])
    fit = fit_gamma_gamma(x, m_obs)

    nu = sample_posterior_nu(x, m_obs, fit["p"], fit["q"], fit["v"], n_draws=4000, seed=7)
    post_mean = nu.mean(axis=0)

    # every customer's posterior mean spend lies in a realistic band around the data
    assert np.all(post_mean > 5.0) and np.all(post_mean < 80.0)
    # shrinkage preserves ranking: the biggest spender has the biggest posterior mean
    assert np.argmax(post_mean) == np.argmax(m_obs)
    # positive correlation with observed spend (a reciprocal bug makes this negative)
    assert np.corrcoef(post_mean, m_obs)[0, 1] > 0.9
