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
    "BTYD": "#4477AA",
    "PoissonGBM": "#EE6677",
    "HurdleGBM": "#CCBB44",
    "QuantileGBM": "#228833",
    "raw": "#BBBBBB",
    "recal": "#4477AA",
    "MCMC": "#4477AA",
    "Amortized": "#EE6677",
    "ML": "#EE6677",
    "PNBD": "#4477AA",
    "GGG": "#228833",
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
    ax.axvspan(-0.5, 4.5, color="#F4F7FB", zorder=0)
    top = ax.get_ylim()[1]
    ax.text(2.0, top * 0.70, "structure calibrated", ha="center", fontsize=9, color="#4477AA")
    ax.text(5.5, top * 0.70, "structure breaks", ha="center", fontsize=9, color="#EE6677")
    ax.legend(ncol=4, frameon=False, loc="upper center", fontsize=9)
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


def main() -> None:
    fig_calibration_map()
    fig_conformal()
    fig_amortized()
    fig_clv()
    fig_churn()
    fig_timing()
    print("all Phase 2 figures written to", os.path.relpath(FIGDIR, ROOT))


if __name__ == "__main__":
    main()
