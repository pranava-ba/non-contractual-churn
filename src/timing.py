"""
Extension B: Purchase Timing Forecast Module (t_{x+1}).

Simon (2025) identified next-purchase timing prediction as a primary failure of
plug-in estimation. This module computes full posterior-predictive distributions for
the wait time until the next purchase t_{x+1} for active customers under both the
classical Pareto/NBD model and the regularity-aware Pareto/GGG model.

While alive:
  - Pareto/NBD: inter-purchase times are Exp(lambda_i), memoryless. Given elapsed
    time since last purchase d_i = T_cal - t_x, remaining wait time is Exp(lambda_i).
  - Pareto/GGG: inter-purchase times are Gamma(shape=k, rate=k*lambda_i). Remaining
    wait time follows a left-truncated Gamma renewal distribution.

Evaluates timing forecasts using continuous CRPS and Median Absolute Error (MdAE).
"""

from __future__ import annotations

import numpy as np
from scipy.special import gammainc, gammaincc, gammaincinv


def sample_next_purchase_time_pnbd(lam, mu, tau, T_cal, n_samples_per_draw=1, seed=0):
    """Sample wait time until next purchase (or infinity if churned before next purchase).
    
    lam, mu, tau: (n_draws, N) individual parameter draws.
    Returns: (n_draws, N) simulated wait times beyond T_cal. If customer churns
    before next purchase, wait time is np.inf."""
    rng = np.random.default_rng(seed)
    n_draws, N = lam.shape
    
    # Next purchase time relative to T_cal
    wait_time = rng.exponential(scale=1.0 / lam)
    t_next = T_cal[None, :] + wait_time
    
    # Customer churns at tau
    churned = t_next > tau
    t_next_obs = np.where(churned, np.inf, wait_time)
    return t_next_obs


def sample_next_purchase_time_pggg(lam, mu, tau, k, T_cal, t_x, seed=0):
    """Sample wait time until next purchase for Pareto/GGG (Gamma renewal).
    
    k: common regularity parameter.
    Elapsed time since last purchase is d_i = T_cal - t_x.
    Remaining wait time is drawn from Gamma(k, k*lam) left-truncated at d_i."""
    rng = np.random.default_rng(seed)
    n_draws, N = lam.shape
    d = np.maximum(T_cal - t_x, 0.0) # elapsed age of current gap
    
    # Inverse CDF sampling for truncated Gamma renewal
    u = rng.uniform(size=(n_draws, N))
    u_lower = gammainc(k, k * lam * d[None, :])
    u_scaled = u_lower + u * (1.0 - u_lower)
    
    # Quantile of Gamma(k, 1)
    g_val = gammaincinv(k, np.clip(u_scaled, 1e-10, 1.0 - 1e-10))
    t_total_gap = g_val / (k * lam)
    wait_time = np.maximum(t_total_gap - d[None, :], 0.0)
    
    t_next = T_cal[None, :] + wait_time
    churned = t_next > tau
    return np.where(churned, np.inf, wait_time)


def score_timing_forecast(pred_wait, true_wait):
    """Score timing forecasts for customers who actually bought next.
    
    pred_wait: (n_draws, N_active) predicted wait times
    true_wait: (N_active,) observed wait times"""
    # Filter finite predictions
    valid_mask = np.isfinite(true_wait)
    if not valid_mask.any():
        return {"timing_MAE": np.nan, "timing_MdAE": np.nan, "timing_CRPS": np.nan}
    
    pw = pred_wait[:, valid_mask]
    tw = true_wait[valid_mask]
    
    # Cap infinite predictions (customer forecast to churn before buying) at 5x the
    # largest observed wait for numerical stability
    cap = max(tw.max() * 5.0, 100.0)
    pw_capped = np.where(np.isfinite(pw), pw, cap)
    
    med_pred = np.median(pw_capped, axis=0)
    abs_err = np.abs(med_pred - tw)
    
    # Sample CRPS
    J = pw_capped.shape[0]
    term1 = np.abs(pw_capped - tw[None, :]).mean(axis=0)
    ps = np.sort(pw_capped, axis=0)
    idx = np.arange(1, J + 1)[:, None]
    term2 = (2.0 / (J * J)) * ((2 * idx - J - 1) * ps).sum(axis=0)
    crps = (term1 - 0.5 * term2).mean()
    
    return {
        "timing_MAE": float(abs_err.mean()),
        "timing_MdAE": float(np.median(abs_err)),
        "timing_CRPS": float(crps)
    }
