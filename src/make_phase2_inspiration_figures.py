"""Generate the 'writing-inspiration' diagrams/figures for the Phase 2 manuscript.

Palette order: BLUE, GREEN, PURPLE, RED, GREY (pastel-forward; the red is a true
red, never pink). Hex values match src/make_phase2_figures.py and
paper/phase2_palette.tex so document, tables and figures are one color system.
Diagrams use pastel fills with dark text and generous box sizing so text never
leaks outside its box. Reference style: Valendin et al. (2022), IJRM.

Run:  python src/make_phase2_inspiration_figures.py
"""
from __future__ import annotations

import os
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
FIGDIR = os.path.join(ROOT, "paper", "figures")
TRACKER = os.path.join(ROOT, "research-paper-tracker", "data", "out")
os.makedirs(FIGDIR, exist_ok=True)

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight",
})

# ---- the ONE palette (order: blue, green, purple, red, grey) ------------------
BLUE, GREEN, PURPLE, RED, GREY = "#5B87BD", "#5FA377", "#9179B3", "#C0392B", "#8A8D8F"
BLUE_T, GREEN_T, PURPLE_T, RED_T, GREY_T = "#DCE6F2", "#DCEBE1", "#E7E0F0", "#EDD6D2", "#E7E8E9"
WASH, INK = "#F5F7FA", "#2B2B2B"


def _save(fig, fname):
    path = os.path.join(FIGDIR, fname)
    fig.savefig(path)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


def _blank(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


def _box(ax, x, y, w, h, text, fill, border, tc=INK, fs=9.0, weight="normal", wrap=None):
    """Rounded box: pastel fill, colored border, dark text. Text is optionally
    wrapped to `wrap` chars so it stays inside the box."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.016",
        fc=fill, ec=border, lw=1.3, mutation_aspect=1.0, zorder=3))
    if wrap:
        text = "\n".join(textwrap.wrap(text, wrap))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color=tc, fontsize=fs, weight=weight, zorder=4, linespacing=1.2)


def _hdr(ax, x, y, w, h, text, color, fs=10.5):
    """Solid header chip with white text (short labels only)."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.016",
        fc=color, ec=color, lw=1.0, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color="white", fontsize=fs, weight="bold", zorder=4)


def _arrow(ax, xy1, xy2, color=INK, lw=1.3, style="-|>"):
    ax.add_patch(FancyArrowPatch(xy1, xy2, arrowstyle=style, mutation_scale=12,
                                 color=color, lw=lw, zorder=2))


