"""
Gap D2 (un-parked at user request): non-stationarity / seasonality robustness.

Every BTYD model assumes a customer's purchase rate lambda_i is constant over their lifetime. Real
demand is seasonal. We inject a chain-wide seasonal multiplier into the true intensity,

    rate_i(t) = lambda_i * (1 + A * sin(2*pi*t/52)),     amplitude A in [0, 1],

via a thinned time-varying-rate Poisson process, fit the stationary Pareto/NBD (MCMC) anyway, and
measure how much calibration and accuracy degrade as the seasonal amplitude grows. A=0 is the
stationary control. This quantifies the robustness of the calibration finding to a specific,
realistic misspecification the model does not know about.

Saves results/seasonality_stress_summary.csv; prints the table.

Run:  python src/run_seasonality_stress.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, WEEKS_PER_90_DAYS           # noqa: E402
from score import spp_predict, score_forecast                  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 6
AMPLITUDES = [0.0, 0.3, 0.6, 1.0]
PERIOD = 52.0
HORIZON = 26
BEHAVIOUR = dict(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, N=1500, T=52.0)


def seasonal_mult(t, A):
    return 1.0 + A * np.sin(2.0 * np.pi * t / PERIOD)


def _sim_customer(lam_i, tau_i, A, horizon, phase, rng):
    """Thinned time-varying-rate repeat-purchase times in (0, horizon], truncated at tau_i."""
    end = min(tau_i, horizon)
    if end <= 0:
        return np.empty(0)
    lam_max = lam_i * (1.0 + A)
    times, t = [], 0.0
    while True:
        batch = rng.exponential(1.0 / lam_max, size=max(16, int(lam_max * end * 2) + 8))
        cs = t + np.cumsum(batch)
        cand = cs[cs <= end]
        if cand.size:
            accept = seasonal_mult(cand + phase, A) / (1.0 + A)
            times.append(cand[rng.uniform(size=cand.size) < accept])
        if cand.size < batch.size:
            break
        t = cs[-1]
    return np.concatenate(times) if times else np.empty(0)


def simulate_seasonal_cohort(A, seed, horizon=HORIZON, **beh):
    rng = np.random.default_rng(seed)
    p = DatasetParams(**beh)
    N = p.N
    lam = rng.gamma(p.r, 1.0 / p.alpha, size=N)
    mu = rng.gamma(p.s, 1.0 / p.beta, size=N)
    tau = rng.exponential(1.0 / mu)
    acq = rng.uniform(0.0, WEEKS_PER_90_DAYS, size=N)
    T_i = p.T - acq
    phase = rng.uniform(0.0, PERIOD)               # cohort's calendar offset (shared)
    rows = []
    for i in range(N):
        cal_len = T_i[i]
        path = _sim_customer(lam[i], tau[i], A, cal_len + horizon, phase, rng)
        cal = path[path <= cal_len]
        x = int(cal.size)
        fut = path[(path > cal_len) & (path <= cal_len + horizon)]
        rows.append({"cust": i, "x": x, "t_x": float(cal.max()) if x else 0.0,
                     "T_cal": cal_len, f"x_star_{horizon}": int(fut.size)})
    return pd.DataFrame(rows)


def one(A, seed, mcmc_draws=1500):
    from estimate import fit_mcmc
    df = simulate_seasonal_cohort(A, seed, **BEHAVIOUR)
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(seed + 2))
    sc = score_forecast(pred, y, np.random.default_rng(seed + 3))
    return dict(amplitude=A, seed=seed, CRPS=sc["CRPS"], pit_ks=sc["pit_ks"],
                cov95=sc["cov95"], cov50=sc["cov50"], nMAE=sc["nMAE"], mean_xstar=float(y.mean()))


def main():
    rows = []
    for A in AMPLITUDES:
        t = time.time()
        for seed in range(SEEDS):
            rows.append(one(A, 9500 + seed))
        print(f"[A={A}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)
    raw = pd.DataFrame(rows)
    summ = raw.groupby("amplitude").mean(numeric_only=True).drop(columns="seed").reset_index()
    summ.to_csv(RES / "seasonality_stress_summary.csv", index=False)

    print("\n=== Seasonality stress test: fit stationary PNBD to seasonal data (MCMC) ===")
    print(f"{'amplitude':>10s}{'PIT-KS':>9s}{'cov95':>8s}{'cov50':>8s}{'CRPS':>8s}{'nMAE':>8s}")
    for _, r in summ.iterrows():
        print(f"{r.amplitude:>10.1f}{r.pit_ks:>9.3f}{r.cov95:>8.3f}{r.cov50:>8.3f}"
              f"{r.CRPS:>8.3f}{r.nMAE:>8.3f}")
    b = summ[summ.amplitude == 0.0].iloc[0]; w = summ[summ.amplitude == 1.0].iloc[0]
    print(f"\nPIT-KS: {b.pit_ks:.3f} (stationary) -> {w.pit_ks:.3f} (amplitude 1.0). "
          f"cov95: {b.cov95:.3f} -> {w.cov95:.3f}.")
    print(f"[saved] {RES/'seasonality_stress_summary.csv'}")


if __name__ == "__main__":
    main()
