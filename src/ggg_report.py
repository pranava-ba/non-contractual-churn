"""
Report the Pareto/GGG-vs-Pareto/NBD misspecification result (expansion A).

Reads results/ggg_results.csv (produced by run_ggg.py) and writes:
  * paper/tables/tab_ggg.tex   -- paired PIT-KS + CRPS + k-recovery + E(lambda) de-bias
  * results/figures/fig5_ggg_vs_pnbd.png (+ copy into paper/figures/)
  * a console summary with paired Wilcoxon tests (GGG vs PNBD, per k and pooled).

Run:  python src/ggg_report.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
TAB = ROOT / "paper" / "tables"
FIGS = [RES / "figures", ROOT / "paper" / "figures"]
KS = sorted([1.0, 1.5, 2.0, 3.0, 4.0])


def load():
    d = pd.read_csv(RES / "ggg_results.csv")
    return d


def paired(d, cond, metric="pit_ks"):
    """Paired GGG-vs-PNBD differences per k (matched by rep), + pooled Wilcoxon."""
    s = d[d["cond"] == cond]
    per_k = {}
    all_g, all_p = [], []
    for k in KS:
        w = (s[s.k == k].pivot_table(index="rep", columns="model", values=metric).dropna())
        if len(w) < 3:
            continue
        per_k[k] = (w["PNBD"].mean(), w["GGG"].mean(), (w["GGG"] - w["PNBD"]).median(), len(w))
        all_g.append(w["GGG"].values); all_p.append(w["PNBD"].values)
    g = np.concatenate(all_g); p = np.concatenate(all_p)
    pv = stats.wilcoxon(g, p).pvalue if not np.allclose(g, p) else 1.0
    return per_k, float(pv)


def mean_by_k(d, model, cond, metric, ks):
    s = d[(d.model == model) & (d["cond"] == cond)]
    return s.groupby("k")[metric].mean().reindex(ks)


def write_table(d):
    ks_present = sorted(d.k.unique())
    crit_xpos = d[d["cond"] == "xcal_pos"].groupby("k").n.mean().reindex(ks_present)
    crit_xpos = 1.36 / np.sqrt(crit_xpos)

    pnbd_pit = mean_by_k(d, "PNBD", "xcal_pos", "pit_ks", ks_present)
    ggg_pit = mean_by_k(d, "GGG", "xcal_pos", "pit_ks", ks_present)
    pnbd_crps = mean_by_k(d, "PNBD", "xcal_pos", "CRPS", ks_present)
    ggg_crps = mean_by_k(d, "GGG", "xcal_pos", "CRPS", ks_present)
    khat = d[d.model == "GGG"].groupby("k").k_hat.mean().reindex(ks_present)
    # E(lambda) recovery ratio (hat / true), averaged
    dd = d.assign(_rp=d.E_lambda_pnbd / d.E_lambda_true,
                  _rg=d.E_lambda_ggg / d.E_lambda_true)
    er_pnbd = dd.groupby("k")._rp.mean().reindex(ks_present)
    er_ggg = dd.groupby("k")._rg.mean().reindex(ks_present)

    def row(label, series, fmt="{:.3f}"):
        return label + " & " + " & ".join(fmt.format(v) for v in series) + r" \\"

    hdr = "$k$ & " + " & ".join(f"{k:g}" for k in ks_present) + r" \\"
    lines = [r"\begin{tabular}{l" + "r" * len(ks_present) + "}", r"\toprule", hdr, r"\midrule",
             r"\multicolumn{" + str(len(ks_present) + 1) +
             r"}{l}{\emph{Calibration} --- PIT-KS on repeat buyers ($x>0$)} \\",
             row(r"\quad Pareto/NBD (misspecified)", pnbd_pit),
             row(r"\quad Pareto/GGG (correctly specified)", ggg_pit),
             row(r"\quad KS 5\% critical value", crit_xpos),
             r"\midrule",
             r"\multicolumn{" + str(len(ks_present) + 1) +
             r"}{l}{\emph{Accuracy} --- CRPS on repeat buyers ($x>0$)} \\",
             row(r"\quad Pareto/NBD", pnbd_crps),
             row(r"\quad Pareto/GGG", ggg_crps),
             r"\midrule",
             r"\multicolumn{" + str(len(ks_present) + 1) +
             r"}{l}{\emph{Parameter recovery}} \\",
             row(r"\quad $\hat k$ (Pareto/GGG)", khat, "{:.2f}"),
             row(r"\quad $\widehat{E(\lambda)}/E(\lambda)$, Pareto/NBD", er_pnbd, "{:.2f}"),
             row(r"\quad $\widehat{E(\lambda)}/E(\lambda)$, Pareto/GGG", er_ggg, "{:.2f}"),
             r"\bottomrule", r"\end{tabular}"]
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / "tab_ggg.tex").write_text("\n".join(lines), encoding="utf-8")
    print("[table] tab_ggg.tex")


def make_figure(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, cond, title in zip(axes, ["all", "xcal_pos"],
                               ["all customers", "repeat buyers ($x>0$)"]):
        for model, color in [("PNBD", "#d95f0e"), ("GGG", "#2c7fb8")]:
            s = d[(d.model == model) & (d["cond"] == cond)]
            g = s.groupby("k").pit_ks
            m = g.mean().reindex(KS); se = g.sem().reindex(KS)
            lbl = "Pareto/NBD (misspecified)" if model == "PNBD" else "Pareto/GGG"
            ax.errorbar(KS, m, yerr=se, marker="o", color=color, label=lbl, capsize=3)
        ncrit = d[d["cond"] == cond].groupby("k").n.mean().reindex(KS)
        ax.plot(KS, 1.36 / np.sqrt(ncrit), ls="--", c="k", lw=1, label="5% KS critical")
        ax.set_title(f"PIT-KS vs regularity — {title}")
        ax.set_xlabel("inter-purchase regularity $k$ ($k=1$ is Pareto/NBD)")
    axes[0].set_ylabel("PIT-KS (0 = calibrated)")
    axes[0].legend(fontsize=8)
    fig.suptitle("Modelling regularity (Pareto/GGG) restores the calibration that the "
                 "misspecified Pareto/NBD loses at high $k$")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for d_ in FIGS:
        d_.mkdir(parents=True, exist_ok=True)
        fig.savefig(d_ / "fig5_ggg_vs_pnbd.png", dpi=140)
    plt.close(fig)
    print("[figure] fig5_ggg_vs_pnbd.png")


def summary(d):
    print(f"\nloaded {len(d)} rows | k={sorted(d.k.unique())} | "
          f"reps/k={d[d.model=='GGG'].groupby('k').rep.nunique().to_dict()}\n")
    for cond in ["all", "xcal_pos"]:
        per_k, pv = paired(d, cond, "pit_ks")
        print(f"=== PIT-KS  ({cond})  GGG vs PNBD ===")
        print(f"{'k':>5} {'PNBD':>7} {'GGG':>7} {'med diff':>9} {'n':>4}")
        for k, (pn, gg, md, nn) in per_k.items():
            print(f"{k:>5} {pn:>7.3f} {gg:>7.3f} {md:>+9.3f} {nn:>4}")
        print(f"pooled Wilcoxon GGG vs PNBD p = {pv:.4g}\n")
    # k recovery + E(lambda) de-bias
    print("=== recovery ===")
    rec = (d[d.model == "GGG"].groupby("k")
           .agg(k_hat=("k_hat", "mean"),
                el_true=("E_lambda_true", "mean"),
                el_pnbd=("E_lambda_pnbd", "mean"),
                el_ggg=("E_lambda_ggg", "mean")))
    print(rec.round(3).to_string())


if __name__ == "__main__":
    d = load()
    summary(d)
    write_table(d)
    make_figure(d)
    print("\ndone.")