# =============================================================================
# 1. Taxonomy of forecasting approaches
# =============================================================================
def fig_taxonomy():
    fig, ax = plt.subplots(figsize=(8.8, 5.6)); _blank(ax)
    ax.text(0.5, 0.965, "Customer-base forecasting", ha="center", va="center",
            fontsize=13.5, weight="bold", color=INK)
    ax.text(0.5, 0.915, "four managerial targets:  counts  ·  value  ·  churn  ·  timing",
            ha="center", va="center", fontsize=9.5, style="italic", color=INK)

    _hdr(ax, 0.02, 0.80, 0.30, 0.07, "Structural  (BTYD)", BLUE)
    _hdr(ax, 0.35, 0.80, 0.30, 0.07, "Machine learning", RED)
    _hdr(ax, 0.68, 0.80, 0.30, 0.07, "Repairs & bridges", GREEN)

    for i, t in enumerate(["Pareto/NBD", "BG/NBD", "Pareto/GGG"]):
        _box(ax, 0.04, 0.655 - i * 0.115, 0.26, 0.088, t, BLUE_T, BLUE, fs=9.5, weight="bold")
    # ML members; Quantile-GBM flagged green (distribution-free)
    ml = [("Poisson-GBM", RED_T, RED), ("Hurdle-GBM", RED_T, RED),
          ("Quantile-GBM", GREEN_T, GREEN), ("Deep ZILN", RED_T, RED),
          ("RNN  (Valendin)", RED_T, RED)]
    for i, (t, f, b) in enumerate(ml):
        _box(ax, 0.37, 0.695 - i * 0.092, 0.26, 0.07, t, f, b, fs=9.0)
    _box(ax, 0.70, 0.545, 0.26, 0.115, "Conformalized BTYD", GREEN_T, GREEN, fs=9.2, wrap=18)
    _box(ax, 0.70, 0.385, 0.26, 0.115, "Amortized MLP (one-pass SBI)", PURPLE_T, PURPLE, fs=9.2, wrap=18)

    for x in (0.17, 0.50, 0.83):
        _arrow(ax, (0.5, 0.905), (x, 0.872), color=GREY, lw=1.1)
    _arrow(ax, (0.63, 0.60), (0.70, 0.60), color=GREEN, lw=1.1)
    _arrow(ax, (0.30, 0.47), (0.70, 0.45), color=PURPLE, lw=1.1)

    ax.text(0.50, 0.245,
            "Quantile-GBM (green) is the only ML forecaster that is distribution-free —\n"
            "it escapes the parametric Poisson count assumption the other models share.",
            ha="center", va="center", fontsize=8.2, color=GREEN)

    ax.add_patch(FancyBboxPatch((0.03, 0.03), 0.94, 0.115,
                 boxstyle="round,pad=0.004,rounding_size=0.02",
                 fc=WASH, ec=BLUE, lw=1.3, zorder=1))
    ax.text(0.5, 0.088, "Evaluation lens (this paper's axis):  proper scoring  +  PIT / CRPS / coverage / ECE",
            ha="center", va="center", fontsize=10, weight="bold", color=INK)
    for x in (0.17, 0.50, 0.83):
        _arrow(ax, (x, 0.185), (x, 0.148), color=GREY, lw=1.0)
    _save(fig, "fig_p2_taxonomy.png")


# =============================================================================
# 2. PRISMA-style literature funnel  (real counts from the tracker)
# =============================================================================
def fig_prisma():
    fc = pd.read_csv(os.path.join(TRACKER, "funnel_counts.csv"))
    row = fc[fc["category"] == "__ALL_unique__"].iloc[0]
    ident, kept = int(row["identified"]), int(row["kept"])
    exc = {"prior screen": int(row["already_hidden"]),
           "RFM segmentation (not churn/CLV)": int(row["rfm_segmentation"]),
           "contractual (telecom/SaaS)": int(row["contractual_churn"]),
           "off-topic keyword hits": int(row["offtopic"]),
           "non-English": int(row["non_english"])}
    total_exc = sum(exc.values())

    fig, ax = plt.subplots(figsize=(8.0, 4.9)); _blank(ax)
    _hdr(ax, 0.04, 0.79, 0.56, 0.14, "", BLUE)
    ax.text(0.32, 0.865, f"{ident} records identified", ha="center", va="center",
            color="white", fontsize=11.5, weight="bold", zorder=4)
    ax.text(0.32, 0.815, "OpenAlex + arXiv + Crossref, 2020–2026", ha="center", va="center",
            color="white", fontsize=8.5, zorder=4)
    _hdr(ax, 0.04, 0.40, 0.56, 0.13, f"{kept} kept for the comparison set", BLUE, fs=11)
    _hdr(ax, 0.04, 0.05, 0.56, 0.15, "", GREEN)
    ax.text(0.32, 0.125, "0 evaluate BTYD vs ML by\nprobability calibration", ha="center",
            va="center", color="white", fontsize=10.5, weight="bold", zorder=4)
    _arrow(ax, (0.32, 0.785), (0.32, 0.535), color=INK, lw=1.5)
    _arrow(ax, (0.32, 0.395), (0.32, 0.205), color=INK, lw=1.5)

    lines = "\n".join(f"–  {v}   {k}" for k, v in exc.items())
    ax.add_patch(FancyBboxPatch((0.64, 0.42), 0.34, 0.44,
                 boxstyle="round,pad=0.008,rounding_size=0.02",
                 fc=GREY_T, ec=GREY, lw=1.2, zorder=3))
    ax.text(0.655, 0.82, f"{total_exc} excluded", ha="left", va="top",
            fontsize=9.5, weight="bold", color=INK)
    ax.text(0.655, 0.74, lines, ha="left", va="top", fontsize=7.8, color=INK, linespacing=1.7)
    _arrow(ax, (0.32, 0.655), (0.64, 0.655), color=GREY, lw=1.2)
    _save(fig, "fig_p2_prisma.png")


