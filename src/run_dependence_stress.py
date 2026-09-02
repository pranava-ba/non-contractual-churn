"""
Gap G4 (un-parked at user request): stress-test the Pareto/NBD independence assumption.

The classical model assumes lambda_i (purchase rate) and mu_i (dropout rate) are drawn
*independently* (Gamma(r,alpha) and Gamma(s,beta)). Abe (2009) reported this holds empirically, and
Simon (2025) relies on it -- but never tests what happens when it is false. We generate cohorts from
a DEPENDENT DGP: (log lambda_i, log mu_i) is bivariate normal with correlation rho, matched to the
same marginal means/CVs, so rho=0 is a controlled (independent-lognormal) baseline and only the
lambda-mu dependence changes. A positive rho means frequent buyers also churn faster; negative means
frequent buyers are more loyal (the practically worrying case). We fit the independence-assuming
classical model (MLE + Gibbs MCMC) anyway and measure the induced miscalibration and bias.

This is a genuine misspecification-robustness check on an axis the project had not tested (the prior
two -- Gamma-k regularity and 2-segment mixture -- are documented as robust in the ROADMAP).

Saves results/dependence_stress_summary.csv; prints the table.

Run:  python src/run_dependence_stress.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import _simulate_customer_purchases, WEEKS_PER_90_DAYS   # noqa: E402
from estimate import fit_mcmc, fit_mle                                 # noqa: E402
from score import (spp_predict, conditional_individual_draws,          # noqa: E402
                   score_forecast)

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 6
RHOS = [-0.6, -0.3, 0.0, 0.3, 0.6]
HORIZON = 26
BEHAVIOUR = dict(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, N=1500, T=52.0)


def _lognormal_params(mean, cv):
    """(m, s) of a lognormal with the given mean and coefficient of variation."""
    s2 = np.log(1.0 + cv * cv)
    return np.log(mean) - 0.5 * s2, np.sqrt(s2)


def simulate_dependent_cohort(rho, seed, horizon=HORIZON, **beh):
    """Cohort with correlation rho between log lambda and log mu (lognormal marginals)."""
    rng = np.random.default_rng(seed)
    N, T = beh["N"], beh["T"]
    ml, sl = _lognormal_params(beh["E_lambda"], beh["CV_lambda"])
    mm, sm = _lognormal_params(beh["E_mu"], beh["CV_mu"])
    cov = np.array([[1.0, rho], [rho, 1.0]])
    z = rng.multivariate_normal([0, 0], cov, size=N)
    lam = np.exp(ml + sl * z[:, 0])
    mu = np.exp(mm + sm * z[:, 1])
    tau = rng.exponential(1.0 / mu)
    acq = rng.uniform(0.0, WEEKS_PER_90_DAYS, size=N)
    T_i = T - acq
    rows = []
    for i in range(N):
        cal_len = T_i[i]
        path = _simulate_customer_purchases(lam[i], tau[i], cal_len + horizon, rng)
        cal = path[path <= cal_len]
        x = int(cal.size)
        fut = path[(path > cal_len) & (path <= cal_len + horizon)]
        rows.append({"cust": i, "x": x, "t_x": float(cal.max()) if x else 0.0,
                     "T_cal": cal_len, f"x_star_{horizon}": int(fut.size)})
    df = pd.DataFrame(rows)
    df.attrs["true_corr"] = float(np.corrcoef(np.log(lam), np.log(mu))[0, 1])
    return df


def one(rho, seed, mcmc_draws=1500):
    df = simulate_dependent_cohort(rho, seed, **BEHAVIOUR)
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    mle = fit_mle(df, seed=seed)
    lam, mu, tau = conditional_individual_draws(df, mle["r"], mle["alpha"], mle["s"], mle["beta"],
                                                n_draws=400, seed=seed + 1)
    pred_mle = spp_predict(lam, mu, tau, Tcal, HORIZON, np.random.default_rng(seed + 2))
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 3)
    pred_mc = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(seed + 4))
    out = {"rho": rho, "seed": seed, "true_corr": df.attrs["true_corr"]}
    for name, pred in [("MLE", pred_mle), ("MCMC", pred_mc)]:
        sc = score_forecast(pred, y, np.random.default_rng(seed + 5))
        out[f"{name}_CRPS"] = sc["CRPS"]; out[f"{name}_pit_ks"] = sc["pit_ks"]
        out[f"{name}_cov95"] = sc["cov95"]; out[f"{name}_nMAE"] = sc["nMAE"]
    return out


def main():
    rows = []
    for rho in RHOS:
        t = time.time()
        for seed in range(SEEDS):
            rows.append(one(rho, 9000 + seed))
        print(f"[rho={rho:+.1f}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)
    raw = pd.DataFrame(rows)
    summ = raw.groupby("rho").mean(numeric_only=True).drop(columns="seed").reset_index()
    summ.to_csv(RES / "dependence_stress_summary.csv", index=False)

    print("\n=== Independence-assumption stress test: fit classical PNBD to dependent data ===")
    print(f"{'rho':>6s}{'true_corr':>10s}{'MCMC PIT-KS':>12s}{'MCMC cov95':>11s}"
          f"{'MLE PIT-KS':>11s}{'MCMC CRPS':>10s}{'MCMC nMAE':>10s}")
    for _, r in summ.iterrows():
        print(f"{r.rho:>+6.1f}{r.true_corr:>10.3f}{r.MCMC_pit_ks:>12.3f}{r.MCMC_cov95:>11.3f}"
              f"{r.MLE_pit_ks:>11.3f}{r.MCMC_CRPS:>10.3f}{r.MCMC_nMAE:>10.3f}")
    base = summ[summ.rho == 0.0].iloc[0]
    worst = summ.loc[summ.MCMC_pit_ks.idxmax()]
    print(f"\nPIT-KS at rho=0 (control): {base.MCMC_pit_ks:.3f}; worst over rho: "
          f"{worst.MCMC_pit_ks:.3f} at rho={worst.rho:+.1f}.")
    print(f"[saved] {RES/'dependence_stress_summary.csv'}")


if __name__ == "__main__":
    main()
