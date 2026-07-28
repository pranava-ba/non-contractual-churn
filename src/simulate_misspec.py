"""
Misspecified data generator: Pareto/NBD heterogeneity + dropout, but REGULAR
(Gamma) inter-purchase times instead of exponential.

Pareto/NBD assumes purchases follow a Poisson process while alive (exponential
inter-purchase times, IPT). Real purchasing is typically more *regular* than
Poisson. The Pareto/GGG model (Platzer & Reutterer 2016) captures this with
Gamma-distributed IPTs of shape k (the "regularity"):

    IPT ~ Gamma(shape=k, rate=k*lambda_i)   =>  mean IPT = 1/lambda_i (rate preserved),
                                                 CV(IPT) = 1/sqrt(k).

k = 1 reduces exactly to Pareto/NBD (exponential IPT). k > 1 is more regular
(clock-like) purchasing — a realistic, named departure from the model's assumptions.

We generate data at various k, fit the (misspecified) Pareto/NBD, and ask whether
its forecasts stay calibrated. This isolates a genuine model-misspecification effect,
unlike the main study which draws from Pareto/NBD itself.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from simulate import DatasetParams, WEEKS_PER_90_DAYS, moments_to_gamma  # noqa: F401


def _sim_customer_ggg(lam, tau, horizon, k, rng):
    """Renewal process with Gamma(shape=k, rate=k*lam) gaps, truncated at min(tau,horizon)."""
    end = min(tau, horizon)
    if end <= 0:
        return np.empty(0)
    scale = 1.0 / (k * lam)  # so mean gap = k*scale = 1/lam
    times, t = [], 0.0
    while True:
        batch = rng.gamma(k, scale, size=max(16, int(lam * end * 2) + 8))
        cs = t + np.cumsum(batch)
        keep = cs[cs <= end]
        times.append(keep)
        if len(keep) < len(batch):
            break
        t = cs[-1]
    return np.concatenate(times) if times else np.empty(0)


def simulate_dataset_ggg(params: DatasetParams, k: float,
                         horizons=(13, 26, 52), rng=None) -> pd.DataFrame:
    """Same cohort structure as simulate.simulate_dataset but with regularity k."""
    if rng is None:
        rng = np.random.default_rng()
    N = params.N
    lam = rng.gamma(shape=params.r, scale=1.0 / params.alpha, size=N)
    mu = rng.gamma(shape=params.s, scale=1.0 / params.beta, size=N)
    tau = rng.exponential(1.0 / mu)
    acq = rng.uniform(0.0, WEEKS_PER_90_DAYS, size=N)
    T_i = params.T - acq
    max_h = max(horizons)

    rows = []
    for i in range(N):
        cal_len = T_i[i]
        path = _sim_customer_ggg(lam[i], tau[i], cal_len + max_h, k, rng)
        cal = path[path <= cal_len]
        x = int(cal.size)
        # litt = sum of log inter-purchase gaps (gaps from acquisition at t=0 through
        # the x observed repeat purchases). This is the sufficient statistic that
        # identifies the Gamma-renewal regularity k, needed by the Pareto/GGG fit.
        # Computed post-hoc from `cal` -> consumes no rng, so datasets regenerated
        # with the same seed stay byte-identical to the Pareto/NBD misspec run.
        litt = float(np.log(np.diff(np.concatenate(([0.0], cal)))).sum()) if x > 0 else 0.0
        row = {"cust": i, "x": x, "t_x": float(cal.max()) if x > 0 else 0.0,
               "litt": litt,
               "T_cal": cal_len, "alive_at_T": bool(tau[i] > cal_len),
               "lambda_true": lam[i], "mu_true": mu[i]}
        for h in horizons:
            fut = path[(path > cal_len) & (path <= cal_len + h)]
            row[f"x_star_{h}"] = int(fut.size)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.attrs["params"] = {**params.as_dict(), "regularity_k": k}
    return df


def _sim_customer_exp(lam, tau, horizon, rng):
    """Exponential-IPT (Poisson) purchases — as in the true Pareto/NBD."""
    end = min(tau, horizon)
    if end <= 0:
        return np.empty(0)
    times, t = [], 0.0
    while True:
        batch = rng.exponential(1.0 / lam, size=max(16, int(lam * end * 2) + 8))
        cs = t + np.cumsum(batch)
        keep = cs[cs <= end]
        times.append(keep)
        if len(keep) < len(batch):
            break
        t = cs[-1]
    return np.concatenate(times) if times else np.empty(0)


def simulate_dataset_mixture(N, T, E_lambda, ratio, E_mu, CV_mu,
                             p_heavy=0.3, within_cv=0.5,
                             horizons=(13, 26, 52), rng=None) -> pd.DataFrame:
    """Purchase-rate heterogeneity is a 2-SEGMENT MIXTURE (light + heavy buyers)
    instead of a single gamma. `ratio` = E(lambda)_heavy / E(lambda)_light controls
    bimodality; ratio=1 collapses to a single population (near-gamma baseline).
    Overall E(lambda) is held fixed. IPT and dropout follow Pareto/NBD assumptions,
    so the ONLY misspecification is the heterogeneity distribution."""
    if rng is None:
        rng = np.random.default_rng()
    El_light = E_lambda / ((1 - p_heavy) + p_heavy * ratio)
    El_heavy = ratio * El_light
    heavy = rng.uniform(size=N) < p_heavy
    means = np.where(heavy, El_heavy, El_light)
    shape = 1.0 / (within_cv ** 2)
    lam = rng.gamma(shape=shape, scale=means / shape)      # per-customer, per segment
    s_mu, b_mu = moments_to_gamma(E_mu, CV_mu)
    mu = rng.gamma(shape=s_mu, scale=1.0 / b_mu, size=N)
    tau = rng.exponential(1.0 / mu)
    acq = rng.uniform(0.0, WEEKS_PER_90_DAYS, size=N)
    T_i = T - acq
    max_h = max(horizons)

    rows = []
    for i in range(N):
        cal_len = T_i[i]
        path = _sim_customer_exp(lam[i], tau[i], cal_len + max_h, rng)
        cal = path[path <= cal_len]
        x = int(cal.size)
        row = {"cust": i, "x": x, "t_x": float(cal.max()) if x > 0 else 0.0,
               "T_cal": cal_len, "segment": "heavy" if heavy[i] else "light"}
        for h in horizons:
            fut = path[(path > cal_len) & (path <= cal_len + h)]
            row[f"x_star_{h}"] = int(fut.size)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.attrs["params"] = dict(N=N, T=T, E_lambda=E_lambda, ratio=ratio,
                              p_heavy=p_heavy, El_light=El_light, El_heavy=El_heavy)
    return df


if __name__ == "__main__":
    from simulate import DatasetParams as DP
    rng = np.random.default_rng(0)
    p = DP(0.12, 1.2, 0.08, 1.0, N=800, T=52.0)
    for k in [1.0, 2.0, 4.0]:
        df = simulate_dataset_ggg(p, k, rng=rng)
        print(f"ggg  k={k}: mean x(cal)={df.x.mean():.2f}, "
              f"active26={100*(df.x_star_26>0).mean():.1f}%")
    for ratio in [1.0, 4.0, 10.0]:
        df = simulate_dataset_mixture(800, 52.0, 0.12, ratio, 0.08, 1.0, rng=rng)
        print(f"mix ratio={ratio}: mean x(cal)={df.x.mean():.2f}, "
              f"active26={100*(df.x_star_26>0).mean():.1f}%, "
              f"heavy mean x={df[df.segment=='heavy'].x.mean():.2f} "
              f"light mean x={df[df.segment=='light'].x.mean():.2f}")