# =============================================================================
# 3. Finite-horizon active/churn window schematic
# =============================================================================
def fig_churnwindow():
    fig, ax = plt.subplots(figsize=(8.4, 3.3)); _blank(ax)
    y = 0.44
    ax.add_patch(plt.Rectangle((0.06, y - 0.05), 0.50, 0.10, fc=BLUE_T, ec=BLUE, lw=1.4, zorder=1))
    ax.add_patch(plt.Rectangle((0.56, y - 0.05), 0.30, 0.10, fc=GREEN_T, ec=GREEN, lw=1.4, zorder=1))
    ax.plot([0.06, 0.90], [y, y], color=INK, lw=1.0, zorder=2)
    ax.annotate("", xy=(0.95, y), xytext=(0.90, y),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0))
    ax.text(0.955, y, "time", ha="left", va="center", fontsize=9, color=INK)

    for xp in (0.12, 0.19, 0.28, 0.41):
        ax.plot([xp, xp], [y - 0.035, y + 0.035], color=BLUE, lw=2.4, zorder=3)
    ax.plot([0.41, 0.41], [y - 0.04, y + 0.04], color=BLUE, lw=3.2, zorder=3)
    ax.text(0.41, y + 0.085, "$t_x$ (last purchase)", ha="center", fontsize=8.5, color=BLUE)
    ax.plot([0.70, 0.70], [y - 0.04, y + 0.04], color=GREEN, lw=3.0, zorder=3)

    ax.text(0.31, y - 0.105, "Calibration period  $T_i$", ha="center", fontsize=9.5, color=BLUE, weight="bold")
    ax.text(0.71, y - 0.105, "Forecast horizon  $T^{*}$", ha="center", fontsize=9.5, color=GREEN, weight="bold")

    ax.annotate("", xy=(0.56, y + 0.185), xytext=(0.86, y + 0.185),
                arrowprops=dict(arrowstyle="-", color=GREEN, lw=1.2))
    ax.text(0.71, y + 0.255,
            "$P(x^{*}\\!>\\!0)$ — active if $\\geq 1$ purchase in the window;\n"
            "validatable, finite-horizon  ( = Ulrich's $R_H$ )",
            ha="center", va="center", fontsize=8.8, color=GREEN)
    ax.plot([0.86, 0.98], [y, y], color=GREY, lw=1.3, ls="--", zorder=1)
    ax.text(0.5, y - 0.28,
            "$P(\\mathrm{alive}\\ \\mathrm{at}\\ T)$: latent, infinite-horizon limit "
            "$=\\lim_{H\\to\\infty} R_H$  (only partially identified)",
            ha="center", va="center", fontsize=8.0, color=GREY, style="italic")
    ax.set_ylim(0.02, 0.95)
    _save(fig, "fig_p2_churnwindow.png")


