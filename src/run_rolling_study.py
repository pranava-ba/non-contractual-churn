"""
Gaps F1 (rolling / walk-forward) and F3 (segment-transition / tenure).

F1 -- Simon (2025) uses a single calibration/holdout split per dataset. We refit at multiple
calibration cut-points as the window rolls forward and track whether each method's accuracy,
calibration, and the MCMC-vs-MLE ranking are stable over time.

F3 -- Top-A% membership is evaluated once per horizon; nobody asks how *durable* it is. We frame
Top-A% membership as a tenure process: split the history into consecutive windows, rank customers by
realised purchases in each, and measure the period-to-period retention of Top-A% status. A geometric
tenure model then gives the expected number of consecutive periods a customer stays in the top
segment -- a segment-tenure forecast the classical pipeline never produces.

Both run on the public event logs (CDNow, Grocery). Saves results/rolling_summary.csv and
results/segment_tenure_summary.csv; prints both tables.

Run:  python src/run_rolling_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import load_cdnow, load_grocery, elog_to_summary, WEEK   # noqa: E402
from estimate import fit_mcmc, fit_mle                                  # noqa: E402
from score import (spp_predict, conditional_individual_draws,          # noqa: E402
                   score_forecast)

RES = Path(__file__).resolve().parent.parent / "results"


# ------------------------------- F1: rolling ---------------------------------- #
def rolling_accuracy(name, elog, cal_grid, horizon, mcmc_draws=1500):
    rows = []
    for cal_weeks in cal_grid:
        df = elog_to_summary(elog, cal_weeks, horizon)
        if len(df) < 100:
            continue
        y = df[f"x_star_{horizon}"].to_numpy(float)
        Tcal = df["T_cal"].to_numpy(float)
        mle = fit_mle(df, seed=1)
        lam, mu, tau = conditional_individual_draws(df, mle["r"], mle["alpha"], mle["s"],
                                                    mle["beta"], n_draws=400, seed=2)
        mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=3)
        preds = {"MCMC": spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(10)),
                 "MLE": spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(11))}
        for m, pred in preds.items():
            sc = score_forecast(pred, y, np.random.default_rng(5))
            rows.append(dict(dataset=name, cal_weeks=cal_weeks, N=len(df), method=m,
                             mean_xstar=float(y.mean()), CRPS=sc["CRPS"], pit_ks=sc["pit_ks"],
                             cov95=sc["cov95"], nMAE=sc["nMAE"]))
    return rows


# ------------------------------ F3: segment tenure ---------------------------- #
def window_counts(elog, window_weeks, n_windows):
    """Per-customer repeat-purchase counts in consecutive calendar windows from cohort start."""
    elog = elog.copy()
    elog["date"] = elog["date"].values.astype("datetime64[D]")
    elog = elog.drop_duplicates(["cust", "date"])
    t0 = elog["date"].values.min()                    # numpy datetime64 (not a pandas Timestamp)
    custs = elog["cust"].unique()
    idx = {c: i for i, c in enumerate(custs)}
    counts = np.zeros((len(custs), n_windows))
    for cust, g in elog.groupby("cust"):
        dates = np.sort(g["date"].values)
        rep = dates[1:]                                   # exclude acquisition
        w = ((rep - t0) / WEEK / window_weeks).astype(int)
        for wi in w[(w >= 0) & (w < n_windows)]:
            counts[idx[cust], wi] += 1
    return counts


def _tenure_from_counts(C, k):
    """Expected Top-k tenure (geometric) from a window-count matrix."""
    nw = C.shape[1]
    top = np.zeros_like(C, dtype=bool)
    for w in range(nw):
        top[np.argsort(-C[:, w])[:k], w] = True
    stays, base = 0, 0
    for w in range(nw - 1):
        cur = np.where(top[:, w])[0]
        if len(cur):
            stays += top[cur, w + 1].sum(); base += len(cur)
    ret = stays / base if base else np.nan
    return (ret, 1.0 / (1.0 - ret)) if (base and ret < 1) else (ret, np.nan)


def segment_tenure(name, elog, window_weeks, n_windows, top_a=0.10, n_boot=500, seed=0):
    """Retention of Top-A% membership across consecutive windows -> expected tenure (geometric),
    with a 95% customer-bootstrap CI on the expected tenure."""
    C = window_counts(elog, window_weeks, n_windows)
    N = C.shape[0]
    k = max(1, int(round(top_a * N)))
    retention, exp_tenure = _tenure_from_counts(C, k)
    rng = np.random.default_rng(seed)
    boot = np.array([_tenure_from_counts(C[rng.integers(0, N, N)], k)[1] for _ in range(n_boot)])
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    return dict(dataset=name, window_weeks=window_weeks, n_windows=n_windows, N=N, topA=top_a,
                retention=retention, exp_tenure_periods=exp_tenure,
                exp_tenure_weeks=exp_tenure * window_weeks if np.isfinite(exp_tenure) else np.nan,
                tenure_ci_lo=float(lo), tenure_ci_hi=float(hi))


def main():
    cdnow, grocery = load_cdnow(), load_grocery()
    t = time.time()

    # F1 -- rolling calibration cut-points
    roll = []
    roll += rolling_accuracy("CDNow", cdnow, [26, 34, 42, 50, 58], horizon=13)
    roll += rolling_accuracy("Grocery", grocery, [40, 55, 70, 85], horizon=13)
    df_roll = pd.DataFrame(roll)
    df_roll.to_csv(RES / "rolling_summary.csv", index=False)
    print(f"=== F1 rolling walk-forward (fit at each cut-point, horizon 13w) [{time.time()-t:.0f}s] ===")
    print(f"{'dataset':10s}{'cal_wk':>7s}{'method':>7s}{'N':>7s}{'CRPS':>8s}{'PIT-KS':>8s}{'cov95':>8s}{'nMAE':>8s}")
    for _, r in df_roll.iterrows():
        print(f"{r.dataset:10s}{int(r.cal_weeks):>7d}{r.method:>7s}{int(r.N):>7d}"
              f"{r.CRPS:>8.3f}{r.pit_ks:>8.3f}{r.cov95:>8.3f}{r.nMAE:>8.3f}")
    # stability: sd of MCMC PIT-KS and of the MCMC-MLE CRPS gap across cut-points
    for ds in ["CDNow", "Grocery"]:
        g = df_roll[df_roll.dataset == ds]
        mc = g[g.method == "MCMC"]; ml = g[g.method == "MLE"]
        gap = (mc.set_index("cal_weeks")["CRPS"] - ml.set_index("cal_weeks")["CRPS"])
        print(f"  [{ds}] MCMC PIT-KS across cut-points: {mc.pit_ks.mean():.3f} +/- {mc.pit_ks.std():.3f}; "
              f"MCMC-MLE CRPS gap: {gap.mean():+.3f} +/- {gap.std():.3f}")

    # F3 -- segment tenure
    ten = [segment_tenure("CDNow", cdnow, window_weeks=13, n_windows=6),
           segment_tenure("Grocery", grocery, window_weeks=13, n_windows=8)]
    df_ten = pd.DataFrame(ten)
    df_ten.to_csv(RES / "segment_tenure_summary.csv", index=False)
    print("\n=== F3 Top-10% segment tenure (realised, consecutive 13-week windows) ===")
    print(f"{'dataset':10s}{'#windows':>9s}{'N':>7s}{'retention':>11s}{'tenure(periods)':>16s}{'tenure(weeks)':>15s}")
    for _, r in df_ten.iterrows():
        print(f"{r.dataset:10s}{int(r.n_windows):>9d}{int(r.N):>7d}{r.retention:>11.3f}"
              f"{r.exp_tenure_periods:>16.2f}{r.exp_tenure_weeks:>15.1f}")
    print(f"\n[saved] {RES/'rolling_summary.csv'} and {RES/'segment_tenure_summary.csv'}")


if __name__ == "__main__":
    main()
