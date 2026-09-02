"""
Phase 2, Step 11 (rigor): a parameter-adjusted PIT-KS null via the parametric bootstrap.

The paper compares PIT-KS to the naive Kolmogorov-Smirnov critical value 1.36/sqrt(n). But that
assumes a fully-specified null, whereas the predictive is built from *estimated* parameters, so the
true null distribution of PIT-KS is wider (the Lilliefors problem) and the naive critical value is
too small. This re-tests the empirical "detectable" departures against a bootstrap null: fit the
model, simulate many cohorts from the fit, refit and recompute PIT-KS on each, and take the 95th
percentile as the corrected 5% critical value. If the observed PIT-KS no longer exceeds it, the
apparent departure was an artefact of the naive critical value.

Uses the fast MLE plug-in throughout. Run:  python src/run_pit_bootstrap.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset             # noqa: E402
from estimate import fit_mle                                     # noqa: E402
from score import (spp_predict, conditional_individual_draws,    # noqa: E402
                   randomized_pit)
from empirical import load_cdnow, load_grocery, elog_to_summary  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
B = 200


def pit_ks(pit):
    p = np.sort(pit)
    return float(np.max(np.abs(p - np.arange(1, len(p) + 1) / len(p))))


def mle_pit_ks(df, horizon, seed):
    """PIT-KS of the MLE plug-in predictive (all customers)."""
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    mle = fit_mle(df, seed=seed)
    lam, mu, tau = conditional_individual_draws(df, mle["r"], mle["alpha"], mle["s"],
                                                mle["beta"], n_draws=300, seed=seed + 1)
    pred = spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 2))
    return pit_ks(randomized_pit(pred, y, np.random.default_rng(seed + 3))), mle


def main():
    rng = np.random.default_rng(0)
    datasets = [("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26),
                ("Grocery", elog_to_summary(load_grocery(), 52, 26), 26)]
    rows = []
    for name, df, h in datasets:
        t = time.time()
        n = len(df)
        obs, mle = mle_pit_ks(df, h, seed=1)
        # parametric-bootstrap null: simulate from the fitted params, refit, recompute
        El, CVl = mle["E_lambda"], 1.0 / np.sqrt(mle["r"])
        Em, CVm = mle["E_mu"], 1.0 / np.sqrt(mle["s"])
        T_eff = float(np.median(df["T_cal"].to_numpy()) + 90.0 / 7.0)
        boot = []
        for b in range(B):
            sim = simulate_dataset(DatasetParams(El, CVl, Em, CVm, N=n, T=T_eff),
                                   rng=np.random.default_rng(1000 + b))
            ks, _ = mle_pit_ks(sim, h, seed=2000 + b)
            boot.append(ks)
        boot = np.array(boot)
        naive = 1.36 / np.sqrt(n)
        corrected = float(np.quantile(boot, 0.95))
        rows.append(dict(dataset=name, n=n, observed_pit_ks=obs, naive_crit=naive,
                         bootstrap_crit=corrected,
                         exceeds_naive=obs > naive, exceeds_bootstrap=obs > corrected))
        print(f"[{name}] n={n} obs={obs:.4f} naive_crit={naive:.4f} "
              f"bootstrap_crit={corrected:.4f}  ({time.time()-t:.0f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(RES / "pit_bootstrap.csv", index=False)
    print("\n=== Parameter-adjusted PIT-KS null (MLE plug-in) ===")
    for _, r in out.iterrows():
        verdict = ("still detectable" if r.exceeds_bootstrap
                   else "NOT significant once the estimated-parameter correction is applied")
        print(f"  {r.dataset}: observed {r.observed_pit_ks:.4f} vs naive {r.naive_crit:.4f} "
              f"vs bootstrap {r.bootstrap_crit:.4f} -> {verdict}")
    print(f"\n[saved] {RES/'pit_bootstrap.csv'}")


if __name__ == "__main__":
    main()
