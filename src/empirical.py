"""
Empirical validation on the two public benchmarks used by Simon (2025): CDNow and
Grocery. Builds the (x, t_x, T_cal) calibration summary + true x* holdout from each
event log, fits MLE + MCMC, forms SPP predictive distributions, and scores them
(all + active customers) with the same battery as the simulation study.

Checks two things:
  1. Do the real-data forecasts show the same pattern as the simulation -
     estimator-agnostic, over-covering unconditionally, under-dispersed on actives?
  2. Do the real-data scores fall within the simulation-based range (Simon's
     validation logic), now extended to calibration?

Run:  python src/empirical.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import fit_mcmc, fit_mle                              # noqa: E402
from score import (spp_predict, conditional_individual_draws,       # noqa: E402
                   score_forecast)

DATA = Path(__file__).resolve().parent.parent / "data"
WEEK = np.timedelta64(7, "D")


def load_cdnow() -> pd.DataFrame:
    """CDNOW_sample.txt: master_id, sample_id, yyyymmdd, n_cds, dollars."""
    df = pd.read_csv(DATA / "CDNOW_sample.txt", sep=r"\s+", header=None,
                     names=["master", "cust", "date", "cds", "spend"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df[["cust", "date"]]


def load_grocery() -> pd.DataFrame:
    df = pd.read_csv(DATA / "groceryElog.csv", parse_dates=["date"])
    return df[["cust", "date"]]


def elog_to_summary(elog: pd.DataFrame, cal_weeks: int, horizon: int) -> pd.DataFrame:
    """Convert an event log to per-customer (x, t_x, T_cal, x_star_h).

    Same-day transactions are merged (standard BTYD). Time is acquisition-relative,
    in weeks. Calibration window = [cohort_start, cohort_start + cal_weeks]."""
    elog = elog.copy()
    elog["date"] = elog["date"].values.astype("datetime64[D]")
    # merge same-day purchases per customer
    elog = elog.drop_duplicates(["cust", "date"])
    t0 = elog["date"].min()
    cal_end = t0 + cal_weeks * WEEK
    fc_end = cal_end + horizon * WEEK

    rows = []
    for cust, g in elog.groupby("cust"):
        dates = np.sort(g["date"].values)
        acq = dates[0]
        if acq > cal_end:                       # acquired after calibration -> skip
            continue
        rep = dates[1:]                          # repeat purchases (exclude acquisition)
        cal_rep = rep[rep <= cal_end]
        fut_rep = rep[(rep > cal_end) & (rep <= fc_end)]
        x = len(cal_rep)
        t_x = (cal_rep[-1] - acq) / WEEK if x > 0 else 0.0
        T_cal = (cal_end - acq) / WEEK
        t_next = float((fut_rep[0] - cal_end) / WEEK) if len(fut_rep) else np.inf
        # litt = sum of log inter-purchase gaps (weeks) from acquisition through the calibration
        # repeat purchases -- the sufficient statistic that identifies the Pareto/GGG regularity k.
        if x > 0:
            gaps = np.diff(np.concatenate([[acq], cal_rep])) / WEEK
            litt = float(np.log(gaps[gaps > 0]).sum())
        else:
            litt = 0.0
        rows.append({"cust": cust, "x": x, "t_x": float(t_x), "litt": litt,
                     "T_cal": float(T_cal), f"x_star_{horizon}": len(fut_rep),
                     f"t_next_{horizon}": t_next})
    return pd.DataFrame(rows)


def validate(name: str, elog: pd.DataFrame, cal_weeks: int, horizon: int,
             sim_ranges: dict | None = None) -> dict:
    df = elog_to_summary(elog, cal_weeks, horizon)
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    active = y > 0
    print(f"\n===== {name}  (cal={cal_weeks}w, T*={horizon}w) =====")
    print(f"  N={len(df)}  mean x(cal)={df.x.mean():.2f}  "
          f"zero-repeat={100*(df.x==0).mean():.1f}%  "
          f"active in forecast={100*active.mean():.1f}%  mean x*={y.mean():.2f}")

    mle = fit_mle(df, seed=1)
    mc = fit_mcmc(df, n_draws=4000, burn_in=1500, thin=5, seed=2)
    print(f"  MLE  E(lam)={mle['E_lambda']:.3f} E(mu)={mle['E_mu']:.3f} | "
          f"MCMC E(lam)={mc.pop_summary()['E_lambda']:.3f} "
          f"E(mu)={mc.pop_summary()['E_mu']:.3f}")

    lam, mu, tau = conditional_individual_draws(
        df, mle["r"], mle["alpha"], mle["s"], mle["beta"], n_draws=400, seed=3)
    preds = {
        "MCMC": spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(10)),
        "MLE": spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(11)),
    }
    xcal = df["x"].to_numpy(float)
    conds = [("all", np.ones(len(y), bool)),
             ("xcal_pos", xcal > 0),        # forecast-time covariate (valid)
             ("active", active)]            # outcome-conditioned (artefact; reported only)
    rows = []
    for method, pred in preds.items():
        for cond, mask in conds:
            sc = score_forecast(pred[:, mask], y[mask], np.random.default_rng(5))
            sc.pop("_pit", None)
            rows.append(dict(dataset=name, cal_weeks=cal_weeks, horizon=horizon,
                             N=len(df), method=method, cond=cond, n=int(mask.sum()),
                             pct_active=float(active.mean()),
                             mean_x_cal=float(df.x.mean()),
                             E_lambda_mle=mle["E_lambda"],
                             E_lambda_mcmc=mc.pop_summary()["E_lambda"], **sc))
    for cond, _ in conds:
        print(f"  --- {cond} ---")
        for method in ["MCMC", "MLE"]:
            s = next(r for r in rows if r["method"] == method and r["cond"] == cond)
            print(f"    {method:5s}  cov50={s['cov50']:.2f} cov95={s['cov95']:.2f} "
                  f"CRPS={s['CRPS']:.3f} nMAE={s['nMAE']:.3f} PIT-KS={s['pit_ks']:.3f}")
    return rows


def main():
    print("Empirical validation of the calibration study on public CBA benchmarks")
    cdnow, grocery = load_cdnow(), load_grocery()
    rows = []
    rows += validate("CDNow", cdnow, cal_weeks=39, horizon=26)
    rows += validate("CDNow", cdnow, cal_weeks=39, horizon=13)
    rows += validate("Grocery", grocery, cal_weeks=52, horizon=26)
    rows += validate("Grocery", grocery, cal_weeks=52, horizon=52)
    out = Path(__file__).resolve().parent.parent / "results" / "empirical_results.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
