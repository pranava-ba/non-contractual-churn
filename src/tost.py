"""
Equivalence testing (TOST) for the manuscript's "immaterial / equivalent" claims.

A non-significant paired test does not establish equivalence; two one-sided tests (TOST) against a
pre-declared margin do. The manuscript's methods section promises TOST for every equivalence claim;
this module delivers it for the three that matter:

  - amortized inference  vs MCMC   (Section: estimation invariant)
  - Pareto/NBD           vs BG/NBD (Section: variant invariant)
  - MLE plug-in          vs MCMC   (the foundational estimator-equivalence)

Pre-declared margins (fixed before looking at the outcomes):
  - CRPS: a RELATIVE margin of +/-5%. Two forecasters are equivalent in accuracy if their per-
    replicate CRPS differ, on average, by less than 5% -- a scale-free bound that pools cleanly across
    cohorts whose CRPS ranges from ~0.4 to ~7.
  - PIT-KS: an ABSOLUTE margin of +/-0.02 -- calibration is equivalent if the paired PIT-KS differ by
    less than 0.02 (calibrated forecasts sit at 0.02-0.06, so this is a tight, meaningful bound).

TOST at alpha=0.05 is equivalent to the 90% CI of the paired difference lying entirely inside the
margin, which is what we report.

Saves results/tost_summary.csv; prints the table.  Run:  python src/tost.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RES = Path(__file__).resolve().parent.parent / "results"
REL_MARGIN = 0.05      # +/-5% relative CRPS
KS_MARGIN = 0.02       # +/-0.02 absolute PIT-KS


def tost_diff(d, margin):
    """TOST on a vector of paired differences d against the equivalence margin +/-`margin`."""
    d = np.asarray(d, float)
    n = len(d)
    mean = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(n))
    tcrit = stats.t.ppf(0.95, n - 1)
    ci = (mean - tcrit * se, mean + tcrit * se)
    p_lower = stats.t.sf((mean + margin) / se, n - 1)     # H0: mean <= -margin
    p_upper = stats.t.cdf((mean - margin) / se, n - 1)    # H0: mean >= +margin
    p_tost = float(max(p_lower, p_upper))
    return dict(n=n, mean=mean, ci_lo=ci[0], ci_hi=ci[1], margin=margin,
                p_tost=p_tost, equivalent=bool(p_tost < 0.05))


def _paired(df, index, method_col, value_col, a, b):
    """Return aligned paired arrays (method a, method b) over the pivot index."""
    w = df.pivot_table(index=index, columns=method_col, values=value_col)
    w = w.dropna(subset=[a, b])
    return w[a].to_numpy(float), w[b].to_numpy(float)


def crps_equiv(name, a_vals, b_vals):
    rel = (a_vals - b_vals) / (0.5 * (a_vals + b_vals))   # scale-free relative difference
    r = tost_diff(rel, REL_MARGIN)
    return dict(comparison=name, metric="CRPS (rel.)", **r)


def ks_equiv(name, a_vals, b_vals):
    r = tost_diff(a_vals - b_vals, KS_MARGIN)
    return dict(comparison=name, metric="PIT-KS (abs.)", **r)


def main():
    rows = []

    # 1) MLE plug-in vs MCMC -- from the main simulation grid (per N,T,rep,horizon, cond=all)
    m = pd.read_csv(RES / "main_results.csv")
    m = m[m["cond"] == "all"]
    for metric, fn in [("CRPS", crps_equiv), ("pit_ks", ks_equiv)]:
        a, b = _paired(m, ["N", "T", "rep", "horizon"], "method", metric, "MCMC", "MLE_plugin")
        rows.append(fn("MLE vs MCMC", a, b))

    # 2) Pareto/NBD vs BG/NBD -- per (dataset, seed), pooled on the scale-free relative CRPS
    bg = pd.read_csv(RES / "bgnbd_study_raw.csv")
    for metric, fn in [("CRPS", crps_equiv), ("pit_ks", ks_equiv)]:
        d = bg[bg["metric"] == metric]
        a, b = _paired(d, ["dataset", "seed"], "model", "value", "ParetoNBD", "BGNBD")
        rows.append(fn("Pareto/NBD vs BG/NBD", a, b))

    # 3) Amortized vs MCMC -- per held-out cohort
    ah = RES / "amortized_heldout_raw.csv"
    if ah.exists():
        am = pd.read_csv(ah)
        for metric, fn in [("CRPS", crps_equiv), ("pit_ks", ks_equiv)]:
            d = am[am["metric"] == metric]
            a, b = _paired(d, ["cohort"], "method", "value", "MCMC", "Amortized")
            rows.append(fn("Amortized vs MCMC", a, b))
    else:
        print(f"[warn] {ah.name} not found -- run run_amortized_check.py first for the amortized pair.")

    out = pd.DataFrame(rows)
    out.to_csv(RES / "tost_summary.csv", index=False)

    print("=== Equivalence (TOST) for the paper's 'immaterial' claims ===")
    print(f"margins: CRPS +/-{REL_MARGIN:.0%} relative, PIT-KS +/-{KS_MARGIN} absolute; "
          f"equivalent iff 90% CI inside the margin\n")
    print(f"{'comparison':22s}{'metric':16s}{'n':>4s}{'mean diff':>11s}{'90% CI':>20s}"
          f"{'p_TOST':>9s}  verdict")
    for _, r in out.iterrows():
        unit = "%" if "rel" in r["metric"] else ""
        scale = 100 if "rel" in r["metric"] else 1
        ci = f"[{scale*r.ci_lo:+.2f}, {scale*r.ci_hi:+.2f}]{unit}"
        verdict = "EQUIVALENT" if r.equivalent else "not shown"
        print(f"{r.comparison:22s}{r.metric:16s}{int(r.n):>4d}{scale*r['mean']:>+10.2f}{unit}"
              f"{ci:>20s}{r.p_tost:>9.3f}  {verdict}")
    print(f"\n[saved] {RES/'tost_summary.csv'}")


if __name__ == "__main__":
    main()
