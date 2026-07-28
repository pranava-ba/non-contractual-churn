"""
PIT-histogram figures (the calibration diagnostic).

Under calibration the randomized PIT (Czado, Gneiting & Held 2009) is Uniform(0,1):
a flat histogram. A U-shape = under-dispersed/overconfident; a hump = over-dispersed.
We show, for CDNow, Grocery, and a representative simulated cohort, the PIT for ALL
customers (dominated by the zero mass -> spuriously humped/over-dispersed) vs ACTIVE
customers (the decision-relevant segment -> clearly U-shaped, i.e. under-dispersed).

MCMC and MLE PITs coincide, so we plot MCMC and overlay MLE as a step outline to
show they agree.

Run:  python src/pit_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib                                              # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                               # noqa: E402
from simulate import DatasetParams, simulate_dataset          # noqa: E402
from estimate import fit_mcmc, fit_mle                        # noqa: E402
from score import (spp_predict, conditional_individual_draws,  # noqa: E402
                   randomized_pit)
from empirical import load_cdnow, load_grocery, elog_to_summary  # noqa: E402

FIG = Path(__file__).resolve().parent.parent / "results" / "figures"


def predictive(df, horizon, seed=0):
    """Return (pred_mcmc, pred_mle, y, active) for a summary dataframe."""
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    mle = fit_mle(df, seed=seed + 1)
    mc = fit_mcmc(df, n_draws=4000, burn_in=1500, thin=5, seed=seed + 2)
    lam, mu, tau = conditional_individual_draws(
        df, mle["r"], mle["alpha"], mle["s"], mle["beta"], n_draws=400, seed=seed + 3)
    p_mc = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 10))
    p_ml = spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 11))
    return p_mc, p_ml, y, y > 0


def panel(ax, pit_mc, pit_ml, title):
    bins = np.linspace(0, 1, 11)
    ax.hist(pit_mc, bins=bins, density=True, color="#2c7fb8", alpha=0.75,
            edgecolor="white", label="MCMC")
    # MLE as step outline to show agreement
    h, _ = np.histogram(pit_ml, bins=bins, density=True)
    ax.step(bins, np.append(h, h[-1]), where="post", color="#d95f0e", lw=1.4, label="MLE")
    ax.axhline(1.0, ls="--", c="k", lw=1)
    ax.set_title(title, fontsize=9)
    ax.set_ylim(0, 3.2)
    ax.set_xticks([0, 0.5, 1])


def main():
    rng = np.random.default_rng(0)
    # representative simulated cohort (main-grid-like, N=500)
    p = DatasetParams(0.12, 1.3, 0.08, 1.2, N=500, T=39.0)
    sim = simulate_dataset(p, rng=rng)

    cases = [
        ("CDNow (N=2357)", elog_to_summary(load_cdnow(), 39, 26), 26),
        ("Grocery (N=1525)", elog_to_summary(load_grocery(), 52, 26), 26),
        ("Simulated (N=500)", sim, 26),
    ]

    fig, axes = plt.subplots(len(cases), 2, figsize=(8.5, 9), sharex=True)
    for i, (name, df, h) in enumerate(cases):
        p_mc, p_ml, y, active = predictive(df, h, seed=100 * i)
        for j, (cond, mask) in enumerate([("all customers", slice(None)),
                                          ("active customers", active)]):
            pit_mc = randomized_pit(p_mc[:, mask], y[mask], np.random.default_rng(1))
            pit_ml = randomized_pit(p_ml[:, mask], y[mask], np.random.default_rng(1))
            panel(axes[i, j], pit_mc, pit_ml, f"{name} — {cond}")
            if j == 0:
                axes[i, j].set_ylabel("density")
    axes[0, 0].legend(fontsize=8, loc="upper center")
    for ax in axes[-1, :]:
        ax.set_xlabel("PIT value")
    fig.suptitle("PIT calibration: flat = calibrated, U-shape = under-dispersed\n"
                 "(all-customer PITs are masked by the zero mass; active reveals "
                 "under-dispersion)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG / "fig3_pit_histograms.png"
    fig.savefig(out, dpi=140)
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
