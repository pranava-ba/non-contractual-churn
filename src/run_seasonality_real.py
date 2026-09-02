"""
Seasonality on REAL data: does the stationary model miscalibrate when the forecast window is
seasonally anomalous?

The simulation shows a stationary Pareto/NBD miscalibrates under an injected seasonal rate
(run_seasonality_stress.py). Here we show the same effect in the wild, with no synthetic component.
On a dataset with real seasonality (Online Retail~II, a UK gift retailer with a strong Christmas
peak; Grocery as a milder comparison) we roll the calibration cut-point so the forecast window sweeps
through the calendar. For each cut-point we fit the stationary model on the calibration history,
forecast the next horizon, and record:

  - seasonal intensity of the forecast window = mean weekly transaction volume in the forecast window
    divided by the mean weekly volume in the calibration window (1.0 = as busy as calibration);
  - the forecast ratio = mean realised future purchases / mean predicted (>1 = the stationary model
    UNDER-forecasts, <1 = OVER-forecasts);
  - PIT-KS calibration.

If seasonality is what the simulation says it is, the forecast ratio should track the seasonal
intensity (busy windows under-forecast, quiet windows over-forecast) and PIT-KS should worsen as the
window departs from the calibration average.

Saves results/seasonality_real_summary.csv; prints the table.  Run: python src/run_seasonality_real.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import load_cdnow, load_grocery, elog_to_summary, WEEK  # noqa: E402
from datasets import load_online_retail_ii                            # noqa: E402
from estimate import fit_mcmc                                         # noqa: E402
from score import spp_predict, score_forecast                        # noqa: E402


def weekly_volume(elog):
    """Transactions per week index from the cohort start; returns (t0, volume array by week)."""
    d = elog.copy()
    d["date"] = d["date"].values.astype("datetime64[D]")
    t0 = d["date"].values.min()
    wk = ((d["date"].values - t0) / WEEK).astype(int)
    n_weeks = int(wk.max()) + 1
    vol = np.bincount(wk, minlength=n_weeks).astype(float)
    return t0, vol


def seasonal_intensity(vol, cut_wk, horizon):
    """Mean weekly volume in the forecast window vs the calibration window."""
    cal = vol[:cut_wk]
    fc = vol[cut_wk:cut_wk + horizon]
    if len(cal) == 0 or len(fc) == 0 or cal.mean() == 0:
        return np.nan
    return float(fc.mean() / cal.mean())


def run(name, elog, cal_grid, horizon, mcmc_draws=1500):
    t0, vol = weekly_volume(elog)
    rows = []
    for cal_weeks in cal_grid:
        df = elog_to_summary(elog, cal_weeks, horizon)
        if len(df) < 150:
            continue
        y = df[f"x_star_{horizon}"].to_numpy(float)
        Tcal = df["T_cal"].to_numpy(float)
        mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=3)
        pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(4))
        sc = score_forecast(pred, y, np.random.default_rng(5))
        ratio = float(y.mean() / max(pred.mean(), 1e-9))
        rows.append(dict(dataset=name, cal_weeks=cal_weeks, N=len(df),
                         seasonal_intensity=seasonal_intensity(vol, cal_weeks, horizon),
                         forecast_ratio=ratio, pit_ks=sc["pit_ks"], cov95=sc["cov95"]))
    return rows


def main():
    RES = Path(__file__).resolve().parent.parent / "results"
    cases = [
        ("OnlineRetailII", load_online_retail_ii(), list(range(40, 92, 6)), 13),
        ("Grocery", load_grocery(), list(range(40, 96, 8)), 13),
    ]
    rows = []
    for name, elog, grid, h in cases:
        t = time.time()
        rows += run(name, elog, grid, h)
        print(f"[{name}] {len(grid)} cut-points done ({time.time()-t:.0f}s)", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(RES / "seasonality_real_summary.csv", index=False)

    print("\n=== Seasonality on real data: stationary model vs forecast-window seasonality ===")
    print(f"{'dataset':16s}{'cal_wk':>7s}{'N':>7s}{'seas.intens':>12s}{'fc ratio':>10s}{'PIT-KS':>8s}{'cov95':>8s}")
    for _, r in d.iterrows():
        print(f"{r.dataset:16s}{int(r.cal_weeks):>7d}{int(r.N):>7d}{r.seasonal_intensity:>12.2f}"
              f"{r.forecast_ratio:>10.2f}{r.pit_ks:>8.3f}{r.cov95:>8.3f}")
    for name, _, _, _ in cases:
        g = d[d.dataset == name].dropna()
        if len(g) < 3:
            continue
        c_ratio = np.corrcoef(g.seasonal_intensity, g.forecast_ratio)[0, 1]
        c_ks = np.corrcoef(np.abs(g.seasonal_intensity - 1.0), g.pit_ks)[0, 1]
        print(f"\n [{name}] corr(seasonal intensity, forecast ratio) = {c_ratio:+.2f}  "
              f"(busy windows under-forecast); corr(|intensity-1|, PIT-KS) = {c_ks:+.2f}")
    print(f"\n[saved] {RES/'seasonality_real_summary.csv'}")


if __name__ == "__main__":
    main()
