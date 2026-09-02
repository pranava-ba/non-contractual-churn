"""
Full seasonal extension: hardens the minimal spike (run_seasonal_structural.py) into something
paper-ready by fixing its three caveats.

Minimal finding: scaling each customer's forecast-window rate by the *market-volume* seasonal
intensity over-corrects (directional bias +0.93 -> -0.78), because aggregate volume carries
new-customer acquisition, which swings more than the existing cohort's repeat rate. A hand-tuned
damped loading beta~0.58 fixed it but was in-sample.

Full version:
  1. PRINCIPLED PROFILE SOURCE. Build the seasonal multiplier from the cohort's REPEAT purchases
     (every transaction except each customer's first), not total market volume. This is the rate the
     Pareto/NBD actually models, so the multiplier is correctly scaled and needs no ad-hoc damping.
  2. LEVEL-RECAL STACK. Any residual *level* bias (the seasonal term fixes the calendar-conditional
     slope, not the overall level) is closed by the existing conformal recalibration on top.
  3. VALIDATION BEYOND ONE COHORT. Online Retail II (strong seasonality), Grocery (mild), and a
     controlled simulated DGP with a KNOWN sinusoidal amplitude (ground truth for the repair).
Plus an honest out-of-sample check: a single loading beta estimated by leave-one-window-out on the
repeat-purchase multiplier -- if the principled source is right, beta stays ~1.

Every regime is scored on the same held-out test half of each window, so the level-recal stack (which
needs a recalibration split) is compared like-for-like. Saves results/seasonal_full_summary.csv.
Run:  python src/run_seasonal_full.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import elog_to_summary, load_grocery, WEEK           # noqa: E402
from datasets import load_online_retail_ii                          # noqa: E402
from estimate import fit_mcmc                                       # noqa: E402
from score import score_forecast                                   # noqa: E402
from conformal import recalibrate_samples                          # noqa: E402
from run_seasonality_real import weekly_volume, seasonal_intensity  # noqa: E402
from run_seasonal_structural import seasonal_profile, calendar_multiplier, spp_scaled, _ratio  # noqa: E402
from run_seasonality_stress import _sim_customer                    # noqa: E402
from simulate import DatasetParams                                 # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
PERIOD = 52


def repeat_weekly_volume(elog):
    """Weekly count of REPEAT transactions only (drops each customer's first purchase / acquisition),
    binned by week from the cohort start. This is the cohort-rate seasonal shape the Pareto/NBD models,
    free of the new-customer acquisition swing that inflates total market volume."""
    d = elog.drop_duplicates(["cust", "date"]).copy()
    d["date"] = d["date"].values.astype("datetime64[D]")
    t0 = d["date"].values.min()
    d = d.sort_values(["cust", "date"])
    rep = d[d.duplicated("cust")]                    # every purchase after the first, per customer
    all_wk = ((d["date"].values - t0) / WEEK).astype(int)
    n_weeks = int(all_wk.max()) + 1
    wk = ((rep["date"].values - t0) / WEEK).astype(int)
    return t0, np.bincount(wk, minlength=n_weeks).astype(float)


def simulate_seasonal_elog(A, seed, N=3000, n_weeks=160, horizon=13,
                           E_lambda=0.15, CV_lambda=1.3, E_mu=0.02, CV_mu=1.2):
    """A synthetic event log with a KNOWN calendar-locked seasonal intensity
    lambda_i * (1 + A sin(2 pi t / 52)). Customers are acquired across the calendar so a rolling
    cut-point sweeps the seasonal cycle, exactly like the real-data runners. Ground truth for the
    repair: at A>0 the stationary model must miscalibrate and the seasonal term must fix it."""
    rng = np.random.default_rng(seed)
    p = DatasetParams(E_lambda=E_lambda, CV_lambda=CV_lambda, E_mu=E_mu, CV_mu=CV_mu, N=N, T=52.0)
    lam = rng.gamma(p.r, 1.0 / p.alpha, size=N)
    mu = rng.gamma(p.s, 1.0 / p.beta, size=N)
    life = rng.exponential(1.0 / np.maximum(mu, 1e-6))          # lifetime from acquisition (weeks)
    acq = rng.uniform(0.0, n_weeks - horizon - 1, size=N)       # calendar acquisition week
    t0 = np.datetime64("2018-01-01")
    cust, date = [], []
    for i in range(N):
        end = min(life[i], n_weeks - acq[i])
        ev = _sim_customer(lam[i], life[i], A, end, acq[i], rng)  # weeks since acq; seasonal by calendar
        weeks = acq[i] + np.concatenate([[0.0], ev])             # include acquisition at offset 0
        days = np.round(weeks * 7).astype(int)
        cust.extend([i] * len(weeks))
        date.extend(t0 + days.astype("timedelta64[D]"))
    return pd.DataFrame({"cust": cust, "date": date})


def run_dataset(name, elog, cal_grid, horizon, mcmc_draws=1200):
    _, tot_vol = weekly_volume(elog)
    _, rep_vol = repeat_weekly_volume(elog)
    prof_mkt = seasonal_profile(tot_vol)
    prof_rep = seasonal_profile(rep_vol)
    rows = []
    for cut in cal_grid:
        df = elog_to_summary(elog, cut, horizon)
        if len(df) < 200:
            continue
        y = df[f"x_star_{horizon}"].to_numpy(float)
        Tcal = df["T_cal"].to_numpy(float)
        n = len(df)
        rng = np.random.default_rng(0)
        idx = rng.permutation(n)
        rec, tst = np.sort(idx[:n // 2]), np.sort(idx[n // 2:])
        mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=400, thin=4, seed=1)

        inten = seasonal_intensity(tot_vol, cut, horizon)          # realised market intensity
        m_mkt = calendar_multiplier(prof_mkt, cut, horizon)        # market-profile multiplier (minimal)
        m_rep = calendar_multiplier(prof_rep, cut, horizon)        # repeat-profile multiplier (full)

        def pred(m, s):
            return spp_scaled(mc.lam, mc.tau, Tcal, horizon, m, np.random.default_rng(s))
        p_raw, p_mkt, p_rep = pred(1.0, 2), pred(m_mkt, 3), pred(m_rep, 4)
        # conformal LEVEL recal on the stationary predictive (no seasonal term) -- the baseline the
        # seasonal term must beat; and seasonal + conformal (the full stack).
        p_recal = recalibrate_samples(p_raw[:, rec], y[rec], p_raw[:, tst], seed=10)
        p_stack = recalibrate_samples(p_rep[:, rec], y[rec], p_rep[:, tst], seed=9)

        yt = y[tst]

        def sc(pred_test, s):
            return score_forecast(pred_test, yt, np.random.default_rng(s))
        s_raw, s_mkt, s_rep = sc(p_raw[:, tst], 5), sc(p_mkt[:, tst], 6), sc(p_rep[:, tst], 7)
        s_rec, s_stk = sc(p_recal, 11), sc(p_stack, 8)

        rows.append(dict(
            dataset=name, cut=cut, N=n, intensity=inten, m_mkt=m_mkt, m_rep=m_rep,
            ratio_raw=_ratio(yt, p_raw[:, tst]), ratio_mkt=_ratio(yt, p_mkt[:, tst]),
            ratio_rep=_ratio(yt, p_rep[:, tst]), ratio_recal=_ratio(yt, p_recal),
            ratio_stack=_ratio(yt, p_stack),
            ks_raw=s_raw["pit_ks"], ks_mkt=s_mkt["pit_ks"], ks_rep=s_rep["pit_ks"],
            ks_recal=s_rec["pit_ks"], ks_stack=s_stk["pit_ks"],
            crps_raw=s_raw["CRPS"], crps_rep=s_rep["CRPS"], crps_recal=s_rec["CRPS"], crps_stack=s_stk["CRPS"]))
        print(f"  [{name}] cut={cut}w intens={inten:.2f} m_rep={m_rep:.2f}  "
              f"ratio raw/rep/recal/stack={rows[-1]['ratio_raw']:.2f}/{rows[-1]['ratio_rep']:.2f}/"
              f"{rows[-1]['ratio_recal']:.2f}/{rows[-1]['ratio_stack']:.2f}  "
              f"KS raw/recal/stack={rows[-1]['ks_raw']:.3f}/{rows[-1]['ks_recal']:.3f}/{rows[-1]['ks_stack']:.3f}", flush=True)
    return pd.DataFrame(rows)


def oos_beta(g):
    """Leave-one-window-out loading beta on the repeat-profile multiplier: for each window, fit
    beta on the OTHER windows (least squares raw_ratio ~ 1 + beta*(m_rep-1)), predict this window's
    adjusted ratio out-of-sample. Returns (mean beta, directional r of the OOS-adjusted ratio)."""
    I = g.intensity.values
    R = g.ratio_raw.values
    X = g.m_rep.values - 1.0
    betas, adj = [], []
    for k in range(len(g)):
        m = np.ones(len(g), bool); m[k] = False
        b = float(np.dot(X[m], R[m] - 1.0) / max(np.dot(X[m], X[m]), 1e-9))  # LS through raw_ratio=1+bX
        betas.append(b)
        adj.append(R[k] / (1.0 + b * X[k]))
    adj = np.array(adj)
    r = float(np.corrcoef(I, adj)[0, 1]) if len(g) > 2 else np.nan
    return float(np.mean(betas)), r


def summarise(g):
    def corr(c):
        return float(np.corrcoef(g.intensity, g[c])[0, 1]) if len(g) > 2 else np.nan
    b_oos, r_oos = oos_beta(g)
    print(f"\n  directional bias r (0 = removed):  "
          f"raw {corr('ratio_raw'):+.2f} | seasonal-rep {corr('ratio_rep'):+.2f} | "
          f"conformal-alone {corr('ratio_recal'):+.2f} | seasonal+conformal {corr('ratio_stack'):+.2f} | "
          f"OOS-beta(rep) {r_oos:+.2f} (beta={b_oos:.2f})")
    print(f"  mean PIT-KS:  raw {g.ks_raw.mean():.3f} | seasonal-rep {g.ks_rep.mean():.3f} | "
          f"conformal-alone {g.ks_recal.mean():.3f} | seasonal+conformal {g.ks_stack.mean():.3f}")
    print(f"  forecast-ratio range (1=unbiased):  raw {g.ratio_raw.min():.2f}-{g.ratio_raw.max():.2f}"
          f" | conformal-alone {g.ratio_recal.min():.2f}-{g.ratio_recal.max():.2f}"
          f" | seasonal+conformal {g.ratio_stack.min():.2f}-{g.ratio_stack.max():.2f}")


def main():
    t = time.time()
    cases = [
        ("OnlineRetailII", load_online_retail_ii(), list(range(40, 92, 6)), 13),
        ("Grocery", load_grocery(), list(range(40, 96, 8)), 13),
        ("SimSeasonal(A=0.6)", simulate_seasonal_elog(0.6, seed=11), list(range(60, 148, 8)), 13),
    ]
    all_rows = []
    for name, elog, grid, h in cases:
        tt = time.time()
        g = run_dataset(name, elog, grid, h)
        all_rows.append(g)
        print(f"[{name}] {len(g)} windows ({time.time()-tt:.0f}s)")
        summarise(g.dropna())

    d = pd.concat(all_rows, ignore_index=True)
    d.to_csv(RES / "seasonal_full_summary.csv", index=False)
    print(f"\n[saved] {RES/'seasonal_full_summary.csv'}   (total {time.time()-t:.0f}s)")


if __name__ == "__main__":
    main()
