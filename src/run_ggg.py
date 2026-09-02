"""
Closing the misspecification loop: does the richer Pareto/GGG restore the calibration
that the misspecified Pareto/NBD loses under regular (Gamma-k) inter-purchase times?

For each (k, rep) we regenerate the SAME cohort as `run_misspec.py` (identical seed and
drawn parameters), then fit BOTH the classical Pareto/NBD and the common-k Pareto/GGG at
matched MCMC settings and score their predictive distributions with randomized PIT, CRPS
and coverage (all customers + the forecast-time x>0 subgroup). Fitting both models in one
script on one dataset makes the PNBD-vs-GGG contrast exactly paired.

Also records the recovered regularity k_hat and E(lambda) for each model, to show that
Pareto/NBD's downward bias in E(lambda) under regularity is corrected by Pareto/GGG.

Resumable + time-budgeted. Run:
    python src/run_ggg.py --reps 15 --max-seconds 1200
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams                                    # noqa: E402
from simulate_misspec import simulate_dataset_ggg                     # noqa: E402
from estimate import fit_mcmc                                        # noqa: E402
from estimate_ggg import fit_ggg, spp_predict_ggg                    # noqa: E402
from score import spp_predict, randomized_pit, coverage, crps_samples  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
K_GRID = [1.0, 1.5, 2.0, 3.0, 4.0]
N, T, HORIZON = 800, 52, 26
DRAWS, BURN, THIN = 2000, 700, 5


def pit_ks(pit):
    p = np.sort(pit)
    return float(np.max(np.abs(p - np.arange(1, len(p) + 1) / len(p))))


def _make_dataset(k, seed):
    """Reproduce run_misspec.run_one's cohort exactly (seed + param draws + sim)."""
    rng = np.random.default_rng(seed)
    p = DatasetParams(rng.uniform(.05, .25), rng.uniform(.8, 2.0),
                      rng.uniform(.03, .15), rng.uniform(.8, 2.0), N=N, T=float(T))
    df = simulate_dataset_ggg(p, k, rng=rng)
    return df, p


def run_one(k, rep, seed):
    df, truth = _make_dataset(k, seed)
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)

    mc = fit_mcmc(df, n_draws=DRAWS, burn_in=BURN, thin=THIN, seed=seed + 2)
    pred_pnbd = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(seed + 10))

    gg = fit_ggg(df, n_draws=DRAWS, burn_in=BURN, thin=THIN, seed=seed + 3)
    pred_ggg = spp_predict_ggg(gg, HORIZON, np.random.default_rng(seed + 11))

    khat = float(gg.k_draws.mean())
    el_true = truth.E_lambda
    el_pnbd = mc.pop_summary()["E_lambda"]
    el_ggg = gg.pop_summary()["E_lambda"]

    rows = []
    for model, pred in [("PNBD", pred_pnbd), ("GGG", pred_ggg)]:
        for cond, mask in [("all", np.ones(len(y), bool)), ("xcal_pos", xcal > 0)]:
            if mask.sum() < 20:
                continue
            pit = randomized_pit(pred[:, mask], y[mask], np.random.default_rng(seed + 20))
            cov = coverage(pred[:, mask], y[mask])
            rows.append(dict(
                k=k, rep=rep, model=model, cond=cond, n=int(mask.sum()),
                pit_ks=pit_ks(pit),
                CRPS=float(crps_samples(pred[:, mask], y[mask]).mean()),
                cov50=cov[0.5], cov95=cov[0.95],
                mean_true=float(y[mask].mean()),
                mean_pred=float(np.median(pred[:, mask], axis=0).mean()),
                k_hat=khat, E_lambda_true=el_true,
                E_lambda_pnbd=el_pnbd, E_lambda_ggg=el_ggg))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=15)
    ap.add_argument("--max-seconds", type=float, default=1e9)
    ap.add_argument("--out", default="ggg_results.csv")
    args = ap.parse_args()
    out = RES / args.out

    all_rows, done = [], set()
    if out.exists():
        prev = pd.read_csv(out)
        all_rows = prev.to_dict("records")
        done = {(float(r["k"]), int(r["rep"])) for _, r in prev.iterrows()}
        print(f"[resume] {len(done)} cells done", flush=True)

    np.seterr(over="ignore", invalid="ignore", divide="ignore")
    t0 = time.time()
    for k in K_GRID:
        for rep in range(args.reps):
            if (k, rep) in done:
                continue
            if time.time() - t0 > args.max_seconds:
                pd.DataFrame(all_rows).to_csv(out, index=False)
                print(f"[budget] stopped ({time.time()-t0:.0f}s)", flush=True)
                return
            t = time.time()
            all_rows.extend(run_one(k, rep, seed=int(1000 * k) + rep))
            pd.DataFrame(all_rows).to_csv(out, index=False)
            print(f"k={k} rep={rep} ({time.time()-t:.1f}s)", flush=True)
    print(f"[done] {len(all_rows)} rows -> {out}", flush=True)


if __name__ == "__main__":
    main()
