"""
Probabilistic scoring of the future-purchase forecast — the core novelty (A+D).

Simon (2025) evaluates only POINT errors (nMAE/nRMSE/nMdAE) and never checks
whether the predictive intervals she credits to MCMC are actually calibrated.
Here we score the FULL predictive distribution of x* (future repeat purchases):

  - point:        nMAE, nRMSE, nMdAE   (replicated for a sanity cross-check)
  - proper score: CRPS (sample estimator)   -- lower is better
  - calibration:  central-interval coverage @ 50/80/95%, and (randomized) PIT
  - sharpness:    mean predictive std / interval width

Predictive distributions are produced by the SPP method (Simon 2025, App. 7.2).
Key identity: while a customer is alive, purchases are Poisson(lambda), so the
number in the forecast window (T, min(tau, T+T*)] is Poisson(lambda * L) with
L = max(0, min(tau, T+T*) - T).  This makes SPP exact and fully vectorised.

The SAME engine is fed either full posterior draws (MCMC) or individual draws
conditional on a FIXED population estimate (MLE plug-in / MLE bootstrap). The
gap in coverage between them isolates exactly the value of full Bayesian
uncertainty quantification -- the claim Simon makes but never measures.
"""

from __future__ import annotations

import numpy as np


# --------------------- predictive distribution (SPP) ----------------------- #
def spp_predict(lam, mu, tau, T_cal, T_star, rng):
    """Vectorised SPP predictive samples of x*.

    lam, mu, tau : (n_draws, N) individual draws;  T_cal : (N,).
    Returns (n_draws, N) integer predictive samples of future repeat purchases."""
    L = np.clip(np.minimum(tau, T_cal + T_star) - T_cal, 0.0, None)
    return rng.poisson(lam * L)


def conditional_individual_draws(df, r, alpha, s, beta, n_draws=500,
                                 burn_in=200, thin=2, seed=0):
    """Individual (lambda_i, mu_i, tau_i) draws conditional on FIXED population
    parameters (r, alpha, s, beta).  This is the MLE plug-in individual posterior:
    it carries individual + count uncertainty but NOT parameter uncertainty."""
    rng = np.random.default_rng(seed)
    x = df["x"].to_numpy(float); t_x = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float); n = len(x)
    tau = T + 1.0
    keep_l, keep_m, keep_t = [], [], []
    total = burn_in + n_draws * thin
    for it in range(total):
        lam = rng.gamma(shape=x + r, scale=1.0 / (alpha + np.minimum(tau, T)))
        mu = rng.gamma(shape=s + 1.0, scale=1.0 / (beta + tau))
        rate = lam + mu
        d = T - t_x
        ealive = np.exp(-rate * d)
        p_alive = ealive / (ealive + (mu / rate) * (1.0 - ealive))
        z = rng.uniform(size=n) < p_alive
        tau = np.empty(n)
        tau[z] = T[z] + rng.exponential(1.0 / mu[z])
        nz = ~z
        if nz.any():
            u = rng.uniform(size=nz.sum()); rr = rate[nz]
            inside = (1 - u) * np.exp(-rr * t_x[nz]) + u * np.exp(-rr * T[nz])
            tau[nz] = -np.log(inside) / rr
        if it >= burn_in and (it - burn_in) % thin == 0:
            keep_l.append(lam); keep_m.append(mu); keep_t.append(tau.copy())
    return np.array(keep_l), np.array(keep_m), np.array(keep_t)


# ------------------------------ scoring ------------------------------------ #
def crps_samples(pred, y):
    """Sample-based CRPS per observation. pred: (J, N) predictive draws,
    y: (N,) truth. CRPS = E|X-y| - 0.5 E|X-X'|  (lower is better)."""
    J = pred.shape[0]
    term1 = np.abs(pred - y[None, :]).mean(axis=0)
    # E|X - X'| via sorted-sample estimator: (2/J^2) * sum_i (2i-J-1) x_(i)
    ps = np.sort(pred, axis=0)
    i = np.arange(1, J + 1)[:, None]
    term2 = (2.0 / (J * J)) * ((2 * i - J - 1) * ps).sum(axis=0)
    return term1 - 0.5 * term2


