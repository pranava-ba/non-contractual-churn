"""
Gap M2: a dedicated ML survival/hazard model for the next-purchase-timing task.

Timing is Simon's most conspicuous failure, yet the cited ML work never targeted it. Extension B
already fixed it structurally with Pareto/GGG (regular inter-purchase times); here we add the ML
answer -- a discrete-time hazard model (pooled classifier on time-expanded person-period data, the
standard way to model censored event timing) -- and run all three (Pareto/NBD, Pareto/GGG, ML
hazard) through the identical timing scorer (`timing.score_timing_forecast`) on a common held-out
split. The hazard model handles the censoring (customers who don't buy within the horizon) properly
and, unlike the parametric models, learns the hazard shape from RFM features.

Datasets: simulated with regularity k in {1,2,3} (k>1 is where GGG helps), plus CDNow and Grocery.

Saves results/ml_timing_summary.csv; prints the table.

Run:  python src/run_ml_timing_study.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams                                   # noqa: E402
from simulate_misspec import simulate_dataset_ggg                    # noqa: E402
from empirical import load_cdnow, load_grocery, elog_to_summary      # noqa: E402
from estimate import fit_mcmc                                        # noqa: E402
from estimate_ggg import fit_ggg                                     # noqa: E402
from ml_benchmark import rfm_features                                # noqa: E402
from timing import (sample_next_purchase_time_pnbd,                  # noqa: E402
                    sample_next_purchase_time_pggg, score_timing_forecast)

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 10
HORIZON = 26


def ml_hazard_timing(X_train, w_train, X_test, horizon, n_draws=200, seed=0):
    """Discrete-time hazard forecaster of the wait to next purchase (weeks).

    Person-period expansion: each training customer is 'at risk' in bins 1..b*, with an event in the
    bin they purchased (b* = ceil(w)) or censored through the horizon (w = inf). A classifier learns
    the per-bin hazard h(bin | RFM); we sample the first-event bin per draw. Returns (n_draws, N_test)
    wait samples (inf if no purchase within the horizon)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    H = int(horizon)
    Xr, bins, ev = [], [], []
    for i, w in enumerate(w_train):
        last = H if not np.isfinite(w) else min(int(np.ceil(max(w, 1e-6))), H)
        for b in range(1, last + 1):
            Xr.append(X_train[i]); bins.append(b)
            ev.append(1 if (np.isfinite(w) and b == last) else 0)
    Xr = np.column_stack([np.asarray(Xr, float), np.asarray(bins, float)])
    ev = np.asarray(ev, int)
    if ev.min() == ev.max():                              # degenerate (no events) -> all censored
        return np.full((n_draws, len(X_test)), np.inf)

    clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, max_leaf_nodes=15,
                                         min_samples_leaf=40, l2_regularization=1.0, random_state=seed)
    clf.fit(Xr, ev)

    n = len(X_test)
    haz = np.zeros((n, H))
    for b in range(1, H + 1):
        Xb = np.column_stack([X_test, np.full(n, float(b))])
        haz[:, b - 1] = clf.predict_proba(Xb)[:, 1]

    rng = np.random.default_rng(seed + 1)
    waits = np.full((n_draws, n), np.inf)
    alive = np.ones((n_draws, n), bool)
    for b in range(H):
        fire = alive & (rng.uniform(size=(n_draws, n)) < haz[:, b][None, :])
        waits[fire] = b + 0.5                             # bin centre (weeks)
        alive &= ~fire
    return waits


def run_dataset(name, df, seed):
    y_wait = df[f"t_next_{HORIZON}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float); tx = df["t_x"].to_numpy(float)
    n = len(df)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(0.3 * n))
    test = np.sort(idx[:n_test]); train = np.sort(idx[n_test:])

    mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=seed + 1)
    gg = fit_ggg(df, n_draws=1200, burn_in=400, thin=4, seed=seed + 2)
    w_p = sample_next_purchase_time_pnbd(mc.lam, mc.mu, mc.tau, Tcal, seed=seed + 3)[:, test]
    w_g = sample_next_purchase_time_pggg(gg.lam, gg.mu, gg.tau, gg.k_draws.mean(),
                                         Tcal, tx, seed=seed + 4)[:, test]
    X = rfm_features(df)
    w_ml = ml_hazard_timing(X[train], y_wait[train], X[test], HORIZON, seed=seed + 5)

    true_test = y_wait[test]
    out = {}
    for model, w in [("PNBD", w_p), ("GGG", w_g), ("MLhazard", w_ml)]:
        out[model] = score_timing_forecast(w, true_test)
    return out


def build_providers():
    provs = {}
    for k in (1.0, 2.0, 3.0):
        provs[f"Sim-k{k:g}"] = (lambda seed, kk=k: simulate_dataset_ggg(
            DatasetParams(0.15, 1.2, 0.08, 1.0, N=1000, T=52.0), k=kk,
            rng=np.random.default_rng(seed)))
    cdnow = elog_to_summary(load_cdnow(), 39, HORIZON)
    grocery = elog_to_summary(load_grocery(), 52, HORIZON)
    provs["CDNow"] = lambda seed, d=cdnow: d
    provs["Grocery"] = lambda seed, d=grocery: d
    return provs


def main():
    providers = build_providers()
    rows = []
    for name, get in providers.items():
        t = time.time()
        for seed in range(SEEDS):
            res = run_dataset(name, get(seed), seed=12000 + seed)
            for model, sc in res.items():
                for metric in ("timing_MdAE", "timing_CRPS"):
                    rows.append(dict(dataset=name, seed=seed, model=model,
                                     metric=metric, value=sc[metric]))
            pd.DataFrame(rows).to_csv(RES / "ml_timing_raw.csv", index=False)
        print(f"[{name}] {SEEDS} seeds done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summ = raw.groupby(["dataset", "model", "metric"]).value.mean().reset_index()
    summ.to_csv(RES / "ml_timing_summary.csv", index=False)

    models = ["PNBD", "GGG", "MLhazard"]
    print("\n=== Next-purchase timing: Pareto/NBD vs Pareto/GGG vs ML hazard (MdAE, weeks) ===")
    print(f"{'dataset':10s}" + "".join(f"{m:>11s}" for m in models) + "   best")
    for ds in providers:
        g = summ[(summ.dataset == ds) & (summ.metric == "timing_MdAE")]
        vals = {m: g[g.model == m].value.iloc[0] for m in models if (g.model == m).any()}
        if not vals:
            continue
        best = min(vals, key=vals.get)
        cells = "".join(f"{vals[m]:>10.2f}" + ("*" if m == best else " ") for m in models)
        print(f"{ds:10s}{cells}   {best}")
    print(f"\n[saved] {RES/'ml_timing_summary.csv'}")


if __name__ == "__main__":
    main()
