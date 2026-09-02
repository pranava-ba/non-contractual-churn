"""
Gap D3 (un-parked at user request): data-quality / transaction-censoring robustness.

Real CRM logs are imperfect: loyalty-ID mismatches and integration gaps drop transactions. The
simulated study assumes perfect logging. We randomly drop a fraction p of *repeat* calibration
transactions from a real event log (acquisitions kept, so the cohort is stable and the forecast
target x* -- which lives in the future window -- is untouched), refit, and measure how much the
forecast degrades. This directly probes how sensitive the calibration finding is to the kind of
missingness practitioners actually face.

Runs on CDNow. Saves results/censoring_stress_summary.csv; prints the table.

Run:  python src/run_censoring_stress.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import load_cdnow, load_grocery, elog_to_summary, WEEK  # noqa: E402
from estimate import fit_mcmc                                          # noqa: E402
from score import spp_predict, score_forecast                         # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 5
DROP = [0.0, 0.05, 0.15, 0.30]
HORIZON = 26


def censor_repeat_cal(elog, cal_weeks, p, seed):
    """Drop a fraction p of each customer's repeat (non-acquisition) transactions in the
    calibration window; keep acquisitions and all post-calibration events."""
    elog = elog.copy()
    elog["date"] = elog["date"].values.astype("datetime64[D]")
    elog = elog.drop_duplicates(["cust", "date"]).sort_values(["cust", "date"])
    t0 = elog["date"].min()
    cal_end = t0 + cal_weeks * WEEK
    rng = np.random.default_rng(seed)
    keep = np.ones(len(elog), bool)
    arr = elog.to_numpy()
    cust_col = elog.columns.get_loc("cust"); date_col = elog.columns.get_loc("date")
    seen = {}
    for i in range(len(elog)):
        c = arr[i, cust_col]; d = arr[i, date_col]
        first = c not in seen
        seen[c] = True
        if (not first) and d <= cal_end and rng.uniform() < p:
            keep[i] = False
    return elog[keep]


def one(name, elog, p, seed, cal_weeks, mcmc_draws=1500):
    df = elog_to_summary(censor_repeat_cal(elog, cal_weeks, p, seed), cal_weeks, HORIZON)
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(seed + 2))
    sc = score_forecast(pred, y, np.random.default_rng(seed + 3))
    return dict(dataset=name, drop=p, seed=seed, N=len(df), mean_x=float(df.x.mean()),
                E_lambda=mc.pop_summary()["E_lambda"], CRPS=sc["CRPS"], pit_ks=sc["pit_ks"],
                cov95=sc["cov95"], nMAE=sc["nMAE"])


def main():
    cases = [("CDNow", load_cdnow(), 39), ("Grocery", load_grocery(), 52)]
    rows = []
    for name, elog, cal in cases:
        t = time.time()
        for p in DROP:
            for seed in range(SEEDS):
                rows.append(one(name, elog, p, 11000 + seed, cal))
        print(f"[{name}] {len(DROP)} drop-levels x {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)
    raw = pd.DataFrame(rows)
    summ = raw.groupby(["dataset", "drop"]).mean(numeric_only=True).drop(columns="seed").reset_index()
    summ.to_csv(RES / "censoring_stress_summary.csv", index=False)

    print("\n=== Transaction-censoring robustness (drop repeat calibration events, MCMC) ===")
    print(f"{'dataset':10s}{'drop%':>7s}{'N':>7s}{'mean_x':>8s}{'E[lam]':>8s}{'PIT-KS':>8s}"
          f"{'cov95':>8s}{'CRPS':>8s}{'nMAE':>8s}")
    for _, r in summ.iterrows():
        print(f"{r.dataset:10s}{100*r['drop']:>6.0f}%{int(r.N):>7d}{r.mean_x:>8.2f}{r.E_lambda:>8.3f}"
              f"{r.pit_ks:>8.3f}{r.cov95:>8.3f}{r.CRPS:>8.3f}{r.nMAE:>8.3f}")
    for ds, _, _ in cases:
        g = summ[summ.dataset == ds]
        b = g[g["drop"] == 0.0].iloc[0]; w = g[g["drop"] == 0.30].iloc[0]
        print(f"  [{ds}] 0%->30% drop:  E[lam] {b.E_lambda:.3f}->{w.E_lambda:.3f}, "
              f"PIT-KS {b.pit_ks:.3f}->{w.pit_ks:.3f}, nMAE {b.nMAE:.3f}->{w.nMAE:.3f}")
    print(f"\n[saved] {RES/'censoring_stress_summary.csv'}")


if __name__ == "__main__":
    main()
