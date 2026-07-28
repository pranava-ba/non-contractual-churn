"""
Extension E: Gamma-Gamma Monetary & Probabilistic CLV Forecast Module.

Combines purchase-count forecasts x* with the Gamma-Gamma spend model
(Fader & Hardie 2005) to compute full posterior-predictive distributions of
future customer value (CLV) over forecast horizon T*.

Model:
  - Customer i's transaction values m_{i,j} ~ Gamma(p, p / nu_i) with mean nu_i.
  - Heterogeneity in mean spend: nu_i ~ Gamma(q, v).
  - Given observed average spend bar{m}_i across x_i repeat transactions,
    the posterior distribution of nu_i is Gamma(p*x_i + q, p*x_i*bar{m}_i + v).

Calculates probabilistic CLV CRPS, coverage, and sharpness.
"""

from __future__ import annotations

import numpy as np
from scipy import optimize
from scipy.special import gammaln


def fit_gamma_gamma(x, m_obs):
    """Fit Gamma-Gamma spend model parameters (p, q, v) via MLE.
    
    x: (N_repeat,) count of repeat transactions (x > 0).
    m_obs: (N_repeat,) average observed spend per repeat transaction."""
    valid = (x > 0) & (m_obs > 0)
    x_val = x[valid]
    m_val = m_obs[valid]
    
    def neg_loglik(params):
        p, q, v = np.exp(params)
        ll = (gammaln(p * x_val + q) - gammaln(p * x_val) - gammaln(q)
              + q * np.log(v) + (p * x_val - 1) * np.log(m_val)
              + (p * x_val) * np.log(p * x_val)
              - (p * x_val + q) * np.log(p * x_val * m_val + v))
        return -np.sum(ll)
    
    res = optimize.minimize(neg_loglik, x0=np.log([2.0, 2.0, 10.0]), method="Nelder-Mead")
    p, q, v = np.exp(res.x)
    return {"p": p, "q": q, "v": v, "expected_margin": v / (q - 1.0) if q > 1 else np.nan}


def sample_posterior_nu(x, m_obs, p, q, v, n_draws=500, seed=0):
    """Draw posterior mean transaction value nu_i per customer.
    
    Returns: (n_draws, N) matrix of drawn transaction averages nu_i."""
    rng = np.random.default_rng(seed)
    N = len(x)
    shape = np.where(x > 0, p * x + q, q)
    rate = np.where(x > 0, p * x * m_obs + v, v)
    
    # Gamma(shape, rate) draws
    nu_draws = rng.gamma(shape=shape[None, :], scale=1.0 / rate[None, :], size=(n_draws, N))
    return nu_draws


def predict_clv_distribution(pred_x_star, nu_draws, discount_rate=0.0):
    """Form probabilistic future spend distribution: CLV_i = x^*_i * nu_i.
    
    pred_x_star: (n_draws, N) sampled repeat purchase counts.
    nu_draws: (n_draws, N) sampled average spend per purchase.
    discount_rate: optional continuous discount rate over T*."""
    dfactor = np.exp(-discount_rate)
    clv_samples = pred_x_star * nu_draws * dfactor
    return clv_samples


def score_clv_forecast(pred_clv, true_clv, rng):
    """Evaluate probabilistic CLV forecasts using CRPS, coverage, and point metrics.
    
    pred_clv: (n_draws, N) predictive spend samples.
    true_clv: (N,) actual realised spend in forecast period."""
    from score import crps_samples, coverage, randomized_pit
    
    point = np.median(pred_clv, axis=0)
    denom = max(true_clv.mean(), 1e-9)
    err = point - true_clv
    cov = coverage(pred_clv, true_clv)
    
    return {
        "clv_nMAE": float(np.abs(err).mean() / denom),
        "clv_nRMSE": float(np.sqrt((err ** 2).mean()) / denom),
        "clv_CRPS": float(crps_samples(pred_clv, true_clv).mean()),
        "clv_cov50": float(cov[0.5]),
        "clv_cov95": float(cov[0.95]),
        "clv_sharpness": float(pred_clv.std(axis=0).mean())
    }
