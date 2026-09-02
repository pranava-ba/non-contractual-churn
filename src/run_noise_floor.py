"""
Gap T3 (empirical): the noise-floor / estimation-error decomposition of forecast error.

nMAE and CRPS conflate two error sources: (a) hyperparameter estimation error -- (r,alpha,s,beta)
mis-estimated from finite calibration data -- and (b) irreducible individual-level stochasticity --
a counting process is noisy over a finite window even at the TRUE parameters. Because the simulated
data has known ground truth, we can separate them by scoring the same forecast target three ways:

  1. est         : predictive at the MLE estimate theta_hat            -> TOTAL error (what you get)
  2. true_hyper  : predictive at the TRUE hyperparameters (r,alpha,s,beta)
                                                            -> removes estimation error
  3. true_indiv  : predictive at the TRUE individual (lambda_i, mu_i, tau_i)
                                                            -> only Poisson counting noise remains

This is the empirical counterpart of the law-of-total-variance result in
`docs/theory_variance_decomposition.md`:
  - est - true_hyper       ~ the O(1/N) hyperparameter-estimation term  (FIXABLE with more data)
  - true_hyper - true_indiv~ the O(1)   individual-posterior term       (irreducible given a summary)
  - true_indiv             ~ pure counting noise                        (structurally irreducible)

We sweep N to show the fixable term contract as ~1/N while the floor stays put.

Saves results/noise_floor_summary.csv and prints the table.

Run:  python src/run_noise_floor.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset            # noqa: E402
from estimate import fit_mle                                    # noqa: E402
from score import (conditional_individual_draws, spp_predict,   # noqa: E402
                   score_forecast)

RES = Path(__file__).resolve().parent.parent / "results"
N_GRID = [500, 1000, 2000, 4000]
SEEDS = 6
HORIZON = 26
J = 400                      # predictive draws per level
# fixed behavioural regime (the same one used across the Phase-2 studies)
BEHAVIOUR = dict(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, T=52.0)


def _score(pred, y):
    sc = score_forecast(pred, y, np.random.default_rng(0))
    return sc["nMAE"], sc["CRPS"]


def one(N: int, seed: int):
    p = DatasetParams(N=N, **BEHAVIOUR)
    df = simulate_dataset(p, rng=np.random.default_rng(seed))
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)

    # (1) est: MLE plug-in individual posterior
    mle = fit_mle(df)
    lam, mu, tau = conditional_individual_draws(
        df, mle["r"], mle["alpha"], mle["s"], mle["beta"], n_draws=J, seed=seed + 1)
    pred_est = spp_predict(lam, mu, tau, Tcal, HORIZON, np.random.default_rng(seed + 2))

    # (2) true_hyper: individual posterior at the TRUE hyperparameters
    lam2, mu2, tau2 = conditional_individual_draws(
        df, p.r, p.alpha, p.s, p.beta, n_draws=J, seed=seed + 3)
    pred_hyp = spp_predict(lam2, mu2, tau2, Tcal, HORIZON, np.random.default_rng(seed + 4))

    # (3) true_indiv: pure counting noise around each customer's true (lambda_i, tau_i)
    lam_t = np.tile(df["lambda_true"].to_numpy(float), (J, 1))
    tau_t = np.tile(df["tau_true"].to_numpy(float), (J, 1))
    pred_ind = spp_predict(lam_t, None, tau_t, Tcal, HORIZON, np.random.default_rng(seed + 5))

    n_est, c_est = _score(pred_est, y)
    n_hyp, c_hyp = _score(pred_hyp, y)
    n_ind, c_ind = _score(pred_ind, y)
    return dict(N=N, seed=seed,
                nMAE_est=n_est, nMAE_true_hyper=n_hyp, nMAE_true_indiv=n_ind,
                CRPS_est=c_est, CRPS_true_hyper=c_hyp, CRPS_true_indiv=c_ind)


def main():
    rows = []
    for N in N_GRID:
        t = time.time()
        for seed in range(SEEDS):
            rows.append(one(N, 700 + seed))
        print(f"[N={N}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)
    raw = pd.DataFrame(rows)

    g = raw.groupby("N").mean(numeric_only=True).drop(columns="seed").reset_index()
    # decomposition (on CRPS, the proper score): fixable vs irreducible
    g["CRPS_fixable"] = g["CRPS_est"] - g["CRPS_true_hyper"]       # ~ O(1/N), estimation error
    g["CRPS_individual"] = g["CRPS_true_hyper"] - g["CRPS_true_indiv"]  # O(1) individual posterior
    g["CRPS_floor"] = g["CRPS_true_indiv"]                         # pure counting noise
    g.to_csv(RES / "noise_floor_summary.csv", index=False)

    print("\n=== Forecast-error decomposition vs cohort size N (CRPS, mean over seeds) ===")
    print(f"{'N':>6s}{'total(est)':>12s}{'true_hyper':>12s}{'true_indiv':>12s}"
          f"{'fixable':>10s}{'individual':>12s}{'floor':>8s}")
    for _, r in g.iterrows():
        print(f"{int(r.N):>6d}{r.CRPS_est:>12.4f}{r.CRPS_true_hyper:>12.4f}"
              f"{r.CRPS_true_indiv:>12.4f}{r.CRPS_fixable:>10.4f}"
              f"{r.CRPS_individual:>12.4f}{r.CRPS_floor:>8.4f}")
    frac = 100 * g["CRPS_fixable"] / g["CRPS_est"]
    print(f"\nfixable share of total CRPS: "
          + ", ".join(f"N={int(n)}:{f:.1f}%" for n, f in zip(g.N, frac)))
    print(f"[saved] {RES/'noise_floor_summary.csv'}")


if __name__ == "__main__":
    main()
