"""
Do the two repairs stack? Conformal recalibration on top of the Pareto/GGG timing forecast.

The paper shows the two repairs work independently: post-hoc conformal recalibration (for the count
distribution) and structural Pareto/GGG (for timing). This asks what happens when they are combined
on the same target---applying the distribution-free conformal warp to the Pareto/GGG next-purchase
wait-time predictive. If stacking improves the timing forecast, the combined repair dominates; if not,
the structural fix already captures the available gain and the post-hoc warp adds little on top of it.

For each cohort we fit Pareto/GGG, form the wait-time predictive, learn the conformal warp from a
held-out split's buyers (whose realised next-purchase wait is observed), apply it to the test split,
and score raw GGG vs GGG+conformal on the customers who actually buy next (MdAE, CRPS).

Datasets: simulated regular buyers (k=3), Grocery (GGG wins), CDNow (exponential, GGG ties).
Saves results/timing_stack_summary.csv; prints the table.  Run: python src/run_timing_stack.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams                                   # noqa: E402
from simulate_misspec import simulate_dataset_ggg                    # noqa: E402
from empirical import load_cdnow, load_grocery, elog_to_summary      # noqa: E402
from estimate_ggg import fit_ggg                                     # noqa: E402
from timing import sample_next_purchase_time_pggg, score_timing_forecast  # noqa: E402
from conformal import recalibrate_samples                           # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 8
HORIZON = 26


def _cap_inf(w, cap):
    return np.where(np.isfinite(w), w, cap)


def run_one(df, seed):
    """Return (raw GGG scores, GGG+conformal scores) for next-purchase timing on a held-out split."""
    true_wait = df[f"t_next_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float); tx = df["t_x"].to_numpy(float)
    n = len(df)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_rec = n // 2
    rec, test = np.sort(idx[:n_rec]), np.sort(idx[n_rec:])

    gg = fit_ggg(df, n_draws=1000, burn_in=350, thin=4, seed=seed + 1)
    w = sample_next_purchase_time_pggg(gg.lam, gg.mu, gg.tau, gg.k_draws.mean(), Tcal, tx, seed=seed + 2)

    finite = np.isfinite(true_wait)
    cap = float(true_wait[finite].max() * 5.0) if finite.any() else 100.0
    w_cap = _cap_inf(w, cap)

    # learn the warp from the recal split's buyers (finite realised wait)
    rec_buy = rec[finite[rec]]
    if len(rec_buy) < 20:
        raw = score_timing_forecast(w[:, test], true_wait[test])
        return raw, raw
    w_conf_test = recalibrate_samples(w_cap[:, rec_buy], true_wait[rec_buy], w_cap[:, test], seed=seed + 9)

    raw = score_timing_forecast(w[:, test], true_wait[test])
    conf = score_timing_forecast(w_conf_test, true_wait[test])
    return raw, conf


def build_cases():
    cases = [("Sim-k3", lambda s: simulate_dataset_ggg(
                  DatasetParams(0.15, 1.2, 0.08, 1.0, N=1000, T=52.0), k=3.0,
                  rng=np.random.default_rng(s)))]
    grocery = elog_to_summary(load_grocery(), 52, HORIZON)
    cdnow = elog_to_summary(load_cdnow(), 39, HORIZON)
    cases += [("Grocery", lambda s, d=grocery: d), ("CDNow", lambda s, d=cdnow: d)]
    return cases


def main():
    rows = []
    for name, get in build_cases():
        t = time.time()
        for seed in range(SEEDS):
            raw, conf = run_one(get(14000 + seed), seed=14000 + seed)
            for metric in ("timing_MdAE", "timing_CRPS"):
                rows.append(dict(dataset=name, seed=seed, metric=metric,
                                 GGG=raw[metric], GGG_conf=conf[metric]))
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summ = []
    for (dataset, metric), g in raw.groupby(["dataset", "metric"]):
        a, b = g["GGG"].to_numpy(), g["GGG_conf"].to_numpy()
        pval = 1.0 if np.allclose(a - b, 0) else stats.wilcoxon(a, b).pvalue
        summ.append(dict(dataset=dataset, metric=metric, GGG=a.mean(), GGG_conf=b.mean(), wilcoxon_p=pval))
    sm = pd.DataFrame(summ)
    sm.to_csv(RES / "timing_stack_summary.csv", index=False)

    def star(p): return "***" if p < 1e-3 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print("\n=== Stacking the repairs: Pareto/GGG vs Pareto/GGG + conformal (timing) ===")
    print(f"{'dataset':10s}{'MdAE GGG':>10s}{'+conf':>8s}{'sig':>4s} | {'CRPS GGG':>10s}{'+conf':>8s}{'sig':>4s}")
    for ds in [c[0] for c in build_cases()]:
        m = sm[(sm.dataset == ds) & (sm.metric == "timing_MdAE")]
        c = sm[(sm.dataset == ds) & (sm.metric == "timing_CRPS")]
        if m.empty:
            continue
        m, c = m.iloc[0], c.iloc[0]
        print(f"{ds:10s}{m.GGG:>10.2f}{m.GGG_conf:>8.2f}{star(m.wilcoxon_p):>4s} | "
              f"{c.GGG:>10.2f}{c.GGG_conf:>8.2f}{star(c.wilcoxon_p):>4s}")
    print(f"\n[saved] {RES/'timing_stack_summary.csv'}")


if __name__ == "__main__":
    main()
