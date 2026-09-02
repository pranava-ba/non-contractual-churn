"""Generate the six figures for the Phase 2 manuscript ("Non-contractual churn").

Reads the confirmed multi-seed summaries in ``results/*_summary.csv`` and writes
publication figures into ``paper/figures/``. Pure matplotlib (no seaborn), so it
runs with the base project dependencies.

Run:  python src/make_phase2_figures.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
FIGDIR = os.path.join(ROOT, "paper", "figures")
os.makedirs(FIGDIR, exist_ok=True)

# ---- shared style -------------------------------------------------------------
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    }
)

PRETTY = {
    "OnlineRetailII": "Online\nRetail II",
    "Ta-Feng": "Ta-Feng",
    "Dunnhumby": "Dunnhumby",
    "Olist": "Olist",
    "Grocery": "Grocery",
    "CDNow": "CDNow",
    "Simulated": "Simulated",
    "Sim-k1": "Sim k=1",
    "Sim-k2": "Sim k=2",
    "Sim-k3": "Sim k=3",
    "HeldoutSim": "Held-out\nsim",
}
# a colour-blind-safe qualitative set
C = {
    "BTYD": "#5B87BD",
    "PoissonGBM": "#C0392B",
    "HurdleGBM": "#9179B3",
    "QuantileGBM": "#5FA377",
    "raw": "#8A8D8F",
    "recal": "#5B87BD",
    "MCMC": "#5B87BD",
    "Amortized": "#C0392B",
    "ML": "#C0392B",
    "PNBD": "#5B87BD",
    "GGG": "#5FA377",
}


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(RESULTS, name))


def _save(fig, fname: str) -> None:
    path = os.path.join(FIGDIR, fname)
    fig.savefig(path)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


# ---- Fig 1: the calibration map (counts, PIT-KS by dataset x method) -----------
def fig_calibration_map() -> None:
    df = _load("ml_study_summary.csv")
    d = df[(df["cond"] == "all") & (df["metric"] == "pit_ks")]
    methods = ["BTYD", "PoissonGBM", "HurdleGBM", "QuantileGBM"]
    piv = d.pivot_table(index="dataset", columns="method", values="mean")
    piv = piv.reindex(columns=methods)
    # order datasets by BTYD calibration (best -> worst) to show the gradient
    piv = piv.sort_values("BTYD")
    x = np.arange(len(piv))
    w = 0.2
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for j, m in enumerate(methods):
        ax.bar(x + (j - 1.5) * w, piv[m].values, w, label=m, color=C[m])
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(i, i) for i in piv.index])
    ax.set_ylabel("PIT–KS  (lower = better calibrated)")
    ax.set_title("Predictive calibration of purchase-count forecasts across seven cohorts")
    ax.axvspan(-0.5, 4.5, color="#F5F7FA", zorder=0)
    ymax = float(piv.values.max())
    ax.set_ylim(0, ymax * 1.34)
    ax.legend(ncol=4, frameon=False, loc="upper center", fontsize=9)
    # region labels sit in the clear band above every bar
    ax.text(2.0, ymax * 1.10, "structure calibrated", ha="center", fontsize=9, color="#5B87BD")
    ax.text(5.5, ymax * 1.10, "structure breaks", ha="center", fontsize=9, color="#C0392B")
    _save(fig, "fig_p2_calibration_map.png")


# ---- Fig 2: Conformalized BTYD, before/after PIT-KS ----------------------------
def fig_conformal() -> None:
    df = _load("conformal_study_summary.csv")
    d = df[(df["cond"] == "all") & (df["metric"] == "pit_ks")].copy()
    d = d.sort_values("raw_mean")
    x = np.arange(len(d))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.bar(x - w / 2, d["raw_mean"].values, w, label="BTYD (raw)", color=C["raw"])
    ax.bar(x + w / 2, d["recal_mean"].values, w, label="Conformalized BTYD", color=C["recal"])
    for xi, raw, rec, p in zip(x, d["raw_mean"], d["recal_mean"], d["wilcoxon_p"]):
        if raw - rec > 0.01:
            ax.annotate("", xy=(xi + w / 2, rec), xytext=(xi - w / 2, raw),
                        arrowprops=dict(arrowstyle="->", color="#333333", lw=0.8))
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(i, i) for i in d["dataset"]])
    ax.set_ylabel("PIT–KS")
    ax.set_title("One held-out split repairs calibration wherever it is broken, and does no harm")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "fig_p2_conformal.png")


# ---- Fig 3: amortized neural inference vs MCMC ---------------------------------
def fig_amortized() -> None:
    df = _load("amortized_summary.csv")
    d = df[df["metric"] == "pit_ks"].copy()
    x = np.arange(len(d))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - w / 2, d["MCMC"].values, w, label="MCMC (Gibbs)", color=C["MCMC"])
    ax.bar(x + w / 2, d["Amortized"].values, w, label="Amortized MLP", color=C["Amortized"])
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(i, i) for i in d["dataset"]])
    ax.set_ylabel("PIT–KS")
    ax.set_title("A one-pass amortized estimator matches (or beats) MCMC calibration")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "fig_p2_amortized.png")


# ---- Fig 4: probabilistic CLV, structural GG vs deep ZILN ----------------------
def fig_clv() -> None:
    df = _load("clv_study_summary.csv")
    d = df[df["cond"] == "all"]
    ks = d[d["metric"] == "pit_ks"].set_index("dataset")
    mae = d[d["metric"] == "nMAE"].set_index("dataset")
    order = ["OnlineRetailII", "Ta-Feng", "Dunnhumby"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.0))
    for ax, tab, ylab, title in (
        (axes[0], ks, "PIT–KS (calibration)", "Calibration"),
        (axes[1], mae, "nMAE (accuracy)", "Accuracy"),
    ):
        x = np.arange(len(order))
        w = 0.38
        ax.bar(x - w / 2, [tab.loc[o, "BTYD_GG_mean"] for o in order], w,
               label="Pareto/NBD + Gamma-Gamma", color=C["PNBD"])
        ax.bar(x + w / 2, [tab.loc[o, "ZILN_mean"] for o in order], w,
               label="Deep ZILN", color=C["GGG"])
        ax.set_xticks(x)
        ax.set_xticklabels([PRETTY.get(o, o) for o in order])
        ax.set_ylabel(ylab)
        ax.set_title(title)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.suptitle("Probabilistic customer lifetime value: structural CLV inherits the miscalibration",
                 y=1.02)
    _save(fig, "fig_p2_clv.png")


# ---- Fig 5: churn P(active) calibration, BTYD vs ML ----------------------------
def fig_churn() -> None:
    df = _load("churn_study_summary.csv")
    d = df[df["metric"] == "ece"].copy()
    d = d.sort_values("BTYD")
    x = np.arange(len(d))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.bar(x - w / 2, d["BTYD"].values, w, label="BTYD  P(active)", color=C["BTYD"])
    ax.bar(x + w / 2, d["ML"].values, w, label="ML classifier", color=C["ML"])
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(i, i) for i in d["dataset"]])
    ax.set_ylabel("Expected calibration error (ECE)")
    ax.set_title("Churn probability: the same assumption-driven pattern in the classification dimension")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "fig_p2_churn.png")


# ---- Fig 6: next-purchase timing, Pareto/NBD vs Pareto/GGG ---------------------
def fig_timing() -> None:
    df = _load("timing_study_summary.csv")
    d = df[df["metric"] == "timing_MdAE"].copy()
    order = ["Sim-k1", "Sim-k2", "Sim-k3", "Grocery", "CDNow"]
    d = d.set_index("dataset").reindex([o for o in order if o in set(df["dataset"])]).dropna(how="all")
    x = np.arange(len(d))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - w / 2, d["PNBD"].values, w, label="Pareto/NBD", color=C["PNBD"])
    ax.bar(x + w / 2, d["GGG"].values, w, label="Pareto/GGG", color=C["GGG"])
    for xi, a, b, p in zip(x, d["PNBD"], d["GGG"], d["wilcoxon_p"]):
        if p < 0.05 and a - b > 0.05:
            ax.text(xi, max(a, b) + 0.05, "*", ha="center", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(i, i) for i in d.index])
    ax.set_ylabel("Median abs. error of next-purchase time")
    ax.set_title("Timing: a richer structural model beats the classic where purchasing is regular")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "fig_p2_timing.png")


# ---- Fig 7: robustness -- only seasonality breaks calibration ------------------
def fig_robustness() -> None:
    dep = _load("dependence_stress_summary.csv").copy()
    sea = _load("seasonality_stress_summary.csv").sort_values("amplitude")
    cen = _load("censoring_stress_summary.csv")
    cen = cen[cen["dataset"] == "CDNow"].sort_values("drop")

    dep["absrho"] = dep["rho"].abs()
    dg = dep.groupby("absrho")["MCMC_pit_ks"].max().reset_index()
    dep_x = (dg["absrho"] / dg["absrho"].max()).values
    sea_x = (sea["amplitude"] / sea["amplitude"].max()).values
    cen_x = (cen["drop"] / cen["drop"].max()).values

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.axhspan(0, 0.05, color="#DCEBE1", zorder=0)
    ax.plot(dep_x, dg["MCMC_pit_ks"].values, "o-", color=C["BTYD"], lw=1.7,
            label=r"rate-dropout dependence ($\rho$ up to $\pm$0.6): robust")
    ax.plot(cen_x, cen["pit_ks"].values, "s-", color=C["HurdleGBM"], lw=1.7,
            label="transaction censoring (0–30%): graceful")
    ax.plot(sea_x, sea["pit_ks"].values, "D-", color=C["PoissonGBM"], lw=2.7,
            label="seasonality (amplitude 0–1): breaks")
    ax.text(0.015, 0.043, "well-calibrated", fontsize=8.5, color="#3F7A55")
    ax.set_xlabel("stress intensity (each axis normalised to its tested maximum)")
    ax.set_ylabel("PIT–KS  (lower = better calibrated)")
    ax.set_title("Only temporal non-stationarity breaks the count calibration")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _save(fig, "fig_p2_robustness.png")


# ---- Fig 8: the estimation noise floor -----------------------------------------
def fig_noisefloor() -> None:
    d = _load("noise_floor_summary.csv").sort_values("N")
    x = np.arange(len(d))
    floor = d["CRPS_floor"].values
    indiv = d["CRPS_individual"].values
    fix = d["CRPS_fixable"].clip(lower=0).values
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.bar(x, floor, label="irreducible counting noise", color=C["raw"])
    ax.bar(x, indiv, bottom=floor, label="individual-level posterior ($O(1)$)", color=C["BTYD"])
    ax.bar(x, fix, bottom=floor + indiv, label="fixable by estimation ($O(1/N)$)", color=C["PoissonGBM"])
    for xi, fl, ind in zip(x, floor, indiv):
        ax.text(xi, fl + ind + 0.008, "fixable ~0", ha="center", fontsize=8, color="#C0392B")
    ax.set_ylim(0, float((floor + indiv).max()) * 1.28)          # headroom above the bars + labels
    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(n)}" for n in d["N"]])
    ax.set_xlabel("cohort size $N$")
    ax.set_ylabel("CRPS decomposition")
    ax.set_title("The estimation-fixable share of forecast error is negligible")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _save(fig, "fig_p2_noisefloor.png")


# ---- Fig 9: seasonality on real data (forecast bias vs seasonal intensity) -----
def fig_seasonality_real() -> None:
    d = _load("seasonality_real_summary.csv").dropna()
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    colours = {"OnlineRetailII": C["PoissonGBM"], "Grocery": C["BTYD"]}
    for name, g in d.groupby("dataset"):
        r = np.corrcoef(g["seasonal_intensity"], g["forecast_ratio"])[0, 1]
        ax.scatter(g["seasonal_intensity"], g["forecast_ratio"], s=42,
                   color=colours.get(name, "#888888"),
                   label=f"{PRETTY.get(name, name).replace(chr(10), ' ')}  ($r={r:+.2f}$)")
    ax.axhline(1.0, color="#8A8D8F", lw=1, ls="--")
    ax.axvline(1.0, color="#8A8D8F", lw=1, ls="--")
    ax.text(ax.get_xlim()[1], 1.02, "unbiased", ha="right", fontsize=8, color="#777777")
    ax.set_xlabel("forecast-window seasonal intensity (vs calibration)")
    ax.set_ylabel("forecast ratio  (realised / predicted)")
    ax.set_title("Seasonality on real data: busy windows are under-forecast")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _save(fig, "fig_p2_seasonality_real.png")


def main() -> None:
    fig_calibration_map()
    fig_conformal()
    fig_amortized()
    fig_clv()
    fig_churn()
    fig_timing()
    fig_robustness()
    fig_noisefloor()
    fig_seasonality_real()
    print("all Phase 2 figures written to", os.path.relpath(FIGDIR, ROOT))


if __name__ == "__main__":
    main()
