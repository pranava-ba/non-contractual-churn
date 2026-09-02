"""
Pareto/GGG estimation (common-regularity variant).

The misspecification stress-test in `run_misspec.py` fits the *classical* Pareto/NBD
to data with regular (Gamma-k) inter-purchase times and finds a mild loss of
calibration at strong regularity (k>=3). This module fits the *richer* model that
actually knows about regularity -- Pareto/GGG (Platzer & Reutterer 2016) -- to the
same data, to test whether modelling the timing restores calibration.

Model.  While alive, customer i's inter-purchase times are Gamma(shape=k, rate=k*lam_i)
(mean gap 1/lam_i, CV = 1/sqrt(k)); k=1 recovers the exponential (Pareto/NBD).
Lifetime tau_i ~ Exp(mu_i). Heterogeneity is Gamma: lam_i ~ Gamma(r,alpha),
mu_i ~ Gamma(s,beta). The regularity k is COMMON across customers -- exactly the
data-generating process of `simulate_dataset_ggg`, so this fit is well specified and
isolates the single extra parameter (regularity) that Pareto/NBD lacks. The full
Platzer-Reutterer model additionally lets k_i ~ Gamma(t,gamma) vary across customers
and nests this common-k case.

Sampler (augmented Metropolis-within-Gibbs).  Augmenting the latent dropout time
tau_i makes the population level identical to the Pareto/NBD Gibbs sampler in
`estimate.py`; the two changes the Gamma renewal forces are:
  * lam_i is no longer conjugate (the censored last gap contributes an upper
    incomplete-gamma survival term Q(k, k*lam_i*d) that a Gamma prior does not absorb).
    We update it with a VECTORISED independence Metropolis step whose proposal is the
    would-be Pareto/NBD conjugate Gamma(r + k*x_i, alpha + k*t_x,i); the acceptance
    ratio is then just Q(k, k*lam'*d)/Q(k, k*lam*d) -- a mild correction, so mixing is
    excellent and no tuning is needed.
  * the alive-probability and the dropped-customer tau draw use the Gamma survival
    Q(k, k*lam*v) in place of the exponential e^{-lam*v}; we evaluate the resulting
    1-D integral by vectorised quadrature. At k=1 this collapses exactly to the
    Pareto/NBD closed form (unit-tested in __main__).
  * k (scalar) is slice-sampled from the pooled renewal log-likelihood, which needs
    litt_i = sum of log inter-purchase gaps (recorded by the simulator).

mu_i stays conjugate Gamma(s+1, beta+tau_i); alpha,beta are conjugate Gamma draws and
r,s are slice-sampled, all exactly as in `estimate.py`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import gammainc, gammaincc, gammaincinv, gammaln

from estimate import HYPER, _slice_sample


def _log_surv(k: float, z: np.ndarray) -> np.ndarray:
    """log P(Gamma(shape=k, rate=1) > z) = log Q(k, z), floored to avoid -inf."""
    return np.log(np.maximum(gammaincc(k, z), 1e-300))


@dataclass
class GGGResult:
    pop_draws: np.ndarray          # (n_keep, 4) columns r, alpha, s, beta
    k_draws: np.ndarray            # (n_keep,) common regularity
    lam: np.ndarray                # (n_keep, N)
    mu: np.ndarray                 # (n_keep, N)
    tau: np.ndarray                # (n_keep, N)
    T_cal: np.ndarray              # (N,)
    t_x: np.ndarray                # (N,)

    def pop_summary(self) -> dict:
        m = self.pop_draws.mean(axis=0)
        return {"r": m[0], "alpha": m[1], "s": m[2], "beta": m[3], "k": self.k_draws.mean(),
                "E_lambda": m[0] / m[1], "E_mu": m[2] / m[3]}


def fit_ggg(df, n_draws: int = 1500, burn_in: int = 500, thin: int = 5,
            seed: int = 0, hyper: dict = None, n_quad: int = 40) -> GGGResult:
    """Fit the common-k Pareto/GGG to a cohort with columns x, t_x, litt, T_cal."""
    h = {**HYPER, **(hyper or {})}
    rng = np.random.default_rng(seed)
    x = df["x"].to_numpy(float)
    t_x = df["t_x"].to_numpy(float)
    litt = df["litt"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)
    n = len(x)
    D = T - t_x                                  # censored-gap horizon since last buy
    # relative quadrature nodes on (0,1]; v_i = grid * D_i per customer
    grid = (np.arange(1, n_quad + 1) - 0.5) / n_quad        # midpoints
    edges = np.linspace(0.0, 1.0, n_quad + 1)

    # init
    r, alpha, s, beta, k = 1.0, 10.0, 1.0, 10.0, 1.0
    lam = np.full(n, 0.1)
    mu = np.full(n, 0.1)
    tau = T + 1.0

    keep_pop, keep_k, keep_lam, keep_mu, keep_tau = [], [], [], [], []
    for it in range(n_draws):
        # ---- lambda_i: independence MH, proposal = PNBD conjugate Gamma ----------
        e = np.minimum(tau, T)
        d = np.maximum(e - t_x, 0.0)                      # active censored-gap length
        shape_l = r + k * x
        rate_l = alpha + k * t_x
        lam_prop = rng.gamma(shape=shape_l, scale=1.0 / rate_l)
        log_acc = _log_surv(k, k * lam_prop * d) - _log_surv(k, k * lam * d)
        take = np.log(rng.uniform(size=n)) < log_acc
        lam = np.where(take, lam_prop, lam)

        # ---- mu_i: conjugate ------------------------------------------------------
        mu = rng.gamma(shape=s + 1.0, scale=1.0 / (beta + tau))

        # ---- alive indicator z_i and dropout time tau_i --------------------------
        # weight_alive = e^{-mu D} Q(k, k lam D);  weight_drop = int_0^D mu e^{-mu v} Q(k, k lam v) dv
        v = grid[:, None] * D[None, :]                    # (n_quad, n)
        integrand = mu[None, :] * np.exp(-mu[None, :] * v) * gammaincc(k, k * lam[None, :] * v)
        w_step = D[None, :] / n_quad
        weight_drop = (integrand * w_step).sum(axis=0)
        weight_alive = np.exp(-mu * D) * gammaincc(k, k * lam * D)
        p_alive = weight_alive / np.maximum(weight_alive + weight_drop, 1e-300)
        z = rng.uniform(size=n) < p_alive

        tau = np.empty(n)
        tau[z] = T[z] + rng.exponential(1.0 / mu[z])
        nz = ~z
        if nz.any():
            # inverse-CDF on the quadrature grid for tau | dropped
            cell = integrand[:, nz] * w_step[:, nz]       # (n_quad, n_drop)
            cdf = np.cumsum(cell, axis=0)
            cdf /= np.maximum(cdf[-1], 1e-300)
            u = rng.uniform(size=nz.sum())
            # locate u in each column's cdf -> fractional grid position -> v
            idx = (cdf < u[None, :]).sum(axis=0)          # number of edges below u
            idx = np.clip(idx, 0, n_quad - 1)
            frac = edges[idx] + (edges[idx + 1] - edges[idx]) * rng.uniform(size=nz.sum())
            tau[nz] = t_x[nz] + frac * D[nz]

        # ---- population r, alpha, s, beta (identical to Pareto/NBD Gibbs) ---------
        sum_lam, sum_mu = lam.sum(), mu.sum()
        sum_log_lam, sum_log_mu = np.log(lam).sum(), np.log(mu).sum()
        alpha = rng.gamma(shape=h["a0"] + n * r, scale=1.0 / (h["b0"] + sum_lam))
        beta = rng.gamma(shape=h["c0"] + n * s, scale=1.0 / (h["d0"] + sum_mu))

        def logf_r(rv, a=alpha, sl=sum_log_lam):
            if rv <= 0:
                return -np.inf
            return (n * rv * np.log(a) + (rv - 1) * sl - n * gammaln(rv)
                    + (h["ar"] - 1) * np.log(rv) - h["br"] * rv)

        def logf_s(sv, b=beta, sm=sum_log_mu):
            if sv <= 0:
                return -np.inf
            return (n * sv * np.log(b) + (sv - 1) * sm - n * gammaln(sv)
                    + (h["as_"] - 1) * np.log(sv) - h["bs"] * sv)

        r = _slice_sample(r, logf_r, w=max(0.5, r), rng=rng)
        s = _slice_sample(s, logf_s, w=max(0.5, s), rng=rng)

        # ---- common regularity k: slice over the pooled renewal log-likelihood ----
        d_k = np.maximum(np.minimum(tau, T) - t_x, 0.0)

        def logf_k(kv, lm=lam, xx=x, tx=t_x, li=litt, dd=d_k):
            if kv <= 0.05 or kv > 30.0:              # flat prior on a wide bounded range
                return -np.inf
            ll = (xx * (kv * np.log(kv * lm) - gammaln(kv))
                  + (kv - 1.0) * li - kv * lm * tx
                  + _log_surv(kv, kv * lm * dd))
            return float(ll.sum())

        k = _slice_sample(k, logf_k, w=max(0.25, 0.5 * k), lower=0.05, rng=rng)

        if it >= burn_in and (it - burn_in) % thin == 0:
            keep_pop.append((r, alpha, s, beta)); keep_k.append(k)
            keep_lam.append(lam.copy()); keep_mu.append(mu.copy()); keep_tau.append(tau.copy())

    return GGGResult(
        pop_draws=np.array(keep_pop), k_draws=np.array(keep_k),
        lam=np.array(keep_lam), mu=np.array(keep_mu), tau=np.array(keep_tau),
        T_cal=T, t_x=t_x,
    )


# --------------------- Pareto/GGG predictive distribution ------------------------ #
def spp_predict_ggg(res: GGGResult, T_star: float, rng, max_gaps: int = 60):
    """Vectorised predictive samples of x* under the Gamma renewal process.

    For each posterior draw and customer alive into the forecast window, the next
    purchase completes a Gamma gap that has already been running for a = T_cal - t_x
    (left-truncated); subsequent gaps are unconditional Gamma(k, k*lam). Purchases are
    counted in (T_cal, min(tau, T_cal+T*)]. Customers who dropped out by T_cal get 0.
    Returns (n_keep, N) integer predictive samples."""
    lam, tau = res.lam, res.tau                          # (n_keep, N)
    kdraws = res.k_draws                                 # (n_keep,)
    T, t_x = res.T_cal[None, :], res.t_x[None, :]
    n_keep, N = lam.shape
    a = np.maximum(T - t_x, 0.0)                          # elapsed age of current gap
    win_end = np.minimum(tau, T + T_star)
    out = np.zeros((n_keep, N), dtype=int)
    for j in range(n_keep):
        k = kdraws[j]
        lm = lam[j]                                       # (N,)
        alive = win_end[j] > T[0]
        if not alive.any():
            continue
        rate = k * lm                                     # Gamma rate
        # first gap, left-truncated at the elapsed age a
        F0 = gammainc(k, rate * a[0])                     # lower reg. incomplete gamma
        u0 = F0 + (1.0 - F0) * rng.uniform(size=N)
        g1 = gammaincinv(k, np.clip(u0, 0.0, 1 - 1e-12)) / rate
        # subsequent unconditional gaps
        gaps = rng.standard_gamma(k, size=(N, max_gaps)) / rate[:, None]
        times = t_x[0][:, None] + g1[:, None] + np.concatenate(
            [np.zeros((N, 1)), np.cumsum(gaps[:, :-1], axis=1)], axis=1)
        # count purchases strictly after T_cal and up to the alive window end
        lo = T[0][:, None]
        hi = win_end[j][:, None]
        cnt = ((times > lo) & (times <= hi)).sum(axis=1)
        out[j] = np.where(alive, cnt, 0)
    return out


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from simulate import DatasetParams
    from simulate_misspec import simulate_dataset_ggg
    from score import randomized_pit, crps_samples, spp_predict
    from estimate import fit_mcmc

    def pit_ks(pit):
        p = np.sort(pit)
        return float(np.max(np.abs(p - np.arange(1, len(p) + 1) / len(p))))

    # ---- unit test: at k=1 the GGG alive-prob quadrature matches PNBD closed form -
    rng = np.random.default_rng(0)
    p = DatasetParams(0.15, 1.2, 0.08, 1.0, N=600, T=52.0)
    df1 = simulate_dataset_ggg(p, k=1.0, rng=rng)
    xv = df1.x.to_numpy(float); txv = df1.t_x.to_numpy(float); Tv = df1.T_cal.to_numpy(float)
    lam_t = 0.15 * np.ones(len(df1)); mu_t = 0.08 * np.ones(len(df1))
    Dv = Tv - txv
    grid = (np.arange(1, 41) - 0.5) / 40
    v = grid[:, None] * Dv[None, :]
    integ = mu_t * np.exp(-mu_t * v) * gammaincc(1.0, lam_t * v)
    wdrop = (integ * (Dv[None, :] / 40)).sum(axis=0)
    walive = np.exp(-mu_t * Dv) * gammaincc(1.0, lam_t * Dv)
    p_alive_ggg = walive / (walive + wdrop)
    rate = lam_t + mu_t; ea = np.exp(-rate * Dv)
    p_alive_pnbd = ea / (ea + (mu_t / rate) * (1 - ea))
    print(f"[unit] k=1 alive-prob max |GGG - PNBD| = "
          f"{np.max(np.abs(p_alive_ggg - p_alive_pnbd)):.2e}  (should be ~1e-3 quadrature)")

    # ---- parameter recovery + calibration at a regular k where PNBD degrades ------
    for ktrue in (1.0, 3.0):
        rng = np.random.default_rng(10 + int(ktrue))
        pp = DatasetParams(rng.uniform(.08, .20), rng.uniform(.9, 1.6),
                           rng.uniform(.04, .12), rng.uniform(.9, 1.6), N=800, T=52.0)
        df = simulate_dataset_ggg(pp, ktrue, rng=rng)
        y = df["x_star_26"].to_numpy(float); xc = df["x"].to_numpy(float)
        # Pareto/NBD (misspecified) for reference
        mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=1)
        Tcal = df["T_cal"].to_numpy(float)
        pred_pnbd = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, 26, np.random.default_rng(2))
        # Pareto/GGG
        g = fit_ggg(df, n_draws=1500, burn_in=500, thin=5, seed=3)
        pred_ggg = spp_predict_ggg(g, 26, np.random.default_rng(4))
        act = xc > 0
        pk_pnbd = pit_ks(randomized_pit(pred_pnbd[:, act], y[act], np.random.default_rng(5)))
        pk_ggg = pit_ks(randomized_pit(pred_ggg[:, act], y[act], np.random.default_rng(5)))
        print(f"\nk_true={ktrue}: GGG k_hat={g.k_draws.mean():.2f} "
              f"E(lam) true~{pp.E_lambda:.3f} GGG={g.pop_summary()['E_lambda']:.3f} "
              f"PNBD={mc.pop_summary()['E_lambda']:.3f}")
        print(f"   PIT-KS (x>0):  PNBD={pk_pnbd:.3f}   GGG={pk_ggg:.3f}   "
              f"CRPS(x>0) PNBD={crps_samples(pred_pnbd[:,act],y[act]).mean():.3f} "
              f"GGG={crps_samples(pred_ggg[:,act],y[act]).mean():.3f}")
