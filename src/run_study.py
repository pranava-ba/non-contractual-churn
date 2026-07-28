"""
Batch experiment runner for the calibration study.

Sweeps a design grid, and for each replicate dataset: simulates, fits MLE + MCMC,
builds predictive distributions for each method, and scores them (point +
probabilistic, unconditional + active-conditional). Appends one tidy row per
(dataset, horizon, method) to results/results.csv.

Methods compared:
  MCMC        - full posterior predictive (SPP over posterior draws)
  MLE_plugin  - individual draws at the MLE point (no parameter uncertainty)
  MLE_boot    - individual draws over bootstrap-refit params (mode uncertainty)
  heuristic   - previous purchase rate x*/T * T*  (Simon 2025, eq. 13)

Run a fast pilot:   python src/run_study.py --pilot
Full small-sample:  python src/run_study.py --grid smallsample --reps 30
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset            # noqa: E402
from estimate import fit_mcmc, fit_mle                          # noqa: E402
from score import (spp_predict, conditional_individual_draws,   # noqa: E402
                   score_forecast)

RESULTS = Path(__file__).resolve().parent.parent / "results"
RESULTS.mkdir(exist_ok=True)

# Design grids: each entry fixes (N, T); behavioural params drawn per replicate.
GRIDS = {
    "pilot": [(300, 26), (800, 39), (2000, 52)],
    "smallsample": [(200, 26), (300, 26), (500, 39), (800, 39),
                    (1200, 52), (2000, 60)],
    # extreme: tiny cohorts + short windows -> max parameter uncertainty, the
    # regime where full-Bayes (MCMC) should beat MLE if it ever does. Pair with
    # high CV (--cvlo 1.8 --cvhi 2.5) to weaken identification of E(lambda)=r/alpha.
    "extreme": [(100, 26), (150, 26), (200, 26), (300, 39)],
}
HORIZONS = (13, 26, 52)


def heuristic_point(df, T_star):
    """Simon (2025) eq.13: x_i/T_i * T*  for repeat buyers, 0 for single buyers."""
    x = df["x"].to_numpy(float); T = df["T_cal"].to_numpy(float)
    return np.where(x > 0, x / T * T_star, 0.0)


def run_replicate(N, T, rep, seed, n_boot, mcmc_draws, mcmc_burn, mcmc_thin,
                  cv_lo=0.5, cv_hi=2.5):
    rng = np.random.default_rng(seed)
    # draw behavioural params, fix operational (N, T); CV range controls heterogeneity
    p = DatasetParams(
        E_lambda=rng.uniform(0.02, 0.30), CV_lambda=rng.uniform(cv_lo, cv_hi),
        E_mu=rng.uniform(0.02, 0.20), CV_mu=rng.uniform(cv_lo, cv_hi), N=N, T=float(T))
    df = simulate_dataset(p, rng=rng)
    Tcal = df["T_cal"].to_numpy(float)

    # ---- fits ----
    mle = fit_mle(df, seed=seed + 1)
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=mcmc_burn, thin=mcmc_thin, seed=seed + 2)
    # MLE plug-in individual draws
    lam_p, mu_p, tau_p = conditional_individual_draws(
        df, mle["r"], mle["alpha"], mle["s"], mle["beta"], n_draws=400, seed=seed + 3)
    # MLE bootstrap: refit on customer resamples (warm-started at full-data MLE),
    # then individual draws per bootstrap estimate.
    boot_lam, boot_mu, boot_tau = [], [], []
    for b in range(n_boot):
        idx = rng.integers(0, len(df), len(df))
        dfb = df.iloc[idx].reset_index(drop=True)
        try:
            mb = fit_mle(dfb, seed=seed + 100 + b, n_start=0, x0=mle["logparams"])
        except Exception:
            continue
        l, m, t = conditional_individual_draws(
            df, mb["r"], mb["alpha"], mb["s"], mb["beta"],
            n_draws=max(1, 400 // n_boot), burn_in=80, seed=seed + 200 + b)
        boot_lam.append(l); boot_mu.append(m); boot_tau.append(t)

    rows = []
    for h in HORIZONS:
        y = df[f"x_star_{h}"].to_numpy(float)
        active = y > 0
        preds = {
            "MCMC": spp_predict(mc.lam, mc.mu, mc.tau, Tcal, h, np.random.default_rng(seed + 10)),
            "MLE_plugin": spp_predict(lam_p, mu_p, tau_p, Tcal, h, np.random.default_rng(seed + 11)),
        }
        if boot_lam:
            preds["MLE_boot"] = spp_predict(
                np.vstack(boot_lam), np.vstack(boot_mu), np.vstack(boot_tau),
                Tcal, h, np.random.default_rng(seed + 12))
        # heuristic as a degenerate (point) predictive
        hp = heuristic_point(df, h)
        preds["heuristic"] = np.repeat(np.round(hp)[None, :], 50, axis=0).astype(int)

        for method, pred in preds.items():
            for cond, mask in [("all", slice(None)), ("active", active)]:
                if cond == "active" and active.sum() < 15:
                    continue
                sc = score_forecast(pred[:, mask], y[mask], np.random.default_rng(seed + 20))
                sc.pop("_pit", None)
                rows.append(dict(
                    N=N, T=T, rep=rep, horizon=h, method=method, cond=cond,
                    n_active=int(active.sum()), pct_active=float(active.mean()),
                    E_lambda=p.E_lambda, E_mu=p.E_mu, CV_lambda=p.CV_lambda, CV_mu=p.CV_mu,
                    **sc))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="pilot", choices=list(GRIDS))
    ap.add_argument("--pilot", action="store_true", help="alias for --grid pilot --reps 2")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--nboot", type=int, default=10)
    ap.add_argument("--mcmc-draws", type=int, default=3000)
    ap.add_argument("--mcmc-burn", type=int, default=1000)
    ap.add_argument("--mcmc-thin", type=int, default=5)
    ap.add_argument("--cvlo", type=float, default=0.5)
    ap.add_argument("--cvhi", type=float, default=2.5)
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--resume", action="store_true",
                    help="skip (N,T,rep) already present in --out and append")
    ap.add_argument("--max-seconds", type=float, default=1e9,
                    help="stop after this budget (partial results are saved)")
    args = ap.parse_args()
    if args.pilot:
        args.grid, args.reps = "pilot", 2

    np.seterr(over="ignore", invalid="ignore", divide="ignore")
    grid = GRIDS[args.grid]
    out = RESULTS / args.out

    # resume: preload existing rows and build the done-set of (N,T,rep)
    all_rows, done = [], set()
    if args.resume and out.exists():
        prev = pd.read_csv(out)
        all_rows = prev.to_dict("records")
        done = {(int(r["N"]), int(r["T"]), int(r["rep"])) for _, r in prev.iterrows()}
        print(f"[resume] {len(all_rows)} rows, {len(done)} cells already done", flush=True)

    t0 = time.time()
    total = len(grid) * args.reps
    k, ran = 0, 0
    for (N, T) in grid:
        for rep in range(args.reps):
            k += 1
            if (N, T, rep) in done:
                continue
            if time.time() - t0 > args.max_seconds:
                print(f"[budget] stopped after {ran} new cells "
                      f"({time.time()-t0:.0f}s)", flush=True)
                pd.DataFrame(all_rows).to_csv(out, index=False)
                return
            seed = 1000 * N + 7 * T + rep
            t = time.time()
            rows = run_replicate(N, T, rep, seed, args.nboot,
                                 args.mcmc_draws, args.mcmc_burn, args.mcmc_thin,
                                 cv_lo=args.cvlo, cv_hi=args.cvhi)
            all_rows.extend(rows); ran += 1
            pd.DataFrame(all_rows).to_csv(out, index=False)  # incremental save
            print(f"[{k}/{total}] N={N} T={T} rep={rep}  "
                  f"({time.time()-t:.1f}s, {len(rows)} rows, {len(all_rows)} total)",
                  flush=True)
    print(f"\n[done] {len(all_rows)} rows -> {out}  ({time.time()-t0:.1f}s, "
          f"{ran} new)", flush=True)


if __name__ == "__main__":
    main()