def randomized_pit(pred, y, rng):
    """Randomized PIT for count forecasts (Czado, Gneiting & Held 2009).
    Returns (N,) values that should be ~Uniform(0,1) under calibration."""
    below = (pred < y[None, :]).mean(axis=0)     # F(y-1)
    at = (pred == y[None, :]).mean(axis=0)        # P(Y=y)
    return below + rng.uniform(size=y.shape[0]) * at


def coverage(pred, y, levels=(0.5, 0.8, 0.95)):
    """Empirical coverage of central predictive intervals at each nominal level."""
    out = {}
    for lv in levels:
        lo = np.quantile(pred, (1 - lv) / 2, axis=0)
        hi = np.quantile(pred, 1 - (1 - lv) / 2, axis=0)
        out[lv] = float(((y >= lo) & (y <= hi)).mean())
    return out


def log_score_smoothed(pred, y, eps: float = 1e-6):
    """Laplace/Epsilon-smoothed discrete log score: -mean(log P(Y = y_i)).
    
    pred: (J, N) predictive draws, y: (N,) true outcomes.
    Smoothes empirical mass P(Y=y_i) with eps floor to prevent numerical infinity."""
    J, N = pred.shape
    match_count = (pred == y[None, :]).sum(axis=0)
    max_k = max(float(pred.max()), float(y.max())) + 1.0
    p_hat = (match_count + eps) / (J + eps * max_k)
    return float(-np.mean(np.log(p_hat)))


def score_forecast(pred, y_true, rng, levels=(0.5, 0.8, 0.95)):
    """Full battery of point + probabilistic scores for one method on one dataset."""
    point = np.median(pred, axis=0)
    denom = max(y_true.mean(), 1e-9)              # normalisation as in Simon (2025)
    err = point - y_true
    cov = coverage(pred, y_true, levels)
    pit = randomized_pit(pred, y_true, rng)
    return {
        "nMAE": np.abs(err).mean() / denom,
        "nRMSE": np.sqrt((err ** 2).mean()) / denom,
        "nMdAE": np.median(np.abs(err)) / denom,
        "CRPS": crps_samples(pred, y_true).mean(),
        "log_score": log_score_smoothed(pred, y_true),
        **{f"cov{int(lv*100)}": cov[lv] for lv in levels},
        "sharpness_std": pred.std(axis=0).mean(),
        "pit_ks": _pit_uniformity(pit),        # 0 = perfectly uniform
        "_pit": pit,                            # keep for aggregate histograms
    }


def _pit_uniformity(pit):
    """KS distance of the PIT sample from Uniform(0,1) (0 = calibrated)."""
    p = np.sort(pit); nps = len(p)
    cdf = np.arange(1, nps + 1) / nps
    return float(np.max(np.abs(p - cdf)))


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from simulate import DatasetParams, simulate_dataset
    from estimate import fit_mcmc, fit_mle

    truth = DatasetParams(0.15, 1.2, 0.08, 1.0, N=1200, T=52.0)
    rng = np.random.default_rng(11)
    df = simulate_dataset(truth, rng=rng)
    y = df["x_star_26"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)

    # --- MCMC: full posterior predictive ---
    mc = fit_mcmc(df, n_draws=3000, burn_in=1000, thin=5, seed=1)
    pred_mcmc = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, 26, np.random.default_rng(2))

    # --- MLE plug-in: individual draws at the MLE point (no param uncertainty) ---
    mle = fit_mle(df)
    lam, mu, tau = conditional_individual_draws(
        df, mle["r"], mle["alpha"], mle["s"], mle["beta"], n_draws=400, seed=3)
    pred_mle = spp_predict(lam, mu, tau, Tcal, 26, np.random.default_rng(4))

    print(f"Dataset: N={len(df)}, active(26w)={100*(y>0).mean():.1f}%,",
          f"mean x*={y.mean():.2f}\n")
    for name, pred in [("MCMC (full posterior)", pred_mcmc),
                       ("MLE  (plug-in)       ", pred_mle)]:
        sc = score_forecast(pred, y, np.random.default_rng(5))
        print(f"{name}  nMAE={sc['nMAE']:.3f}  CRPS={sc['CRPS']:.3f}  "
              f"cov50={sc['cov50']:.2f} cov80={sc['cov80']:.2f} "
              f"cov95={sc['cov95']:.2f}  PIT-KS={sc['pit_ks']:.3f}")
    print("\n(nominal coverage targets: 0.50 / 0.80 / 0.95)")