# =============================================================================
# 4. Structural vs ML/amortized pipeline schematic
# =============================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(8.8, 4.0)); _blank(ax)
    _box(ax, 0.01, 0.39, 0.22, 0.19,
         "Transaction log $\\rightarrow$\nRFM summary\n$(x,\\,t_x,\\,T,\\,\\bar m)$",
         GREY_T, GREY, fs=8.4)
    _box(ax, 0.31, 0.70, 0.25, 0.15, "Pareto/NBD likelihood", BLUE_T, BLUE, fs=9, wrap=16)
    _box(ax, 0.61, 0.70, 0.16, 0.15, "MCMC / MLE", BLUE_T, BLUE, fs=9)
    _box(ax, 0.81, 0.63, 0.18, 0.22, "Posterior predictive distribution", BLUE_T, BLUE, fs=8.8, wrap=13)
    _box(ax, 0.31, 0.06, 0.25, 0.15, "GBM / RNN / ZILN", RED_T, RED, fs=9, wrap=16)
    _box(ax, 0.81, 0.06, 0.18, 0.15, "Predictive distribution", RED_T, RED, fs=8.8, wrap=13)
    _box(ax, 0.31, 0.37, 0.46, 0.15,
         "Amortized MLP — trained once\non simulated $(\\theta,\\mathrm{data})$ pairs",
         PURPLE_T, PURPLE, fs=8.8)

    _arrow(ax, (0.235, 0.53), (0.31, 0.76), color=BLUE)
    _arrow(ax, (0.235, 0.49), (0.31, 0.45), color=PURPLE)
    _arrow(ax, (0.235, 0.45), (0.31, 0.15), color=RED)
    _arrow(ax, (0.56, 0.775), (0.61, 0.775), color=BLUE)
    _arrow(ax, (0.77, 0.775), (0.81, 0.75), color=BLUE)
    _arrow(ax, (0.77, 0.45), (0.905, 0.63), color=PURPLE)
    _arrow(ax, (0.56, 0.135), (0.81, 0.135), color=RED)
    ax.text(0.5, 0.925, "One RFM summary, three inference paths, one calibration lens",
            ha="center", fontsize=10.5, weight="bold", color=INK)
    _save(fig, "fig_p2_architecture.png")


