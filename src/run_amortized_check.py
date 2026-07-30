"""
Phase 2, Step 6 (confirmation): multi-cohort check that amortized neural inference matches MCMC.

Train the amortizer once, then evaluate MCMC vs. the amortized plug-in on many held-out simulated
cohorts (paired Wilcoxon across cohorts) plus the real datasets. Saves results/amortized_summary.csv.

Run:  python src/run_amortized_check.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset            # noqa: E402
from empirical import load_cdnow, load_grocery, elog_to_summary  # noqa: E402
from datasets import load_summary                               # noqa: E402
from amortized import generate_training_data, fit_amortizer, compare_amortized_vs_mcmc  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
N_HELDOUT = 25


def main():
    print("Training amortizer...", flush=True)
    t = time.time()
    X, Y = generate_training_data(n_cohorts=4000, seed=0)
    am = fit_amortizer(X, Y, seed=0)
    print(f"  trained in {time.time()-t:.0f}s", flush=True)

    # held-out simulated cohorts (drawn from the same ranges, different seeds)
    rng = np.random.default_rng(777)
    held = {"MCMC": {"CRPS": [], "pit_ks": []}, "Amortized": {"CRPS": [], "pit_ks": []}}
    for k in range(N_HELDOUT):
        p = DatasetParams(rng.uniform(.02, .3), rng.uniform(.5, 2.5), rng.uniform(.02, .2),
                          rng.uniform(.5, 2.5), N=int(rng.integers(300, 1500)), T=float(rng.uniform(26, 72)))
        df = simulate_dataset(p, rng=rng)
        res = compare_amortized_vs_mcmc(df, 26, am, seed=5000 + k)
        for method in ["MCMC", "Amortized"]:
            for m in ["CRPS", "pit_ks"]:
                held[method][m].append(res[(method, "all")][m])
        print(f"  held-out cohort {k+1}/{N_HELDOUT}", flush=True)

    rows = []
    print("\n=== Held-out simulated cohorts (n=%d), MCMC vs Amortized (all customers) ===" % N_HELDOUT)
    for m in ["CRPS", "pit_ks"]:
        a = np.array(held["MCMC"][m]); b = np.array(held["Amortized"][m])
        p = stats.wilcoxon(a, b).pvalue if not np.allclose(a, b) else 1.0
        print(f"  {m:7s}  MCMC {a.mean():.3f}±{a.std():.3f}   Amortized {b.mean():.3f}±{b.std():.3f}"
              f"   Wilcoxon p={p:.3f}")
        rows.append(dict(dataset="HeldoutSim", metric=m, MCMC=a.mean(), Amortized=b.mean(), wilcoxon_p=p))

    # real datasets (single evaluation each)
    reals = [("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26),
             ("Grocery", elog_to_summary(load_grocery(), 52, 26), 26),
             ("OnlineRetailII", *load_summary("OnlineRetailII")),
             ("Dunnhumby", *load_summary("Dunnhumby"))]
    print("\n=== Real datasets ===")
    for name, df, h in reals:
        res = compare_amortized_vs_mcmc(df, h, am, seed=1)
        for m in ["CRPS", "pit_ks"]:
            mc = res[("MCMC", "all")][m]; a = res[("Amortized", "all")][m]
            rows.append(dict(dataset=name, metric=m, MCMC=mc, Amortized=a, wilcoxon_p=np.nan))
        print(f"  {name:15s} PIT-KS MCMC {res[('MCMC','all')]['pit_ks']:.3f} "
              f"Amortized {res[('Amortized','all')]['pit_ks']:.3f}")

    pd.DataFrame(rows).to_csv(RES / "amortized_summary.csv", index=False)
    print(f"\n[saved] {RES/'amortized_summary.csv'}")


if __name__ == "__main__":
    main()
