"""
Phase 2, Step 10 (full): a second structural model under the lens -- Pareto/NBD vs BG/NBD.

For each dataset and many held-out-free full-cohort fits over seeds, score the Pareto/NBD (MCMC)
and BG/NBD (MLE) predictive count distributions with CRPS / randomized-PIT / coverage, and run a
paired Wilcoxon across seeds. Both are structural BTYD models; the question is whether the popular
"easy" BG/NBD calibrates as well as Pareto/NBD.

Saves results/bgnbd_study_summary.csv and prints the headline table.
Run:  python src/run_bgnbd_study.py
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
from estimate import fit_mcmc                                   # noqa: E402
from estimate_bgnbd import fit_bgnbd, bgnbd_predict             # noqa: E402
from score import spp_predict, score_forecast                  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 10
METRICS = ["CRPS", "pit_ks", "cov95"]
ORDER = ["Simulated", "CDNow", "Grocery", "OnlineRetailII", "Dunnhumby"]


def build_providers():
    provs = {"Simulated": lambda seed: (simulate_dataset(
        DatasetParams(0.15, 1.3, 0.08, 1.2, N=1200, T=52.0), rng=np.random.default_rng(seed)), 26)}
    cdnow = elog_to_summary(load_cdnow(), 39, 26)
    grocery = elog_to_summary(load_grocery(), 52, 26)
    provs["CDNow"] = lambda seed, d=cdnow: (d, 26)
    provs["Grocery"] = lambda seed, d=grocery: (d, 26)
    for name in ["OnlineRetailII", "Dunnhumby"]:
        df, h = load_summary(name)
        provs[name] = lambda seed, d=df, hh=h: (d, hh)
    return provs


def main():
    print("Loading...", flush=True)
    providers = build_providers()
    rows = []
    for name, get in providers.items():
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            y = df[f"x_star_{h}"].to_numpy(float)
            Tcal = df["T_cal"].to_numpy(float)
            mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=seed + 1)
            pred_pn = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, h, np.random.default_rng(seed + 2))
            bg = fit_bgnbd(df, seed=seed + 3)
            pred_bg = bgnbd_predict(df, bg, h, n_draws=400, seed=seed + 4)
            for model, pred in [("ParetoNBD", pred_pn), ("BGNBD", pred_bg)]:
                sc = score_forecast(pred, y, np.random.default_rng(seed + 5))
                for metric in METRICS:
                    rows.append(dict(dataset=name, seed=seed, model=model,
                                     metric=metric, value=sc[metric]))
            pd.DataFrame(rows).to_csv(RES / "bgnbd_study_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summary = []
    for (dataset, metric), g in raw.groupby(["dataset", "metric"]):
        w = g.pivot_table(index="seed", columns="model", values="value")
        if "ParetoNBD" not in w or "BGNBD" not in w:
            continue
        pn, bg = w["ParetoNBD"].to_numpy(), w["BGNBD"].to_numpy()
        p = 1.0 if np.allclose(pn - bg, 0) else stats.wilcoxon(pn, bg).pvalue
        summary.append(dict(dataset=dataset, metric=metric, ParetoNBD=pn.mean(),
                            BGNBD=bg.mean(), wilcoxon_p=p))
    sm = pd.DataFrame(summary)
    sm.to_csv(RES / "bgnbd_study_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Structural models: Pareto/NBD vs BG/NBD (mean over seeds, all customers) ===")
    print(f"{'dataset':15s}{'CRPS PN':>10s}{'CRPS BG':>10s}{'sig':>4s} | "
          f"{'PIT-KS PN':>11s}{'PIT-KS BG':>11s}{'sig':>4s}")
    for ds in ORDER:
        c = sm[(sm.dataset == ds) & (sm.metric == "CRPS")]
        k = sm[(sm.dataset == ds) & (sm.metric == "pit_ks")]
        if c.empty:
            continue
        c, k = c.iloc[0], k.iloc[0]
        print(f"{ds:15s}{c.ParetoNBD:>10.3f}{c.BGNBD:>10.3f}{star(c.wilcoxon_p):>4s} | "
              f"{k.ParetoNBD:>11.3f}{k.BGNBD:>11.3f}{star(k.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'bgnbd_study_summary.csv'}")


if __name__ == "__main__":
    main()
