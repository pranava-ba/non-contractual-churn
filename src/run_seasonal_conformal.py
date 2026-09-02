"""
Does conformal recalibration repair the *calendar-conditional* seasonal bias, or only the aggregate?

Figure 8 shows the stationary model's forecast ratio (realised/predicted) tracks the forecast
window's seasonal intensity at r=+0.93 on Online Retail II. The question (a referee's sharpest one):
a static conformal warp can shift the average level, but can it fix a bias that depends on *which*
calendar window you forecast into? We answer it by rolling the cut-point and, at each window,
comparing the forecast ratio under three regimes:

  - raw                : stationary Pareto/NBD, no recalibration;
  - conformal-per-window: the paper's procedure -- the warp is learned from a held-out split of the
                          SAME cohort, whose realised outcomes fall in the SAME forecast window, then
                          applied to the test split of that window;
  - conformal-frozen   : a genuinely static warp, learned once at an anchor (near-average) window and
                          applied unchanged to every other window.

Prediction: the per-window warp is learned on same-season data, so it should flatten the ratio toward
1 at every window (r -> ~0) -- confirming the single-mechanism reading for the procedure the paper
actually uses. The frozen warp, blind to calendar position, should NOT flatten it -- confirming that a
truly static correction cannot track seasonality, and that recalibration must be refreshed per period.

Runs on Online Retail II. Saves results/seasonal_conformal_summary.csv; prints the table + correlations.
Run:  python src/run_seasonal_conformal.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import elog_to_summary                            # noqa: E402
from datasets import load_online_retail_ii                       # noqa: E402
from estimate import fit_mcmc                                    # noqa: E402
from score import spp_predict                                    # noqa: E402
from conformal import recalibrate_samples                        # noqa: E402
from run_seasonality_real import weekly_volume, seasonal_intensity  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
CAL_GRID = list(range(40, 92, 6))
HORIZON = 13
ANCHOR_INTENSITY_TARGET = 1.0     # frozen warp is learned at the window closest to "average" season


def _ratio(y, pred):
    return float(y.mean() / max(pred.mean(), 1e-9))


def main():
    elog = load_online_retail_ii()
    _, vol = weekly_volume(elog)
    rows = []
    windows = []   # keep per-window (recal pred/y, test pred/y, intensity) for the frozen pass
    t = time.time()
    for cal_weeks in CAL_GRID:
        df = elog_to_summary(elog, cal_weeks, HORIZON)
        if len(df) < 200:
            continue
        y = df[f"x_star_{HORIZON}"].to_numpy(float)
        Tcal = df["T_cal"].to_numpy(float)
        n = len(df)
        rng = np.random.default_rng(0)
        idx = rng.permutation(n)
        n_rec = n // 2
        rec, test = np.sort(idx[:n_rec]), np.sort(idx[n_rec:])
        mc = fit_mcmc(df, n_draws=1200, burn_in=400, thin=4, seed=1)
        pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(2))
        pr, yr = pred[:, rec], y[rec]
        pt, yt = pred[:, test], y[test]
        inten = seasonal_intensity(vol, cal_weeks, HORIZON)
        raw = _ratio(yt, pt)
        conf_pw = _ratio(yt, recalibrate_samples(pr, yr, pt, seed=9))
        windows.append(dict(cal_weeks=cal_weeks, inten=inten, pr=pr, yr=yr, pt=pt, yt=yt, raw=raw,
                            conf_pw=conf_pw))
        print(f"  cut={cal_weeks}w  intensity={inten:.2f}  raw={raw:.2f}  conf_pw={conf_pw:.2f}", flush=True)

    # frozen warp: pick the window whose intensity is closest to 1 as the anchor
    anchor = min(windows, key=lambda w: abs(w["inten"] - ANCHOR_INTENSITY_TARGET))
    for w in windows:
        w["conf_frozen"] = _ratio(w["yt"], recalibrate_samples(anchor["pr"], anchor["yr"], w["pt"], seed=9))
        rows.append(dict(cal_weeks=w["cal_weeks"], seasonal_intensity=w["inten"],
                         raw_ratio=w["raw"], conf_perwindow_ratio=w["conf_pw"],
                         conf_frozen_ratio=w["conf_frozen"]))
    d = pd.DataFrame(rows)
    d.to_csv(RES / "seasonal_conformal_summary.csv", index=False)

    print(f"\n=== Seasonal bias vs recalibration regime (Online Retail II, {time.time()-t:.0f}s) ===")
    print(f"(anchor window for the frozen warp: cut={anchor['cal_weeks']}w, intensity {anchor['inten']:.2f})")
    print(f"{'cal_wk':>7s}{'intensity':>10s}{'raw':>8s}{'per-window':>12s}{'frozen':>9s}")
    for _, r in d.iterrows():
        print(f"{int(r.cal_weeks):>7d}{r.seasonal_intensity:>10.2f}{r.raw_ratio:>8.2f}"
              f"{r.conf_perwindow_ratio:>12.2f}{r.conf_frozen_ratio:>9.2f}")

    def corr(col):
        return np.corrcoef(d.seasonal_intensity, d[col])[0, 1]
    print("\ncorrelation of forecast ratio with seasonal intensity:")
    print(f"  raw:               r = {corr('raw_ratio'):+.2f}   (the Fig-8 effect)")
    print(f"  conformal per-window: r = {corr('conf_perwindow_ratio'):+.2f}   "
          f"(the paper's procedure -- should flatten)")
    print(f"  conformal frozen:  r = {corr('conf_frozen_ratio'):+.2f}   "
          f"(static warp -- should NOT flatten)")
    print(f"\n[saved] {RES/'seasonal_conformal_summary.csv'}")


if __name__ == "__main__":
    main()
