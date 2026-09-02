"""
Generate the ADDED tables/numbers for the expanded Springer-Nature manuscript, all from
already-computed result CSVs (no new experiments). Prints LaTeX tabular bodies and the
equivalence-test (TOST) figures to stdout for inlining into the single-file sn-jnl .tex.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RES = Path(__file__).resolve().parent.parent / "results"
main = pd.read_csv(RES / "main_results.csv")
extreme = pd.read_csv(RES / "extreme_results.csv")


def sep(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# ---- 1. per-horizon estimator tables (T*=13 and 52) ------------------------------
def estimator_horizon(h):
    d = main[main.horizon == h]
    print(f"\n% --- T*={h}: cov95(all) | cov95(active) | CRPS(active), MCMC vs MLE ---")
    for N, g in d.groupby("N"):
        def m(cond, meth, col):
            return g[(g["cond"] == cond) & (g.method == meth)][col].mean()
        print(f"{N} & {m('all','MCMC','cov95'):.3f} & {m('all','MLE_plugin','cov95'):.3f} & "
              f"{m('active','MCMC','cov95'):.3f} & {m('active','MLE_plugin','cov95'):.3f} & "
              f"{m('active','MCMC','CRPS'):.3f} & {m('active','MLE_plugin','CRPS'):.3f} \\\\")


# ---- 2. sharpness (mean predictive SD) T*=26 -------------------------------------
def sharpness():
    d = main[main.horizon == 26]
    print("\n% --- Sharpness (mean predictive std), T*=26; all | active ---")
    print("% N & MCMC_all & MLE_all & heur_all & MCMC_act & MLE_act & heur_act")
    for N, g in d.groupby("N"):
        def sh(cond, meth):
            v = g[(g["cond"] == cond) & (g.method == meth)]["sharpness_std"]
            return v.mean() if len(v) else float("nan")
        print(f"{N} & {sh('all','MCMC'):.3f} & {sh('all','MLE_plugin'):.3f} & {sh('all','heuristic'):.3f} & "
              f"{sh('active','MCMC'):.3f} & {sh('active','MLE_plugin'):.3f} & {sh('active','heuristic'):.3f} \\\\")


# ---- 3. point-error sanity (Simon's own metrics), T*=26 pooled -------------------
def point_error():
    d = main[main.horizon == 26]
    print("\n% --- Point error (Simon's metrics), pooled mean over 90 cohorts, T*=26 ---")
    print("% method & cond & nMAE & nRMSE & nMdAE")
    for meth in ["MCMC", "MLE_plugin", "heuristic"]:
        for cond in ["all", "active"]:
            g = d[(d.method == meth) & (d["cond"] == cond)]
            print(f"{meth} & {cond} & {g.nMAE.mean():.3f} & {g.nRMSE.mean():.3f} & {g.nMdAE.mean():.3f} \\\\")


# ---- 4. extreme grid, T*=26 ------------------------------------------------------
def extreme_tab():
    d = extreme[extreme.horizon == 26]
    print("\n% --- Extreme grid (small N, high CV), T*=26: cov95(all/act), CRPS(act) MCMC vs MLE ---")
    for N, g in d.groupby("N"):
        def m(cond, meth, col):
            return g[(g["cond"] == cond) & (g.method == meth)][col].mean()
        print(f"{N} & {m('all','MCMC','cov95'):.3f} & {m('all','MLE_plugin','cov95'):.3f} & "
              f"{m('active','MCMC','cov95'):.3f} & {m('active','MLE_plugin','cov95'):.3f} & "
              f"{m('active','MCMC','CRPS'):.3f} & {m('active','MLE_plugin','CRPS'):.3f} \\\\")


# ---- 5. TOST equivalence, MCMC vs MLE_plugin, T*=26 ------------------------------
def tost():
    d = main[main.horizon == 26]
    sep("EQUIVALENCE (TOST) — MCMC vs MLE_plugin, paired across cohorts, T*=26")
    print(f"{'metric':16s}{'cond':8s}{'n':>4s}{'meanDiff':>10s}{'95% CI':>20s}"
          f"{'90% CI':>20s}{'SD(metric)':>12s}")
    for metric in ["CRPS", "cov95", "cov50", "nMAE"]:
        for cond in ["all", "active"]:
            w = (d[(d["cond"] == cond) & (d.method.isin(["MCMC", "MLE_plugin"]))]
                 .pivot_table(index=["N", "T", "rep"], columns="method", values=metric).dropna())
            diff = (w["MCMC"] - w["MLE_plugin"]).values
            nramp = len(diff); mean = diff.mean(); se = diff.std(ddof=1) / np.sqrt(nramp)
            t95 = stats.t.ppf(0.975, nramp - 1) * se
            t90 = stats.t.ppf(0.95, nramp - 1) * se
            sd_metric = pd.concat([w["MCMC"], w["MLE_plugin"]]).std(ddof=1)
            print(f"{metric:16s}{cond:8s}{nramp:>4d}{mean:>+10.4f}"
                  f"{f'[{mean-t95:+.4f},{mean+t95:+.4f}]':>20s}"
                  f"{f'[{mean-t90:+.4f},{mean+t90:+.4f}]':>20s}{sd_metric:>12.4f}")
    print("\nInterpretation: for TOST at margin d, equivalence holds if the 90% CI lies "
          "within (-d, +d). Suggested principled margins: coverage d=0.01 (1 pp, below "
          "sampling noise); CRPS d = 2% of grand-mean CRPS.")
    for cond in ["all", "active"]:
        gm = d[(d["cond"] == cond) & (d.method == "MCMC")]["CRPS"].mean()
        print(f"   grand-mean CRPS ({cond}) = {gm:.3f}  ->  2% margin d = {0.02*gm:.4f}")


if __name__ == "__main__":
    sep("1. ESTIMATOR TABLE, T*=13 and T*=52")
    estimator_horizon(13); estimator_horizon(52)
    sep("2. SHARPNESS, T*=26"); sharpness()
    sep("3. POINT-ERROR SANITY, T*=26"); point_error()
    sep("4. EXTREME GRID, T*=26"); extreme_tab()
    tost()
