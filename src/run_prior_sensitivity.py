"""
Gap E5: prior-sensitivity analysis for the Bayesian (MCMC) arm.

The headline "MCMC = MLE" null is only as strong as its insensitivity to the prior -- otherwise a
reviewer can attribute the result to a conveniently diffuse choice. The Gibbs sampler
(`estimate.fit_mcmc`) exposes its hyper-priors via the `hyper` dict:
  alpha ~ Gamma(a0, b0),  beta ~ Gamma(c0, d0),  r ~ Gamma(ar, br),  s ~ Gamma(as_, bs).
We re-fit under three deliberately different priors and report the shift in the population posterior
(E[lambda], E[mu]) and, more importantly, in forecast calibration (PIT-KS, coverage, CRPS):

  - vague        : the paper's default (near-flat: 1e-3 rates, unit shapes)
  - informative  : r,s ~ Gamma(4,4) (mean 1, sd 0.5) -- a genuinely informative prior on heterogeneity
  - very_diffuse : even flatter (1e-5 rates, Gamma(0.5,0.5) shapes)

Expectation, given a realistic cohort size: the likelihood dominates and the posterior + forecast
are prior-insensitive -- so the MCMC = MLE null is not a prior artefact.

Saves results/prior_sensitivity_summary.csv; prints the table.

Run:  python src/run_prior_sensitivity.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 5
MCMC_DRAWS = 1500
HORIZON = 26
PRIORS = {
    "vague": {},
    "informative": dict(ar=4.0, br=4.0, as_=4.0, bs=4.0),
    "very_diffuse": dict(a0=1e-5, b0=1e-5, c0=1e-5, d0=1e-5, ar=0.5, br=0.5, as_=0.5, bs=0.5),
}


def _score_one(df, horizon, prior, seed):
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=MCMC_DRAWS, burn_in=500, thin=5, seed=seed, hyper=prior)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 1))
    sc = score_forecast(pred, y, np.random.default_rng(seed + 2))
    ps = mc.pop_summary()
    return dict(E_lambda=ps["E_lambda"], E_mu=ps["E_mu"], r=ps["r"], s=ps["s"],
                CRPS=sc["CRPS"], pit_ks=sc["pit_ks"], cov95=sc["cov95"], nMAE=sc["nMAE"])


def build_cases():
    from simulate import DatasetParams, simulate_dataset
    from empirical import load_cdnow, elog_to_summary
    cdnow = elog_to_summary(load_cdnow(), 39, 26)
    return {
        "Simulated": lambda seed: simulate_dataset(
            DatasetParams(0.15, 1.3, 0.08, 1.2, N=1500, T=52.0), rng=np.random.default_rng(seed)),
        "CDNow": lambda seed, d=cdnow: d,
    }


def main():
    cases = build_cases()
    rows = []
    for name, get in cases.items():
        t = time.time()
        for seed in range(SEEDS):
            df = get(seed)
            for pname, prior in PRIORS.items():
                s = _score_one(df, HORIZON, prior, seed=6000 + seed)
                rows.append(dict(dataset=name, prior=pname, seed=seed, **s))
        print(f"[{name}] {SEEDS} seeds x {len(PRIORS)} priors done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summ = raw.groupby(["dataset", "prior"]).mean(numeric_only=True).drop(columns="seed").reset_index()
    summ.to_csv(RES / "prior_sensitivity_summary.csv", index=False)

    print("\n=== Prior sensitivity: population posterior + forecast calibration (mean over seeds) ===")
    print(f"{'dataset':11s}{'prior':13s}{'E[lam]':>9s}{'E[mu]':>9s}{'r':>7s}{'s':>7s}"
          f"{'CRPS':>8s}{'PIT-KS':>8s}{'cov95':>8s}")
    for name in cases:
        for pname in PRIORS:
            r = summ[(summ.dataset == name) & (summ.prior == pname)].iloc[0]
            print(f"{name:11s}{pname:13s}{r.E_lambda:>9.4f}{r.E_mu:>9.4f}{r.r:>7.3f}{r.s:>7.3f}"
                  f"{r.CRPS:>8.3f}{r.pit_ks:>8.3f}{r.cov95:>8.3f}")
        # spread across priors = robustness measure
        g = summ[summ.dataset == name]
        print(f"{'  -> range across priors:':24s}"
              f"{g.E_lambda.max()-g.E_lambda.min():>9.4f}{g.E_mu.max()-g.E_mu.min():>9.4f}"
              f"{'':7s}{'':7s}{g.CRPS.max()-g.CRPS.min():>8.3f}{g.pit_ks.max()-g.pit_ks.min():>8.3f}")
    print(f"\n[saved] {RES/'prior_sensitivity_summary.csv'}")


if __name__ == "__main__":
    main()
