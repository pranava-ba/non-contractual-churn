"""Emit LaTeX table bodies for the Phase 2 manuscript from results/*_summary.csv.

Every number in the paper's tables is produced here and pasted verbatim, so each is
traceable to a confirmed multi-seed study. Run:  python src/make_phase2_tables.py
"""
from __future__ import annotations

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")

ORDER7 = ["Simulated", "CDNow", "Grocery", "Olist", "Ta-Feng", "Dunnhumby", "OnlineRetailII"]
NAME = {"OnlineRetailII": "Online Retail II", "Ta-Feng": "Ta-Feng"}


def load(n):
    return pd.read_csv(os.path.join(RESULTS, n))


def nm(d):
    return NAME.get(d, d)


def p(v):
    if pd.isna(v):
        return "--"
    return "$<$0.001" if v < 0.001 else f"{v:.3f}"


def b(x, best):
    return f"\\textbf{{{x:.3f}}}" if best else f"{x:.3f}"


def tab_counts():
    df = load("ml_study_summary.csv")
    d = df[(df.cond == "all") & (df.metric == "pit_ks")]
    piv = d.pivot_table(index="dataset", columns="method", values="mean")
    cols = ["BTYD", "PoissonGBM", "HurdleGBM", "QuantileGBM"]
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Predictive calibration of purchase-count forecasts (PIT--KS, lower is better; "
          r"mean over 15 seeds). Best per row in bold. Datasets ordered by BTYD calibration.}"
          r"\label{tab:counts}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cccc@{}}")
    print(r"\toprule")
    print(r"Dataset & BTYD & Poisson-GBM & Hurdle-GBM & Quantile-GBM \\")
    print(r"\midrule")
    for ds in sorted(piv.index, key=lambda z: piv.loc[z, "BTYD"]):
        row = piv.loc[ds]
        best = row[cols].idxmin()
        cells = " & ".join(b(row[c], c == best) for c in cols)
        print(f"{nm(ds)} & {cells} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_conformal():
    df = load("conformal_study_summary.csv")
    d = df[(df.cond == "all") & (df.metric == "pit_ks")].sort_values("raw_mean")
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Conformalized BTYD: PIT--KS before and after a single held-out isotonic "
          r"recalibration (mean over 15 seeds; $p$ from paired Wilcoxon).}\label{tab:conformal}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l ccc@{}}")
    print(r"\toprule")
    print(r"Dataset & BTYD (raw) & Conformalized & $p$ \\")
    print(r"\midrule")
    for _, r in d.iterrows():
        print(f"{nm(r.dataset)} & {r.raw_mean:.3f} & {r.recal_mean:.3f} & {p(r.wilcoxon_p)} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_clv():
    df = load("clv_study_summary.csv")
    d = df[df.cond == "all"]
    order = ["OnlineRetailII", "Ta-Feng", "Dunnhumby"]
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Probabilistic CLV on the monetary target: Pareto/NBD${}+{}$Gamma-Gamma "
          r"versus a deep zero-inflated-lognormal (ZILN) model (mean over 15 seeds).}\label{tab:clv}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cc cc cc@{}}")
    print(r"\toprule")
    print(r"& \multicolumn{2}{@{}c@{}}{PIT--KS} & \multicolumn{2}{@{}c@{}}{nMAE} "
          r"& \multicolumn{2}{@{}c@{}}{cov$_{95}$}\\")
    print(r"\cmidrule{2-3}\cmidrule{4-5}\cmidrule{6-7}")
    print(r"Dataset & GG & ZILN & GG & ZILN & GG & ZILN \\")
    print(r"\midrule")
    for ds in order:
        ks = d[(d.dataset == ds) & (d.metric == "pit_ks")].iloc[0]
        ma = d[(d.dataset == ds) & (d.metric == "nMAE")].iloc[0]
        cv = d[(d.dataset == ds) & (d.metric == "cov95")].iloc[0]
        print(f"{nm(ds)} & {ks.BTYD_GG_mean:.3f} & {ks.ZILN_mean:.3f} & "
              f"{ma.BTYD_GG_mean:.3f} & {ma.ZILN_mean:.3f} & "
              f"{cv.BTYD_GG_mean:.3f} & {cv.ZILN_mean:.3f} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_churn():
    df = load("churn_study_summary.csv")
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Churn probability $P(\text{active})$: expected calibration error (ECE) and "
          r"Brier score, BTYD versus an ML classifier (mean over 15 seeds).}\label{tab:churn}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cc cc@{}}")
    print(r"\toprule")
    print(r"& \multicolumn{2}{@{}c@{}}{ECE} & \multicolumn{2}{@{}c@{}}{Brier}\\")
    print(r"\cmidrule{2-3}\cmidrule{4-5}")
    print(r"Dataset & BTYD & ML & BTYD & ML \\")
    print(r"\midrule")
    for ds in ORDER7:
        e = df[(df.dataset == ds) & (df.metric == "ece")]
        br = df[(df.dataset == ds) & (df.metric == "brier")]
        if len(e) == 0:
            continue
        e = e.iloc[0]
        br = br.iloc[0]
        print(f"{nm(ds)} & {e.BTYD:.3f} & {e.ML:.3f} & {br.BTYD:.3f} & {br.ML:.3f} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_variant():
    df = load("bgnbd_study_summary.csv")
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Model variant is immaterial: Pareto/NBD versus BG/NBD "
          r"(mean over 10 seeds).}\label{tab:variant}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cc cc@{}}")
    print(r"\toprule")
    print(r"& \multicolumn{2}{@{}c@{}}{PIT--KS} & \multicolumn{2}{@{}c@{}}{CRPS}\\")
    print(r"\cmidrule{2-3}\cmidrule{4-5}")
    print(r"Dataset & Pareto/NBD & BG/NBD & Pareto/NBD & BG/NBD \\")
    print(r"\midrule")
    for ds in ["Simulated", "CDNow", "Grocery", "Dunnhumby", "OnlineRetailII"]:
        ks = df[(df.dataset == ds) & (df.metric == "pit_ks")]
        cr = df[(df.dataset == ds) & (df.metric == "CRPS")]
        if len(ks) == 0:
            continue
        ks = ks.iloc[0]
        cr = cr.iloc[0]
        print(f"{nm(ds)} & {ks.ParetoNBD:.3f} & {ks.BGNBD:.3f} & "
              f"{cr.ParetoNBD:.3f} & {cr.BGNBD:.3f} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_timing():
    df = load("timing_study_summary.csv")
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Next-purchase-timing forecast, Pareto/NBD versus Pareto/GGG: median absolute "
          r"error and CRPS of the predicted time to next purchase (12 seeds; $p$ paired Wilcoxon).}"
          r"\label{tab:timing}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cc c cc c@{}}")
    print(r"\toprule")
    print(r"& \multicolumn{2}{@{}c@{}}{MdAE} & & \multicolumn{2}{@{}c@{}}{CRPS} &\\")
    print(r"\cmidrule{2-3}\cmidrule{5-6}")
    print(r"Dataset & Pareto/NBD & Pareto/GGG & $p$ & Pareto/NBD & Pareto/GGG & $p$ \\")
    print(r"\midrule")
    order = ["Sim-k1", "Sim-k2", "Sim-k3", "Grocery", "CDNow"]
    for ds in order:
        md = df[(df.dataset == ds) & (df.metric == "timing_MdAE")]
        cr = df[(df.dataset == ds) & (df.metric == "timing_CRPS")]
        if len(md) == 0:
            continue
        md = md.iloc[0]
        cr = cr.iloc[0]
        print(f"{ds} & {md.PNBD:.2f} & {md.GGG:.2f} & {p(md.wilcoxon_p)} & "
              f"{cr.PNBD:.2f} & {cr.GGG:.2f} & {p(cr.wilcoxon_p)} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_amortized():
    df = load("amortized_summary.csv")
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Amortized neural inference versus MCMC: CRPS and PIT--KS. "
          r"HeldoutSim is 25 held-out simulated cohorts ($p$ paired Wilcoxon over cohorts).}"
          r"\label{tab:amortized}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cc c cc@{}}")
    print(r"\toprule")
    print(r"& \multicolumn{2}{@{}c@{}}{CRPS} & & \multicolumn{2}{@{}c@{}}{PIT--KS}\\")
    print(r"\cmidrule{2-3}\cmidrule{5-6}")
    print(r"Dataset & MCMC & Amortized & $p$(CRPS) & MCMC & Amortized \\")
    print(r"\midrule")
    for ds in ["HeldoutSim", "CDNow", "Grocery", "OnlineRetailII", "Dunnhumby"]:
        cr = df[(df.dataset == ds) & (df.metric == "CRPS")].iloc[0]
        ks = df[(df.dataset == ds) & (df.metric == "pit_ks")].iloc[0]
        print(f"{nm(ds)} & {cr.MCMC:.3f} & {cr.Amortized:.3f} & {p(cr.wilcoxon_p)} & "
              f"{ks.MCMC:.3f} & {ks.Amortized:.3f} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_counts_accuracy():
    """CRPS and nMAE for the four count forecasters (accuracy/sharpness companion)."""
    df = load("ml_study_summary.csv")
    methods = ["BTYD", "PoissonGBM", "HurdleGBM", "QuantileGBM"]
    crps = df[(df.cond == "all") & (df.metric == "CRPS")].pivot_table(
        index="dataset", columns="method", values="mean").reindex(columns=methods)
    mae = df[(df.cond == "all") & (df.metric == "nMAE")].pivot_table(
        index="dataset", columns="method", values="mean").reindex(columns=methods)
    order = sorted(crps.index, key=lambda z: load("ml_study_summary.csv")
                   .query("cond=='all' and metric=='pit_ks' and dataset==@z and method=='BTYD'")
                   ["mean"].iloc[0])
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Accuracy and sharpness of purchase-count forecasts: CRPS (lower is sharper "
          r"subject to calibration) and normalised MAE, mean over 15 seeds. Best per block in bold.}"
          r"\label{tab:counts-acc}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cccc c cccc@{}}")
    print(r"\toprule")
    print(r"& \multicolumn{4}{@{}c@{}}{CRPS} & & \multicolumn{4}{@{}c@{}}{nMAE}\\")
    print(r"\cmidrule{2-5}\cmidrule{7-10}")
    print(r"Dataset & BTYD & Pois. & Hur. & Quant. & & BTYD & Pois. & Hur. & Quant. \\")
    print(r"\midrule")
    for ds in order:
        cr, ma = crps.loc[ds], mae.loc[ds]
        bc, bm = cr[methods].idxmin(), ma[methods].idxmin()
        cc = " & ".join(b(cr[m], m == bc) for m in methods)
        mc = " & ".join(b(ma[m], m == bm) for m in methods)
        print(f"{nm(ds)} & {cc} & & {mc} \\\\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_coverage():
    """95% interval coverage for the four count forecasters (nominal 0.95)."""
    df = load("ml_study_summary.csv")
    methods = ["BTYD", "PoissonGBM", "HurdleGBM", "QuantileGBM"]
    piv = df[(df.cond == "all") & (df.metric == "cov95")].pivot_table(
        index="dataset", columns="method", values="mean").reindex(columns=methods)
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Empirical coverage of nominal 95\% predictive intervals for purchase counts "
          r"(closest to 0.95 is best), mean over 15 seeds.}\label{tab:coverage}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cccc@{}}")
    print(r"\toprule")
    print(r"Dataset & BTYD & Poisson-GBM & Hurdle-GBM & Quantile-GBM \\")
    print(r"\midrule")
    for ds in ORDER7:
        if ds not in piv.index:
            continue
        r = piv.loc[ds]
        print(f"{nm(ds)} & " + " & ".join(f"{r[m]:.3f}" for m in methods) + r" \\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


def tab_counts_xpos():
    """PIT-KS under forecast-time conditioning (x>0): the repeat-buyer subgroup."""
    df = load("ml_study_summary.csv")
    d = df[(df.cond == "x>0") & (df.metric == "pit_ks")]
    methods = ["BTYD", "PoissonGBM", "HurdleGBM", "QuantileGBM"]
    piv = d.pivot_table(index="dataset", columns="method", values="mean").reindex(columns=methods)
    print(r"\begin{table}[htbp]\centering")
    print(r"\caption{Calibration (PIT--KS) on the repeat-buyer subgroup, conditioning at forecast "
          r"time on $x>0$, mean over 15 seeds. Best per row in bold.}\label{tab:xpos}")
    print(r"\begin{tabular*}{\textwidth}{@{\extracolsep\fill}l cccc@{}}")
    print(r"\toprule")
    print(r"Dataset & BTYD & Poisson-GBM & Hurdle-GBM & Quantile-GBM \\")
    print(r"\midrule")
    for ds in sorted(piv.index, key=lambda z: piv.loc[z, "BTYD"]):
        r = piv.loc[ds]
        best = r[methods].idxmin()
        print(f"{nm(ds)} & " + " & ".join(b(r[m], m == best) for m in methods) + r" \\")
    print(r"\botrule")
    print(r"\end{tabular*}\end{table}")
    print()


if __name__ == "__main__":
    tab_counts()
    tab_counts_accuracy()
    tab_coverage()
    tab_counts_xpos()
    tab_conformal()
    tab_amortized()
    tab_variant()
    tab_clv()
    tab_churn()
    tab_timing()
