"""
Gap E1: a gradient-based (HMC) sampler as a fourth estimation arm, alongside the Abe/Gibbs MCMC,
MLE, and amortized/Laplace routes.

Simon (2025) uses only Abe's (2009) data-augmentation Gibbs sampler. Here we sample the four
population parameters theta = (log r, log alpha, log s, log beta) directly from the *marginal*
Pareto/NBD log-posterior (the closed-form likelihood in `estimate._pnbd_loglik`, which integrates
lambda_i and mu_i out analytically) using Hamiltonian Monte Carlo with a numerical gradient -- no
data augmentation, no latent variables at the population level. Individual draws for the forecast
are then generated per posterior sample, as in the Laplace tier.

Self-contained (numpy/scipy only): the posterior is smooth and 4-dimensional, so a finite-difference
gradient and a short-adaptation leapfrog integrator mix well. The point is a genuinely different
sampler kernel; the expectation, given MCMC = MLE, is that HMC agrees with Gibbs on the population
posterior and on forecast calibration -- confirming the result is not specific to one sampler.

Run:  python src/hmc.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import _pnbd_loglik, _LO, _HI, fit_mle             # noqa: E402
from score import spp_predict, score_forecast                   # noqa: E402

PRIOR_SD = 5.0            # weak N(0, PRIOR_SD^2) prior on each log-parameter (propriety)


def _log_post(theta, x, t_x, T):
    if np.any(theta < _LO) or np.any(theta > _HI):
        return -np.inf
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        ll = _pnbd_loglik(theta, x, t_x, T)
    if not np.isfinite(ll):
        return -np.inf
    return ll - 0.5 * np.sum((theta / PRIOR_SD) ** 2)


def _grad(theta, x, t_x, T, h=1e-4):
    g = np.zeros(4)
    for i in range(4):
        e = np.zeros(4); e[i] = h
        g[i] = (_log_post(theta + e, x, t_x, T) - _log_post(theta - e, x, t_x, T)) / (2 * h)
    return g


def hmc_sample(df, n_samples: int = 500, warmup: int = 300, L: int = 20, seed: int = 0):
    """HMC on the 4-D marginal log-posterior. Returns (n_samples, 4) kept LOG-parameter draws.
    Step size is adapted during warmup to target ~0.7 acceptance; init at the MLE mode."""
    rng = np.random.default_rng(seed)
    x = df["x"].to_numpy(float); t_x = df["t_x"].to_numpy(float); T = df["T_cal"].to_numpy(float)
    theta = np.clip(np.asarray(fit_mle(df, seed=seed)["logparams"], float), _LO + 1, _HI - 1)
    eps = 0.02
    kept, accepts = [], 0
    total = warmup + n_samples
    for it in range(total):
        p0 = rng.standard_normal(4)
        th = theta.copy()
        g = _grad(th, x, t_x, T)
        p = p0 + 0.5 * eps * g
        for _ in range(L):
            th = th + eps * p
            g = _grad(th, x, t_x, T)
            p = p + eps * g
        p -= 0.5 * eps * g
        cur_H = -_log_post(theta, x, t_x, T) + 0.5 * p0 @ p0
        new_H = -_log_post(th, x, t_x, T) + 0.5 * p @ p
        if np.isfinite(new_H) and np.log(rng.uniform()) < cur_H - new_H:
            theta = th; accepts += 1
        # dual-ish step-size adaptation during warmup
        if it < warmup:
            acc_rate = accepts / (it + 1)
            eps *= 1.05 if acc_rate > 0.7 else 0.95
        elif (it - warmup) % 1 == 0:
            kept.append(theta.copy())
    return np.array(kept), accepts / total


def augmented_draws_from_theta(df, theta_log_draws, n_draws=400, burn_in=150, thin=2, seed=0):
    """Individual (lambda_i, mu_i, tau_i) draws integrating over a set of population draws: same
    augmentation recursion as the MLE plug-in, but theta is drawn (with replacement) from
    `theta_log_draws` each iteration -- so any posterior sample (Gibbs, HMC, Laplace) plugs in."""
    rng = np.random.default_rng(seed)
    x = df["x"].to_numpy(float); t_x = df["t_x"].to_numpy(float); T = df["T_cal"].to_numpy(float)
    n = len(x); M = len(theta_log_draws)
    tau = T + 1.0
    keep_l, keep_m, keep_t = [], [], []
    total = burn_in + n_draws * thin
    for it in range(total):
        r, alpha, s, beta = np.exp(theta_log_draws[rng.integers(M)])
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


def hmc_predict(df, horizon, n_hmc=400, warmup=250, seed=0):
    """Forecast predictive samples via HMC population draws + individual augmentation."""
    draws, acc = hmc_sample(df, n_samples=n_hmc, warmup=warmup, seed=seed)
    lam, mu, tau = augmented_draws_from_theta(df, draws, n_draws=400, seed=seed + 1)
    Tcal = df["T_cal"].to_numpy(float)
    pred = spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 2))
    Elam = float(np.exp(draws[:, 0] - draws[:, 1]).mean())
    Emu = float(np.exp(draws[:, 2] - draws[:, 3]).mean())
    return pred, dict(accept=acc, E_lambda=Elam, E_mu=Emu)


def compare_samplers(df, horizon, seed=0, mcmc_draws=1500):
    """Gibbs vs HMC on population posterior + forecast calibration."""
    from estimate import fit_mcmc
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    pred_g = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    pred_h, meta = hmc_predict(df, horizon, seed=seed + 10)

    out = {}
    for name, pred, El, Em in [("Gibbs", pred_g, mc.pop_summary()["E_lambda"], mc.pop_summary()["E_mu"]),
                               ("HMC", pred_h, meta["E_lambda"], meta["E_mu"])]:
        sc = score_forecast(pred, y, np.random.default_rng(seed + 3))
        out[name] = {"E_lambda": El, "E_mu": Em, "CRPS": sc["CRPS"], "pit_ks": sc["pit_ks"],
                     "cov95": sc["cov95"], "nMAE": sc["nMAE"]}
    out["_hmc_accept"] = meta["accept"]
    return out


if __name__ == "__main__":
    from simulate import DatasetParams, simulate_dataset
    from empirical import load_cdnow, elog_to_summary

    print("=== E1: Gibbs vs HMC (population posterior + forecast calibration) ===")
    print(f"{'dataset':12s}{'sampler':8s}{'E[lam]':>9s}{'E[mu]':>9s}{'CRPS':>8s}{'PIT-KS':>8s}{'cov95':>8s}")
    cases = [("Simulated", simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=1500, T=52.0),
                                            rng=np.random.default_rng(1)), 26),
             ("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26)]
    for name, df, h in cases:
        res = compare_samplers(df, h, seed=1)
        for s in ("Gibbs", "HMC"):
            r = res[s]
            print(f"{name:12s}{s:8s}{r['E_lambda']:>9.4f}{r['E_mu']:>9.4f}{r['CRPS']:>8.3f}"
                  f"{r['pit_ks']:>8.3f}{r['cov95']:>8.3f}")
        print(f"  (HMC acceptance: {res['_hmc_accept']:.2f})")
