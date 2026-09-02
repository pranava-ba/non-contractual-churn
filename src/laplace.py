"""
Gap E4: a Laplace approximate-Bayes middle tier between the MLE point estimate and full MCMC.

Simon (2025) treats "MLE point estimate" and "full MCMC posterior" as the only two options. A
well-established third tier sits between them: a Gaussian (Laplace) approximation of the
hyperparameter posterior, obtained from the MLE mode plus the observed-information Hessian -- one
optimisation and one 4x4 Hessian, no Markov chain to mix.

We propagate that hyperparameter uncertainty into the forecast by an individual-augmentation pass
that is *identical* to `score.conditional_individual_draws` (the MLE plug-in), with one change: at
each iteration the population parameters (r,alpha,s,beta) are redrawn from the Laplace Gaussian
instead of held fixed at theta_hat. So the Laplace predictive differs from the MLE plug-in by
exactly the hyperparameter-uncertainty term -- the O(1/N) term of the law-of-total-variance
decomposition. This gives a clean, cheap test of whether adding parameter uncertainty changes the
forecast, and a third analytic estimation route alongside amortized inference (`amortized.py`).

Expectation, given the MCMC = MLE null and the T3 noise-floor result (the O(1/N) term is
negligible at realistic N): Laplace should coincide with both MLE and MCMC on calibration, at a
fraction of MCMC's wall-clock.

Run:  python src/laplace.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import fit_mle, _pnbd_loglik, _LO, _HI            # noqa: E402
from score import spp_predict, score_forecast                  # noqa: E402


def _neg_ll(p, x, t_x, T):
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        ll = _pnbd_loglik(p, x, t_x, T)
    return -ll if np.isfinite(ll) else 1e12


def laplace_cov(df, mode_log, eps: float = 1e-3):
    """Covariance of the Laplace Gaussian over LOG hyperparameters: the inverse observed-
    information (Hessian of the negative log-likelihood) at the mode, made positive-definite by
    eigenvalue clipping (guards against finite-difference indefiniteness)."""
    x = df["x"].to_numpy(float); t_x = df["t_x"].to_numpy(float); T = df["T_cal"].to_numpy(float)
    f = lambda p: _neg_ll(p, x, t_x, T)
    p0 = np.asarray(mode_log, float)
    n = 4
    H = np.zeros((n, n))
    f0 = f(p0)
    e = np.eye(n) * eps
    for i in range(n):
        H[i, i] = (f(p0 + e[i]) - 2 * f0 + f(p0 - e[i])) / (eps * eps)
        for j in range(i + 1, n):
            fpp = f(p0 + e[i] + e[j]); fpm = f(p0 + e[i] - e[j])
            fmp = f(p0 - e[i] + e[j]); fmm = f(p0 - e[i] - e[j])
            H[i, j] = H[j, i] = (fpp - fpm - fmp + fmm) / (4 * eps * eps)
    # symmetric eigen-repair -> PD covariance
    H = 0.5 * (H + H.T)
    w, V = np.linalg.eigh(H)
    w = np.clip(w, 1e-6, None)                       # clip tiny/negative curvature
    Sigma = (V / w) @ V.T
    return 0.5 * (Sigma + Sigma.T)


def laplace_augmented_draws(df, mode_log, Sigma, n_draws: int = 400, burn_in: int = 150,
                            thin: int = 2, seed: int = 0):
    """Individual (lambda_i, mu_i, tau_i) draws that integrate over the Laplace hyperparameter
    posterior: same augmentation recursion as the MLE plug-in, but (r,alpha,s,beta) is redrawn
    from N(mode_log, Sigma) each iteration."""
    rng = np.random.default_rng(seed)
    x = df["x"].to_numpy(float); t_x = df["t_x"].to_numpy(float); T = df["T_cal"].to_numpy(float)
    n = len(x)
    Lc = np.linalg.cholesky(Sigma)
    tau = T + 1.0
    keep_l, keep_m, keep_t = [], [], []
    total = burn_in + n_draws * thin
    for it in range(total):
        theta = np.clip(mode_log + Lc @ rng.standard_normal(4), _LO, _HI)
        r, alpha, s, beta = np.exp(theta)
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


def laplace_predict(df, horizon: int, n_draws: int = 400, seed: int = 0):
    """Laplace posterior-predictive samples (n_draws, N) of x*. One MLE fit + Hessian + a short
    augmentation pass -- no Markov chain over the population parameters."""
    mle = fit_mle(df, seed=seed)
    Sigma = laplace_cov(df, mle["logparams"])
    lam, mu, tau = laplace_augmented_draws(df, mle["logparams"], Sigma,
                                           n_draws=n_draws, seed=seed + 1)
    Tcal = df["T_cal"].to_numpy(float)
    return spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 2)), Sigma


def compare_estimation_tiers(df, horizon: int, seed: int = 0, mcmc_draws: int = 1200):
    """Score the three estimation tiers -- MLE plug-in, Laplace, MCMC -- on one cohort, with
    wall-clock for each. Returns {method: {scores..., '_secs': t}}."""
    from estimate import fit_mcmc
    from score import conditional_individual_draws

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    out = {}

    t = time.time()
    mle = fit_mle(df, seed=seed)
    lam, mu, tau = conditional_individual_draws(df, mle["r"], mle["alpha"], mle["s"], mle["beta"],
                                                n_draws=400, seed=seed + 1)
    pred_mle = spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 2))
    t_mle = time.time() - t

    t = time.time()
    pred_lap, _ = laplace_predict(df, horizon, n_draws=400, seed=seed + 10)
    t_lap = time.time() - t

    t = time.time()
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=400, thin=4, seed=seed + 20)
    pred_mc = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 21))
    t_mc = time.time() - t

    for name, pred, secs in [("MLE_plugin", pred_mle, t_mle), ("Laplace", pred_lap, t_lap),
                             ("MCMC", pred_mc, t_mc)]:
        sc = score_forecast(pred, y, np.random.default_rng(seed + 30))
        out[name] = {"CRPS": sc["CRPS"], "pit_ks": sc["pit_ks"], "cov95": sc["cov95"],
                     "cov50": sc["cov50"], "nMAE": sc["nMAE"], "_secs": secs}
    return out


if __name__ == "__main__":
    from simulate import DatasetParams, simulate_dataset
    from empirical import load_cdnow, elog_to_summary

    print("=== E4: MLE plug-in vs Laplace vs MCMC (calibration + wall-clock) ===")
    print(f"{'dataset':16s}{'method':12s}{'CRPS':>8s}{'PIT-KS':>8s}{'cov95':>8s}"
          f"{'nMAE':>8s}{'secs':>8s}")
    cases = [("Simulated", simulate_dataset(
                  DatasetParams(0.15, 1.3, 0.08, 1.2, N=1500, T=52.0),
                  rng=np.random.default_rng(1)), 26),
             ("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26)]
    for name, df, h in cases:
        res = compare_estimation_tiers(df, h, seed=1)
        for m in ("MLE_plugin", "Laplace", "MCMC"):
            s = res[m]
            print(f"{name:16s}{m:12s}{s['CRPS']:>8.3f}{s['pit_ks']:>8.3f}{s['cov95']:>8.3f}"
                  f"{s['nMAE']:>8.3f}{s['_secs']:>8.1f}")
