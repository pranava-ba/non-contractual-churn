"""
Gap F4: sensitivity of the active-customer task to the *definition* of "active" and the planning
horizon.

Simon (2025)'s key methodological move is to redefine an "active" customer as one who *purchases
within a validation window* (the planning horizon), rather than by the unobservable P(alive at T)
used by the classical literature. Her argument is that P(alive) is neither practically meaningful
(an alive customer who never buys in the planning horizon is not "active" to a manager) nor
validatable on real data. This study makes that argument quantitative on simulated cohorts, where
BOTH definitions are observable (we know the true dropout time tau_i):

  - Definition A (purchase-in-window): active_i = (x*_h > 0)             [Simon; validatable]
  - Definition B (alive-at-T):         active_i = (tau_i > T_cal)        [classical; unobservable]

For each horizon h in {13, 26, 52} we report (i) the calibration (ECE) of the model's implied
probability for each target, (ii) how far the two definitions AGREE, and (iii) the classification
sensitivity/precision of the validatable target. The headline: the two definitions diverge most at
short horizons -- P(alive) over-counts "active" because many alive customers don't buy soon -- and
the gap shrinks as the horizon lengthens.

Saves results/active_def_summary.csv; prints the table.

Run:  python src/run_active_def_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset            # noqa: E402
from churn import ece                                           # noqa: E402

HORIZONS = [13, 26, 52]
SEEDS = 6
BEHAVIOUR = dict(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, N=1500, T=52.0)


def _sens_prec(p_active, truth, thr=0.5):
    pred = p_active >= thr
    tp = np.sum(pred & truth)
    sens = tp / max(truth.sum(), 1)                       # recall on the truly active
    prec = tp / max(pred.sum(), 1)
    return float(sens), float(prec)


def one(seed, mcmc_draws=1500):
    from estimate import fit_mcmc
    from score import spp_predict

    df = simulate_dataset(DatasetParams(**BEHAVIOUR), rng=np.random.default_rng(seed))
    Tcal = df["T_cal"].to_numpy(float)
    alive = df["alive_at_T"].to_numpy(bool)               # Definition B truth (unobservable IRL)

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    p_alive = (mc.tau > Tcal[None, :]).mean(axis=0)       # model P(alive at T)

    rows = []
    for h in HORIZONS:
        y = df[f"x_star_{h}"].to_numpy(float)
        active_A = y > 0                                  # Definition A truth (validatable)
        pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, h, np.random.default_rng(seed + h))
        p_active = (pred > 0).mean(axis=0)                # model P(purchase in window)

        ece_A = ece(p_active, active_A.astype(float))     # calibration of the validatable target
        ece_B = ece(p_alive, alive.astype(float))         # calibration of the classical target
        agree = float(np.mean(active_A == alive))         # do the two definitions coincide?
        over = float(np.mean(alive & ~active_A))          # alive but NOT purchasing in window
        sens, prec = _sens_prec(p_active, active_A)
        rows.append(dict(seed=seed, horizon=h, active_rate_A=float(active_A.mean()),
                         alive_rate_B=float(alive.mean()), ece_A=ece_A, ece_B=ece_B,
                         AB_agreement=agree, alive_not_active=over, sensitivity=sens, precision=prec))
    return rows


def main():
    rows = []
    t = time.time()
    for seed in range(SEEDS):
        rows.extend(one(700 + seed))
    raw = pd.DataFrame(rows)
    summ = raw.groupby("horizon").mean(numeric_only=True).drop(columns="seed").reset_index()
    summ.to_csv(Path(RES := Path(__file__).resolve().parent.parent / "results") / "active_def_summary.csv",
                index=False)

    print(f"Active-customer DEFINITION sensitivity (simulated, {SEEDS} seeds, {time.time()-t:.0f}s)\n")
    print(f"{'horizon':>8s}{'act.rate_A':>11s}{'alive_B':>9s}{'ECE_A':>8s}{'ECE_B':>8s}"
          f"{'A=B agree':>11s}{'alive!buy':>10s}{'sens_A':>8s}{'prec_A':>8s}")
    for _, r in summ.iterrows():
        print(f"{int(r.horizon):>8d}{r.active_rate_A:>11.3f}{r.alive_rate_B:>9.3f}"
              f"{r.ece_A:>8.3f}{r.ece_B:>8.3f}{r.AB_agreement:>11.3f}"
              f"{r.alive_not_active:>10.3f}{r.sensitivity:>8.3f}{r.precision:>8.3f}")
    print("\nRead: A = purchase-in-window (validatable), B = alive-at-T (classical, unobservable).")
    print("'alive!buy' = fraction alive at T but NOT buying within the horizon -- the customers the")
    print("classical P(alive) definition mislabels as active. It shrinks as the horizon lengthens.")
    print(f"[saved] {RES/'active_def_summary.csv'}")


if __name__ == "__main__":
    main()
