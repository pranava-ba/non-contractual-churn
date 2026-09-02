"""
Gap V2: a profit-linked decision layer over the active-customer / Top-A% forecasts.

Simon's metrics (sensitivity, precision, accuracy, CRPS) are purely statistical. Practitioners act
on a forecast: they contact a targeted subset in a retention/upsell campaign. We monetise that
decision. With a margin M per future repeat purchase and a contact cost c per targeted customer, the
expected profit of contacting customer i is M*E[x*_i] - c, so the optimal policy contacts everyone
whose predicted expected purchases clear the break-even c/M. Realised profit is then

    profit(method) = sum over contacted i of ( M * y_i - c ),      y_i = realised x*_i,

and we rank methods by profit -- and by the share of the oracle (perfect-foresight) profit they
capture -- instead of by accuracy alone. A second policy (Top-A%) contacts the A% with the highest
predicted value and reports the realised value captured vs the oracle Top-A%.

Methods: BTYD (Pareto/NBD, MCMC), heuristic (Simon eq.13), Poisson-GBM. Everything is evaluated on
the same held-out test split; BTYD is unsupervised, the GBM trains on the train split.

Saves results/profit_study_summary.csv; prints the profit table.

Run:  python src/run_profit_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml_benchmark import rfm_features, poisson_gbm_forecast     # noqa: E402
from run_study import heuristic_point                           # noqa: E402
from run_ml_study import build_providers                        # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 6
MARGIN = 1.0                       # margin per future repeat purchase (normalised)
COSTS = [0.2, 0.5, 1.0]            # contact cost per targeted customer (break-even E[x*] = c/M)
TOP_A = 0.10                       # Top-A% policy fraction
DATASETS = ["Simulated", "CDNow", "OnlineRetailII", "Dunnhumby"]


def _predictive_means(df, horizon, test_idx, train_idx, seed, mcmc_draws=1200):
    """Per-customer predicted E[x*] on the test split for each method."""
    from estimate import fit_mcmc
    from score import spp_predict

    Tcal = df["T_cal"].to_numpy(float)
    y = df[f"x_star_{horizon}"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=400, thin=4, seed=seed + 1)
    e_btyd = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon,
                         np.random.default_rng(seed + 2)).mean(axis=0)[test_idx]
    e_heur = heuristic_point(df, horizon)[test_idx]
    X = rfm_features(df)
    e_gbm = poisson_gbm_forecast(X[train_idx], y[train_idx], X[test_idx],
                                 seed=seed + 3).mean(axis=0)
    return {"BTYD": e_btyd, "heuristic": e_heur, "PoissonGBM": e_gbm}


def profit_for(pred_mean, y_test, margin, cost):
    """Realised profit of the contact policy: target everyone with M*E[x*] >= c."""
    contact = margin * pred_mean >= cost
    return float(np.sum((margin * y_test - cost)[contact]))


def topa_capture(pred_mean, y_test, frac):
    """Realised value captured by targeting the top-`frac` predicted customers,
    as a share of the oracle top-`frac` realised value."""
    n = len(y_test)
    k = max(1, int(round(frac * n)))
    got = np.sort(y_test[np.argsort(-pred_mean)[:k]]).sum()
    best = np.sort(y_test)[::-1][:k].sum()
    return float(got / best) if best > 0 else np.nan


def main():
    providers = build_providers()
    methods = ["BTYD", "heuristic", "PoissonGBM"]
    rows = []
    for name in DATASETS:
        get = providers[name]
        t = time.time()
        for seed in range(SEEDS):
            df, h = get(seed)
            y = df[f"x_star_{h}"].to_numpy(float)
            xcal = df["x"].to_numpy(float)
            n = len(df)
            rng = np.random.default_rng(1000 + seed)
            idx = rng.permutation(n)
            n_test = int(round(0.3 * n))
            test_idx, train_idx = np.sort(idx[:n_test]), np.sort(idx[n_test:])
            y_test = y[test_idx]
            means = _predictive_means(df, h, test_idx, train_idx, seed=4000 + seed)

            for c in COSTS:
                oracle = float(np.sum(np.maximum(MARGIN * y_test - c, 0.0)))
                for m in methods:
                    pr = profit_for(means[m], y_test, MARGIN, c)
                    rows.append(dict(dataset=name, seed=seed, cost=c, method=m,
                                     profit=pr, oracle=oracle,
                                     pct_oracle=100 * pr / oracle if oracle > 0 else np.nan))
            for m in methods:
                rows.append(dict(dataset=name, seed=seed, cost="topA", method=m,
                                 profit=topa_capture(means[m], y_test, TOP_A),
                                 oracle=1.0, pct_oracle=100 * topa_capture(means[m], y_test, TOP_A)))
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    raw.to_csv(RES / "profit_study_raw.csv", index=False)
    summ = raw.groupby(["dataset", "cost", "method"]).agg(
        profit=("profit", "mean"), pct_oracle=("pct_oracle", "mean")).reset_index()
    summ.to_csv(RES / "profit_study_summary.csv", index=False)

    print("\n=== Contact-policy profit as % of oracle (mean over seeds) ===")
    for c in COSTS:
        print(f"\n contact cost c={c} (break-even E[x*]={c/MARGIN:.2f}):")
        print(f"  {'dataset':16s}" + "".join(f"{m:>13s}" for m in methods))
        for ds in DATASETS:
            cells = ""
            for m in methods:
                r = summ[(summ.dataset == ds) & (summ.cost == c) & (summ.method == m)]
                cells += f"{r['pct_oracle'].iloc[0]:>12.1f}%" if not r.empty else f"{'-':>13s}"
            print(f"  {ds:16s}{cells}")
    print("\n=== Top-10% targeting: realised value captured vs oracle (%) ===")
    print(f"  {'dataset':16s}" + "".join(f"{m:>13s}" for m in methods))
    for ds in DATASETS:
        cells = ""
        for m in methods:
            r = summ[(summ.dataset == ds) & (summ.cost == "topA") & (summ.method == m)]
            cells += f"{r['pct_oracle'].iloc[0]:>12.1f}%" if not r.empty else f"{'-':>13s}"
        print(f"  {ds:16s}{cells}")
    print(f"\n[saved] {RES/'profit_study_summary.csv'}")


if __name__ == "__main__":
    main()
