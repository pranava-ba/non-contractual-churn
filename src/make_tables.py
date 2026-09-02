"""
Generate submission-ready LaTeX tables directly from the results CSVs, so every
number in the manuscript is provably traceable to the pipeline output.

Writes paper/tables/*.tex, each a bare tabular that manuscript.tex \\input's.
Run:  python src/make_tables.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RES, TAB = ROOT / "results", ROOT / "paper" / "tables"
TAB.mkdir(parents=True, exist_ok=True)
H = 26  # reported horizon


def bh(p):
    p = np.asarray(p, float)
    m = np.isfinite(p).sum()
    order = np.argsort(np.where(np.isfinite(p), p, np.inf))
    adj, prev = np.full_like(p, np.nan), 1.0
    for rank, idx in enumerate(order[::-1]):
        if not np.isfinite(p[idx]):
            continue
        prev = min(prev, p[idx] * m / (m - rank))
        adj[idx] = prev
    return adj


def write(name, body):
    (TAB / name).write_text(body, encoding="utf-8")
    print(f"[table] {name}")


# ---- Table 1: estimator comparison by cohort size --------------------------- #
def table_estimator():
    d = pd.read_csv(RES / "main_results.csv")
    d = d[d.horizon == H]
    rows = []
    for N, g in d.groupby("N"):
        r = {}
        for cond in ["all", "active"]:
            for m in ["MCMC", "MLE_plugin"]:
                s = g[(g["cond"] == cond) & (g.method == m)]
                r[(cond, m, "cov95")] = s.cov95.mean()
                r[(cond, m, "CRPS")] = s.CRPS.mean()
        rows.append((N, r))
    lines = [r"\begin{tabular}{r cc cc cc}", r"\toprule",
             r"& \multicolumn{2}{c}{cov$_{95}$ (all)} & "
             r"\multicolumn{2}{c}{cov$_{95}$ ($x>0$)} & "
             r"\multicolumn{2}{c}{CRPS ($x>0$)} \\",
             r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}",
             r"$N$ & MCMC & MLE & MCMC & MLE & MCMC & MLE \\", r"\midrule"]
    for N, r in rows:
        lines.append(
            f"{N} & {r[('all','MCMC','cov95')]:.3f} & {r[('all','MLE_plugin','cov95')]:.3f} & "
            f"{r[('active','MCMC','cov95')]:.3f} & {r[('active','MLE_plugin','cov95')]:.3f} & "
            f"{r[('active','MCMC','CRPS')]:.3f} & {r[('active','MLE_plugin','CRPS')]:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("tab_estimator.tex", "\n".join(lines))


# ---- Table 2: paired significance tests ------------------------------------- #
def table_significance():
    d = pd.read_csv(RES / "main_results.csv")
    d = d[d.horizon == H]
    recs = []
    for metric in ["CRPS", "cov95", "cov50"]:
        for cond in ["all", "active"]:
            for m2, label in [("MLE_plugin", "MCMC vs.\\ MLE"),
                              ("heuristic", "MCMC vs.\\ heuristic")]:
                w = (d[(d["cond"] == cond) & (d.method.isin(["MCMC", m2]))]
                     .pivot_table(index=["N", "rep"], columns="method", values=metric)
                     .dropna())
                if len(w) < 6:
                    continue
                p = stats.wilcoxon(w["MCMC"], w[m2]).pvalue
                recs.append(dict(metric=metric, cond=cond, comp=label, n=len(w),
                                 med=(w["MCMC"] - w[m2]).median(), p=p))
    out = pd.DataFrame(recs)
    out["pbh"] = bh(out.p.values)
    lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
             r"Metric & Subgroup & Comparison & $n$ & Median diff. & $p_{\text{BH}}$ \\",
             r"\midrule"]
    namemap = {"all": "all", "active": "$y>0$"}
    for _, r in out.iterrows():
        pstr = "$<$0.001" if r.pbh < 1e-3 else f"{r.pbh:.3f}"
        lines.append(f"{r.metric} & {namemap[r['cond']]} & {r.comp} & {int(r.n)} & "
                     f"{r.med:+.3f} & {pstr} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("tab_significance.tex", "\n".join(lines))


# ---- Table 3: PIT by conditioning (the evaluation-trap table) --------------- #
def table_conditioning():
    e = pd.read_csv(RES / "empirical_results.csv")
    e = e[(e.horizon == H) & (e.method == "MCMC")]
    lines = [r"\begin{tabular}{l ccc ccc}", r"\toprule",
             r"& \multicolumn{3}{c}{PIT-KS} & \multicolumn{3}{c}{KS 5\% critical value} \\",
             r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
             r"Dataset & all & $x>0$ & $y>0$ & all & $x>0$ & $y>0$ \\",
             r"\midrule"]
    for ds in ["CDNow", "Grocery"]:
        s = e[e.dataset == ds]
        ks = {c: s[s["cond"] == c].pit_ks.iloc[0] for c in ["all", "xcal_pos", "active"]}
        cr = {c: 1.36 / np.sqrt(s[s["cond"] == c].n.iloc[0])
              for c in ["all", "xcal_pos", "active"]}
        lines.append(
            f"{ds} & {ks['all']:.3f} & {ks['xcal_pos']:.3f} & {ks['active']:.3f} & "
            f"{cr['all']:.3f} & {cr['xcal_pos']:.3f} & {cr['active']:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("tab_conditioning.tex", "\n".join(lines))


# ---- Table 4: misspecification stress-tests --------------------------------- #
def table_misspec():
    reg = pd.read_csv(RES / "misspec_results.csv")
    mix = pd.read_csv(RES / "mixture_results.csv")
    lines = [r"\begin{tabular}{lrrrrr}", r"\toprule",
             r"\multicolumn{6}{l}{\emph{(a) Inter-purchase regularity} "
             r"($k=1$ is Pareto/NBD)} \\", r"\midrule",
             r"$k$ & " + " & ".join(f"{k:g}" for k in sorted(reg.k.unique())) + r" \\"]
    for cond, lab in [("all", "PIT-KS (all)"), ("xcal_pos", "PIT-KS ($x>0$)")]:
        g = reg[reg["cond"] == cond].groupby("k").pit_ks.mean()
        lines.append(lab + " & " + " & ".join(f"{v:.3f}" for v in g) + r" \\")
    lines += [r"\midrule",
              r"\multicolumn{6}{l}{\emph{(b) Bimodal heterogeneity} "
              r"(ratio $=1$ is a single population)} \\", r"\midrule",
              r"ratio & " + " & ".join(f"{r:g}" for r in sorted(mix.ratio.unique())) + r" \\"]
    for cond, lab in [("all", "PIT-KS (all)"), ("xcal_pos", "PIT-KS ($x>0$)")]:
        g = mix[mix["cond"] == cond].groupby("ratio").pit_ks.mean()
        lines.append(lab + " & " + " & ".join(f"{v:.3f}" for v in g) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("tab_misspec.tex", "\n".join(lines))


# ---- Table 5: empirical validation ------------------------------------------ #
def table_empirical():
    e = pd.read_csv(RES / "empirical_results.csv")
    e = e[e["cond"] == "all"]
    lines = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
             r"Dataset & $T^*$ & $N$ & \%active & Method & cov$_{95}$ & CRPS & PIT-KS \\",
             r"\midrule"]
    for (ds, h), g in e.groupby(["dataset", "horizon"], sort=False):
        for i, (_, r) in enumerate(g.iterrows()):
            head = (f"{ds} & {int(h)} & {int(r.N)} & {100*r.pct_active:.1f}\\%"
                    if i == 0 else " & & & ")
            lines.append(f"{head} & {r.method} & {r.cov95:.3f} & {r.CRPS:.3f} & "
                         f"{r.pit_ks:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("tab_empirical.tex", "\n".join(lines))


if __name__ == "__main__":
    table_estimator(); table_significance(); table_conditioning()
    table_misspec(); table_empirical()
    print("\nAll tables written to", TAB)
