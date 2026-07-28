"""
Mixture-heterogeneity stress-test: fit Pareto/NBD (single-gamma heterogeneity) to
data whose purchase-rate heterogeneity is a 2-segment mixture (light + heavy buyers)
and measure calibration as the segment separation `ratio` grows.

ratio=1 -> single population (gamma baseline, calibrated); ratio>1 -> increasingly
bimodal, violating the gamma assumption. Scored with randomized PIT (all + x>0),
CRPS, coverage. Resumable + budgeted.

Run:  python src/run_mixture.py --reps 15 --max-seconds 500
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_misspec import simulate_dataset_mixture             # noqa: E402
from estimate import fit_mcmc                                     # noqa: E402
from score import spp_predict, randomized_pit, coverage, crps_samples  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
RATIO_GRID = [1.0, 2.0, 4.0, 6.0, 10.0]
N, T, HORIZON = 800, 52, 26


def pit_ks(pit):
    p = np.sort(pit)
    return float(np.max(np.abs(p - np.arange(1, len(p) + 1) / len(p))))


def run_one(ratio, rep, seed):
    rng = np.random.default_rng(seed)
    E_lambda = rng.uniform(.08, .20)
    E_mu = rng.uniform(.03, .12)
    CV_mu = rng.uniform(.8, 1.8)
    df = simulate_dataset_mixture(N, float(T), E_lambda, ratio, E_mu, CV_mu, rng=rng)
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=2500, burn_in=900, thin=5, seed=seed + 2)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(seed + 10))
    rows = []
    for cond, mask in [("all", np.ones(len(y), bool)), ("xcal_pos", xcal > 0)]:
        if mask.sum() < 20:
            continue
        pit = randomized_pit(pred[:, mask], y[mask], np.random.default_rng(seed + 20))
        cov = coverage(pred[:, mask], y[mask])
        rows.append(dict(ratio=ratio, rep=rep, cond=cond, n=int(mask.sum()),
                         pit_ks=pit_ks(pit),
                         CRPS=float(crps_samples(pred[:, mask], y[mask]).mean()),
                         cov50=cov[0.5], cov95=cov[0.95]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=15)
    ap.add_argument("--max-seconds", type=float, default=1e9)
    ap.add_argument("--out", default="mixture_results.csv")
    args = ap.parse_args()
    out = RES / args.out

    all_rows, done = [], set()
    if out.exists():
        prev = pd.read_csv(out)
        all_rows = prev.to_dict("records")
        done = {(float(r["ratio"]), int(r["rep"])) for _, r in prev.iterrows()}
        print(f"[resume] {len(done)} cells done", flush=True)

    np.seterr(over="ignore", invalid="ignore", divide="ignore")
    t0 = time.time()
    for ratio in RATIO_GRID:
        for rep in range(args.reps):
            if (ratio, rep) in done:
                continue
            if time.time() - t0 > args.max_seconds:
                pd.DataFrame(all_rows).to_csv(out, index=False)
                print(f"[budget] stopped ({time.time()-t0:.0f}s)", flush=True)
                return
            t = time.time()
            all_rows.extend(run_one(ratio, rep, seed=int(1000 * ratio) + rep))
            pd.DataFrame(all_rows).to_csv(out, index=False)
            print(f"ratio={ratio} rep={rep} ({time.time()-t:.1f}s)", flush=True)
    print(f"[done] {len(all_rows)} rows -> {out}", flush=True)


if __name__ == "__main__":
    main()
