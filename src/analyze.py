"""
Aggregate the study results, run paired significance tests, and make figures.

Reads results/main_results.csv (+ optionally extreme_results.csv), then:
  - prints aggregate tables (coverage, CRPS, sharpness, PIT-KS) by N x method x cond
  - runs paired Wilcoxon signed-rank tests across matched datasets for the key
    comparisons (MCMC vs MLE_boot -> does the estimator matter?; MCMC vs heuristic
    -> does the model matter?), with Benjamini-Hochberg FDR control
  - saves figures to results/figures/

Robust to partial CSVs, so it can be run on in-progress runs.
Run:  python src/analyze.py            (main grid)
      python src/analyze.py --extreme  (include extreme grid)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RES = Path(__file__).resolve().parent.parent / "results"
FIG = RES / "figures"
FIG.mkdir(exist_ok=True)
METHOD_ORDER = ["MCMC", "MLE_plugin", "MLE_boot", "heuristic"]


def load(include_extreme=False):
    frames = []
    p = RES / "main_results.csv"
    if p.exists():
        d = pd.read_csv(p); d["grid"] = "main"; frames.append(d)
    if include_extreme and (RES / "extreme_results.csv").exists():
        d = pd.read_csv(RES / "extreme_results.csv"); d["grid"] = "extreme"; frames.append(d)
    if not frames:
        raise SystemExit("no results CSVs found yet")
    return pd.concat(frames, ignore_index=True)


def agg_table(df, horizon, metric, cond):
    s = df[(df.horizon == horizon) & (df["cond"] == cond)]
    piv = s.pivot_table(index="N", columns="method", values=metric, aggfunc="mean")
    cols = [m for m in METHOD_ORDER if m in piv.columns]
    return piv[cols].round(3)


def paired_wilcoxon(df, metric, m1, m2, cond, horizon):
    """Paired test of m1 vs m2 on `metric`, matched by dataset (N,T,rep)."""
    s = df[(df["cond"] == cond) & (df.horizon == horizon) & (df.method.isin([m1, m2]))]
    wide = s.pivot_table(index=["N", "T", "rep"], columns="method", values=metric)
    wide = wide.dropna(subset=[m1, m2])
    if len(wide) < 6:
        return dict(n=len(wide), p=np.nan, median_diff=np.nan)
    diff = wide[m1] - wide[m2]
    if np.allclose(diff, 0):
        return dict(n=len(wide), p=1.0, median_diff=0.0)
    stat, p = stats.wilcoxon(wide[m1], wide[m2])
    return dict(n=len(wide), p=float(p), median_diff=float(diff.median()))


def bh(pvals):
    """Benjamini-Hochberg FDR-adjusted p-values."""
    p = np.asarray(pvals, float); m = np.isfinite(p).sum()
    order = np.argsort(np.where(np.isfinite(p), p, np.inf))
    adj = np.full_like(p, np.nan)
    prev = 1.0
    for rank, idx in enumerate(order[::-1]):
        if not np.isfinite(p[idx]):
            continue
        k = m - rank
        prev = min(prev, p[idx] * m / k)
        adj[idx] = prev
    return adj


def run_tests(df, horizon=26):
    rows = []
    present = set(df.method.unique())
    comparisons = [c for c in [("MCMC", "MLE_boot", "estimator effect"),
                               ("MCMC", "MLE_plugin", "param-uncertainty effect"),
                               ("MCMC", "heuristic", "model-vs-heuristic")]
                   if c[0] in present and c[1] in present]
    for metric in ["CRPS", "cov95", "cov50"]:
        for cond in ["all", "active"]:
            for m1, m2, label in comparisons:
                r = paired_wilcoxon(df, metric, m1, m2, cond, horizon)
                rows.append(dict(metric=metric, cond=cond, comparison=f"{m1} vs {m2}",
                                 label=label, **r))
    out = pd.DataFrame(rows)
    out["p_bh"] = bh(out["p"].values)
    return out


def make_figures(df, horizon=26):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = [m for m in METHOD_ORDER if m in df.method.unique()]
    colors = {"MCMC": "#2c7fb8", "MLE_plugin": "#41b6c4",
              "MLE_boot": "#7fcdbb", "heuristic": "#d95f0e"}

    # Fig 1: 95% coverage vs N, all vs active
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, cond in zip(axes, ["all", "active"]):
        for m in methods:
            piv = agg_table(df, horizon, "cov95", cond)
            if m in piv.columns:
                ax.plot(piv.index, piv[m], "-o", label=m, color=colors.get(m))
        ax.axhline(0.95, ls="--", c="k", lw=1, label="nominal 0.95")
        ax.set_title(f"95% interval coverage — {cond} customers")
        ax.set_xlabel("cohort size N"); ax.set_xscale("log")
    axes[0].set_ylabel("empirical coverage"); axes[0].legend(fontsize=8)
    fig.suptitle(f"Calibration of Pareto/NBD purchase forecasts (T*={horizon})")
    fig.tight_layout()
    fig.savefig(FIG / "fig1_coverage_vs_N.png", dpi=140)
    fig.savefig(FIG / "fig1_coverage_vs_N.pdf")
    fig.savefig(FIG / "fig1_coverage_vs_N.eps")
    plt.close(fig)

    # Fig 2: CRPS vs N (active), model vs heuristic
    fig, ax = plt.subplots(figsize=(6, 4.2))
    for m in methods:
        piv = agg_table(df, horizon, "CRPS", "active")
        if m in piv.columns:
            ax.plot(piv.index, piv[m], "-o", label=m, color=colors.get(m))
    ax.set_title(f"CRPS on active customers (T*={horizon}, lower=better)")
    ax.set_xlabel("cohort size N"); ax.set_ylabel("CRPS"); ax.set_xscale("log")
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(FIG / "fig2_crps_vs_N.png", dpi=140)
    fig.savefig(FIG / "fig2_crps_vs_N.pdf")
    fig.savefig(FIG / "fig2_crps_vs_N.eps")
    plt.close(fig)
    print(f"[figures] saved PNG, PDF, and EPS to {FIG}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extreme", action="store_true")
    ap.add_argument("--horizon", type=int, default=26)
    args = ap.parse_args()
    df = load(include_extreme=args.extreme)
    h = args.horizon
    print(f"loaded {len(df)} rows | designs N={sorted(df.N.unique())} | "
          f"reps/design~{df.groupby('N').rep.nunique().to_dict()}\n")

    for cond in ["all", "active"]:
        for metric in ["cov95", "cov50", "CRPS"]:
            print(f"=== {metric}  ({cond}, T*={h}) ===")
            print(agg_table(df, h, metric, cond).to_string(), "\n")

    print("=== Paired Wilcoxon tests (BH-adjusted), T*=%d ===" % h)
    tests = run_tests(df, h)
    with pd.option_context("display.width", 200):
        print(tests.round(4).to_string(index=False))
    tests.to_csv(RES / "significance_tests.csv", index=False)
    make_figures(df, h)


if __name__ == "__main__":
    main()
