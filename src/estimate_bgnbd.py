"""
Phase 2, Step 10: the BG/NBD model (Fader, Hardie & Lee 2005) under the calibration lens.

BG/NBD is the popular "easy" alternative to Pareto/NBD: while alive a customer buys as Poisson(lambda),
and after each purchase drops out with probability p; heterogeneity is lambda ~ Gamma(r, alpha),
p ~ Beta(a, b). The likelihood is closed form (MLE, no sampler). Its predictive count over a window
factorises cleanly: a customer alive at T makes min(K, N) future purchases, where K ~ Geometric(p)
is the number of purchases before dropout and N ~ Poisson(lambda * T*) is the Poisson count in the
window -- so the predictive is fully vectorised, no per-customer simulation.

We add it as a second structural model to compare against Pareto/NBD on calibration.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize
from scipy.special import gammaln


def _bgnbd_loglik(params, x, tx, T):
    r, alpha, a, b = np.exp(params)
    lA1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
    lA2 = gammaln(a + b) + gammaln(b + x) - gammaln(b) - gammaln(a + b + x)
    lA3 = -(r + x) * np.log(alpha + T)
    lA4 = np.log(a) - np.log(b + x - 1.0) - (r + x) * np.log(alpha + tx)
    term = np.where(x > 0, np.logaddexp(lA3, lA4), lA3)
    ll = np.sum(lA1 + lA2 + term)
    return ll if np.isfinite(ll) else -np.inf


_LO, _HI = np.log(1e-5), np.log(1e5)


@dataclass
class BGNBDResult:
    r: float
    alpha: float
    a: float
    b: float

    def as_tuple(self):
        return self.r, self.alpha, self.a, self.b


def fit_bgnbd(df, seed: int = 0, n_start: int = 3) -> BGNBDResult:
    """Maximum-likelihood BG/NBD fit (bounded, method-of-moments started, multistart)."""
    x = df["x"].to_numpy(float)
    tx = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)

    def neg(p):
        if np.any(p < _LO) or np.any(p > _HI):
            return 1e12
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            ll = _bgnbd_loglik(p, x, tx, T)
        return -ll if np.isfinite(ll) else 1e12

    El0 = min(max(x.mean() / max(T.mean(), 1.0), 0.01), 0.5)
    mom = np.log([1.0, 1.0 / El0, 1.0, 1.0])
    rng = np.random.default_rng(seed)
    starts = [mom] + [np.clip(mom + rng.normal(0, 0.6, 4), _LO, _HI) for _ in range(n_start - 1)]

    best = None
    for st in starts:
        res = optimize.minimize(neg, st, method="Nelder-Mead",
                                options=dict(maxiter=4000, xatol=1e-5, fatol=1e-5))
        if -10.0 < res.fun < 1e11 and (best is None or res.fun < best.fun):
            best = res
    if best is None:
        best = optimize.minimize(neg, mom, method="Nelder-Mead", options=dict(maxiter=4000))
    r, alpha, a, b = np.exp(best.x)
    return BGNBDResult(r, alpha, a, b)


def bgnbd_predict(df, fit: BGNBDResult, horizon: float, n_draws: int = 400, seed: int = 0):
    """Vectorised BG/NBD predictive of the future purchase count. Returns (n_draws, N) integers.

    P(alive at T) is the closed-form BG/NBD expression; if alive, count = min(K, N) with
    K ~ Geometric(p), N ~ Poisson(lambda * T*), lambda ~ Gamma(r+x, alpha+T), p ~ Beta(a, b+x)."""
    r, alpha, a, b = fit.as_tuple()
    x = df["x"].to_numpy(float)
    tx = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)
    N = len(x)

    ratio = np.where(x > 0, (a / np.maximum(b + x - 1.0, 1e-9)) * ((alpha + T) / (alpha + tx)) ** (r + x), 0.0)
    p_alive = 1.0 / (1.0 + ratio)

    rng = np.random.default_rng(seed)
    lam = rng.gamma(shape=r + x, scale=1.0 / (alpha + T), size=(n_draws, N))
    p_drop = np.clip(rng.beta(a, b + x, size=(n_draws, N)), 1e-6, 1.0)
    alive = rng.uniform(size=(n_draws, N)) < p_alive[None, :]
    n_pois = rng.poisson(lam * horizon)
    K = rng.geometric(p_drop)
    return np.where(alive, np.minimum(K, n_pois), 0).astype(float)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from simulate import DatasetParams, simulate_dataset
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast, randomized_pit

    # fit BG/NBD to a Pareto/NBD cohort; compare its calibration to Pareto/NBD (MCMC)
    df = simulate_dataset(DatasetParams(0.15, 1.2, 0.08, 1.0, N=1500, T=52.0),
                          rng=np.random.default_rng(3))
    y = df["x_star_26"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    bg = fit_bgnbd(df)
    print(f"BG/NBD MLE: r={bg.r:.3f} alpha={bg.alpha:.3f} a={bg.a:.3f} b={bg.b:.3f}  "
          f"E(lambda)={bg.r/bg.alpha:.3f}")
    pred_bg = bgnbd_predict(df, bg, 26, seed=1)
    mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=2)
    pred_pn = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, 26, np.random.default_rng(4))
    for name, pred in [("Pareto/NBD", pred_pn), ("BG/NBD", pred_bg)]:
        sc = score_forecast(pred, y, np.random.default_rng(5))
        print(f"  {name:11s} CRPS={sc['CRPS']:.3f}  PIT-KS={sc['pit_ks']:.3f}  cov95={sc['cov95']:.3f}")
