"""Generate the Gear 2 (prescriptive/causal-ML) figures from results/gear2_*_summary.csv.

Gear 2 is a SEPARATE future paper from the Phase 2 manuscript (paper/), so these figures are
written to results/figures_gear2/, not paper/figures/ -- do not fold them into the Phase 2
submission. Pure matplotlib (Agg), mirroring make_phase2_figures.py's style conventions.

Run:  python src/make_gear2_figures.py
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
FIGDIR = os.path.join(ROOT, "results", "figures_gear2")
os.makedirs(FIGDIR, exist_ok=True)

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

STRUCT_PRETTY = {"homogeneous": "Homogeneous", "heterogeneous": "Heterogeneous",
                 "sleeping_dogs": "Sleeping dogs"}
EST_PRETTY = {"econml_CausalForest": "Causal Forest\n(econml)", "structural_BTYD": "Structural\nBTYD-CATE",
             "conformal_ITE": "Conformal\nITE", "base_value": "Value\ntargeting",
             "base_risk": "Risk\ntargeting", "random": "Random"}
C = {"econml_CausalForest": "#5B87BD", "structural_BTYD": "#5FA377", "conformal_ITE": "#7A6FB0",
    "base_value": "#C0392B", "base_risk": "#D98C3D", "random": "#8A8D8F"}


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(RESULTS, name))


def _save(fig, fname: str) -> None:
    path = os.path.join(FIGDIR, fname)
    fig.savefig(path)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


# ---- Fig 1: prediction != decision -- policy value by estimator x effect structure -------------
def fig_policy_by_structure() -> None:
    df = _load("gear2_uplift_summary.csv")
    ests = ["econml_CausalForest", "structural_BTYD", "base_value", "base_risk", "random"]
    structs = ["homogeneous", "heterogeneous", "sleeping_dogs"]
    piv = (df[df["estimator"].isin(ests)]
          .pivot_table(index="structure", columns="estimator", values="policy_pct", aggfunc="mean")
          .reindex(index=structs, columns=ests))
    x = np.arange(len(structs))
    w = 0.8 / len(ests)
    fig, ax = plt.subplots(figsize=(9.5, 4.5))
    for j, e in enumerate(ests):
        ax.bar(x + (j - (len(ests) - 1) / 2) * w, piv[e].values, w,
              label=EST_PRETTY[e].replace("\n", " "), color=C[e])
    ax.axhline(1.0, color="#333333", lw=0.8, ls="--", zorder=0)
    ax.axhline(0.0, color="#999999", lw=0.6, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels([STRUCT_PRETTY[s] for s in structs])
    ax.set_ylabel("Policy value / oracle  (1.0 = oracle targeting)")
    ax.set_title("Prediction ≠ decision: causal targeting degrades gracefully where\n"
                 "value/risk targeting backfires (sleeping dogs)")
    ax.legend(ncol=3, frameon=False, loc="lower center", fontsize=8.5, bbox_to_anchor=(0.5, -0.34))
    _save(fig, "fig_g2_policy_by_structure.png")


# ---- Fig 2: calibration of the treatment-effect interval, incl. the conformal repair -----------
def fig_calibration_repair() -> None:
    df = _load("gear2_coverage_summary.csv")
    piv = (df.pivot_table(index="estimator", columns="assignment", values="coverage90", aggfunc="mean")
          .sort_values("randomized"))
    x = np.arange(len(piv))
    w = 0.38
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(x - w / 2, piv["randomized"].values, w, label="Randomized", color="#5B87BD")
    ax.bar(x + w / 2, piv["confounded"].values, w, label="Confounded", color="#C0392B")
    ax.axhline(0.90, color="#333333", lw=0.9, ls="--", label="Nominal (90%)")
    ax.set_xticks(x)
    ax.set_xticklabels(piv.index, rotation=15, ha="right")
    ax.set_ylabel("Coverage of the 90% CATE interval")
    ax.set_title("Causal-forest intervals are genuinely overconfident;\nconformal-ITE restores nominal coverage")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "fig_g2_calibration_repair.png")


# ---- Fig 3: external validity -- Dunnhumby (DR) + Hillstrom (Qini) + X5 (Qini) -----------------
def fig_real_data() -> None:
    dh = _load("gear2_dunnhumby_summary.csv")
    hs = _load("gear2_hillstrom_summary.csv")
    x5 = _load("gear2_x5_summary.csv")

    dh_agg = dh.groupby("policy").dr_value.mean()
    base = dh_agg.get("treat_none", 0.0)
    dh_inc = (dh_agg - base).drop(index=[i for i in ("treat_none",) if i in dh_agg.index]).sort_values()

    hs_agg = hs.groupby("method").qini_auc.mean().sort_values()
    x5_agg = x5.groupby("method").qini_auc.mean().sort_values()

    def _colors(idx):
        return ["#C0392B" if "value" in n else ("#8A8D8F" if n in ("random", "treat_all") else "#5B87BD")
               for n in idx]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.2))
    ax = axes[0]
    ax.barh(range(len(dh_inc)), dh_inc.values, color=_colors(dh_inc.index))
    ax.set_yticks(range(len(dh_inc)))
    ax.set_yticklabels(dh_inc.index)
    ax.set_xlabel("Incremental DR policy value\nvs. treat-none")
    ax.set_title("Dunnhumby (observational,\ndoubly-robust)")

    ax2 = axes[1]
    ax2.barh(range(len(hs_agg)), hs_agg.values, color=_colors(hs_agg.index))
    ax2.set_yticks(range(len(hs_agg)))
    ax2.set_yticklabels(hs_agg.index)
    ax2.set_xlabel("Qini AUC")
    ax2.set_title("Hillstrom (randomized,\nQini-valid)")

    ax3 = axes[2]
    ax3.barh(range(len(x5_agg)), x5_agg.values, color=_colors(x5_agg.index))
    ax3.axvline(0.0, color="#333333", lw=0.7, zorder=0)
    ax3.set_yticks(range(len(x5_agg)))
    ax3.set_yticklabels(x5_agg.index)
    ax3.set_xlabel("Qini AUC")
    ax3.set_title("X5 RetailHero (randomized,\nQini-valid)")

    fig.suptitle("External validity: uplift beats value on all three real datasets "
                 "(value even loses to random on X5)", y=1.04)
    _save(fig, "fig_g2_realdata_validation.png")


# ---- Fig 4: does the BTYD posterior state help over raw RFM? -----------------------------------
def fig_ablation() -> None:
    df = _load("gear2_ablation_summary.csv")
    piv = df.pivot_table(index="features", columns="structure", values="policy_pct", aggfunc="mean")
    structs = ["homogeneous", "heterogeneous", "sleeping_dogs"]
    piv = piv.reindex(columns=structs)
    x = np.arange(len(structs))
    w = 0.38
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(x - w / 2, piv.loc["rfm"].values, w, label="RFM only", color="#8A8D8F")
    ax.bar(x + w / 2, piv.loc["rfm+btyd"].values, w, label="RFM + BTYD state", color="#5B87BD")
    ax.set_xticks(x)
    ax.set_xticklabels([STRUCT_PRETTY[s] for s in structs])
    ax.set_ylabel("Policy value / oracle")
    ax.set_title("Feature ablation: the BTYD posterior state is immaterial\nfor causal targeting (RFM already sufficient)")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "fig_g2_feature_ablation.png")


if __name__ == "__main__":
    fig_policy_by_structure()
    fig_calibration_repair()
    fig_real_data()
    fig_ablation()