# =============================================================================
# 5. Per-cohort BTYD-vs-ML calibration lift panel  (churn ECE)
# =============================================================================
def fig_lift():
    d = pd.read_csv(os.path.join(RESULTS, "churn_study_summary.csv"))
    e = d[d["metric"] == "ece"].copy()
    e["delta"] = e["ML"] - e["BTYD"]
    e = e.sort_values("delta")
    names = {"OnlineRetailII": "Online Retail II"}
    labels = [names.get(n, n) for n in e["dataset"]]
    colors = [BLUE if v > 0 else RED for v in e["delta"]]

    fig, ax = plt.subplots(figsize=(7.8, 4.1))
    yv = np.arange(len(e))
    ax.barh(yv, e["delta"].values, color=colors, height=0.62, zorder=3)
    ax.axvline(0, color=INK, lw=1.0)
    ax.set_yticks(yv); ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlabel("churn-ECE advantage   (ML ECE $-$ BTYD ECE)")
    ax.set_ylim(-0.7, len(e) - 0.3)
    ax.text(0.028, len(e) - 0.55, "◀  ML better", color=RED, fontsize=9.5, weight="bold", ha="left")
    ax.text(-0.028, len(e) - 0.55, "BTYD better  ▶", color=BLUE, fontsize=9.5, weight="bold", ha="right")
    for yi, v in zip(yv, e["delta"].values):
        ax.text(v + (0.004 if v >= 0 else -0.004), yi, f"{v:+.3f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=8, color=INK)
    ax.margins(x=0.18)
    ax.set_title("Churn calibration by cohort: structure wins where the count law fits", fontsize=11)
    _save(fig, "fig_p2_lift.png")


# =============================================================================
# 6. Per-customer event-timeline strips  (raw cohorts)
# =============================================================================
def fig_timeline():
    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        from datasets import load_dunnhumby, load_online_retail_ii, load_olist
    except Exception as ex:  # pragma: no cover
        print("  [timeline] skipped — could not import loaders:", ex); return
    specs = [("Olist  (sparse)", load_olist, BLUE),
             ("Online Retail II  (mixed)", load_online_retail_ii, PURPLE),
             ("Dunnhumby  (dense)", load_dunnhumby, RED)]
    fig, axes = plt.subplots(len(specs), 1, figsize=(8.2, 4.6), sharex=True)
    for ax, (title, loader, col) in zip(axes, specs):
        try:
            elog = loader()[["cust", "date"]].dropna().copy()
            elog["date"] = pd.to_datetime(elog["date"])
            t0 = elog["date"].min()
            elog["wk"] = (elog["date"] - t0).dt.days / 7.0
            counts = elog.groupby("cust").size()
            qs = np.quantile(counts.values, np.linspace(0.80, 0.999, 8))
            picks = []
            for q in qs:
                c = counts.index[np.argmin(np.abs(counts.values - q))]
                if c not in picks:
                    picks.append(c)
            for i, c in enumerate(picks):
                wks = elog.loc[elog["cust"] == c, "wk"].values
                ax.scatter(wks, np.full_like(wks, i, dtype=float), s=14, color=col,
                           marker="|", linewidths=1.6)
            ax.set_yticks([]); ax.set_ylabel(title, fontsize=8.8, rotation=0,
                                             ha="right", va="center", labelpad=6)
            ax.set_ylim(-0.7, len(picks) - 0.3)
            for sp in ("top", "right", "left"):
                ax.spines[sp].set_visible(False)
        except Exception as ex:  # pragma: no cover
            print(f"  [timeline] {title} failed:", ex)
            ax.text(0.5, 0.5, "(data unavailable)", ha="center", transform=ax.transAxes)
    axes[-1].set_xlabel("weeks since cohort start")
    axes[0].set_title("A handful of customers per cohort: sparsity vs density drives the calibration story",
                      fontsize=10.5)
    _save(fig, "fig_p2_timeline.png")


# =============================================================================
# 7. CORP reliability diagrams for churn probability (Dimitriadis-Gneiting-Jordan)
# =============================================================================
def fig_reliability():
    cf = os.path.join(RESULTS, "reliability_curves.csv")
    mf = os.path.join(RESULTS, "reliability_meta.csv")
    if not (os.path.exists(cf) and os.path.exists(mf)):
        print("  [reliability] skipped — run src/make_reliability_data.py first"); return
    cur = pd.read_csv(cf); meta = pd.read_csv(mf)
    order = ["Simulated", "Grocery", "OnlineRetailII", "Dunnhumby"]
    pretty = {"OnlineRetailII": "Online Retail II"}
    regime = {"Simulated": ("structure fits", BLUE), "Grocery": ("structure fits", BLUE),
              "OnlineRetailII": ("structure breaks", RED), "Dunnhumby": ("structure breaks", RED)}
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.2))
    for ax, name in zip(axes.ravel(), order):
        ax.plot([0, 1], [0, 1], color=GREY, lw=1.0, ls="--", zorder=1)
        for method, col in (("BTYD", BLUE), ("ML", RED)):
            d = cur[(cur.dataset == name) & (cur.method == method)].sort_values("x")
            ax.plot(d.x, d.y, color=col, lw=2.3, zorder=3, solid_capstyle="round", label=method)
        try:
            mb = meta[(meta.dataset == name) & (meta.method == "BTYD")].iloc[0]
            mm = meta[(meta.dataset == name) & (meta.method == "ML")].iloc[0]
            ax.text(0.05, 0.93, f"BTYD  ECE {mb.ece:.3f}", color=BLUE, fontsize=8.6, weight="bold")
            ax.text(0.05, 0.84, f"ML    ECE {mm.ece:.3f}", color=RED, fontsize=8.6, weight="bold")
        except IndexError:
            pass
        lab, lc = regime[name]
        ax.text(0.95, 0.06, lab, color=lc, fontsize=8.4, style="italic", ha="right")
        ax.set_title(pretty.get(name, name), fontsize=10.5)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
        ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1])
    for ax in axes[-1]:
        ax.set_xlabel("predicted $P(\\mathrm{active})$")
    for ax in axes[:, 0]:
        ax.set_ylabel("observed frequency (isotonic)")
    fig.suptitle("CORP reliability diagrams for churn probability: BTYD (blue) vs ML (red)",
                 fontsize=11, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, "fig_p2_reliability.png")


def print_covariate_means():
    c = pd.read_csv(os.path.join(RESULTS, "covariate_targets_summary.csv"))
    g = c.groupby("features")[["count_pit_ks", "count_CRPS"]].agg(["mean", "std"])
    print("\n[covariate means for tab:covariate]\n", g.round(4).to_string())


if __name__ == "__main__":
    fig_taxonomy()
    fig_prisma()
    fig_churnwindow()
    fig_architecture()
    fig_lift()
    fig_timeline()
    fig_reliability()
    print_covariate_means()
