"""
Objection 9 (ML under-tuning): is the structural-versus-ML verdict robust to the ML hyperparameters?

The GBM forecasters use one fixed hyperparameter setting. A referee may worry that the comparison is
decided by ML tuning---either that a better-tuned ML would win on sparse data too, or that ours is
handicapped. We re-run the two decisive ML forecasters (the parametric Poisson-GBM and the
distribution-free Quantile-GBM) under a spread of reasonable settings (shallow/default/deep/slow) on
one cohort where structure wins (Simulated) and one where ML wins (Online Retail II), and compare the
PIT-KS spread across settings with the structural baseline. If the qualitative verdict---BTYD best on
sparse, Quantile-GBM best on dense---holds across the whole spread, it does not hinge on tuning.

Saves results/ml_tuning_summary.csv; prints the table.  Run:  python src/run_ml_tuning.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml_benchmark import rfm_features                             # noqa: E402
from score import score_forecast                                 # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"

CONFIGS = {
    "shallow": dict(max_iter=200, learning_rate=0.05, max_leaf_nodes=7, min_samples_leaf=40),
    "default": dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=30),
    "deep":    dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=15),
    "slow":    dict(max_iter=500, learning_rate=0.02, max_leaf_nodes=15, min_samples_leaf=30),
}
QUANTILES = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95])


def poisson_gbm(Xtr, ytr, Xte, cfg, n_draws=400, seed=0):
    from sklearn.ensemble import HistGradientBoostingRegressor
    m = HistGradientBoostingRegressor(loss="poisson", l2_regularization=1.0, random_state=seed, **cfg)
    m.fit(Xtr, np.maximum(ytr, 0.0))
    rate = np.clip(m.predict(Xte), 1e-6, None)
    rng = np.random.default_rng(seed + 1)
    return rng.poisson(rate[None, :], size=(n_draws, rate.shape[0])).astype(float)


def quantile_gbm(Xtr, ytr, Xte, cfg, n_draws=400, seed=0):
    from sklearn.ensemble import HistGradientBoostingRegressor
    n_test = Xte.shape[0]
    preds = np.zeros((len(QUANTILES), n_test))
    for i, q in enumerate(QUANTILES):
        r = HistGradientBoostingRegressor(loss="quantile", quantile=q, random_state=seed, **cfg)
        r.fit(Xtr, np.asarray(ytr, float))
        preds[i] = np.clip(r.predict(Xte), 0.0, None)
    preds = np.sort(preds, axis=0)
    rng = np.random.default_rng(seed + 1)
    u = rng.uniform(size=(n_draws, n_test))
    idx = np.clip(np.searchsorted(QUANTILES, u, side="right") - 1, 0, len(QUANTILES) - 2)
    q_lo, q_hi = QUANTILES[idx], QUANTILES[idx + 1]
    frac = (u - q_lo) / (q_hi - q_lo)
    col = np.arange(n_test)[None, :]
    val = preds[idx, col] * (1 - frac) + preds[idx + 1, col] * frac
    return np.clip(np.round(val), 0.0, None)


def btyd_pitks(df, horizon, test_idx, seed):
    from estimate import fit_mcmc
    from score import spp_predict
    mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=seed + 1)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, df["T_cal"].to_numpy(float), horizon,
                       np.random.default_rng(seed + 2))[:, test_idx]
    return pred


def run(name, df, horizon, seed=0):
    y = df[f"x_star_{horizon}"].to_numpy(float)
    n = len(df)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(0.3 * n))
    test, train = np.sort(idx[:n_test]), np.sort(idx[n_test:])
    X = rfm_features(df)
    y_test = y[test]
    rows = []
    # structural baseline (config-free)
    sc = score_forecast(btyd_pitks(df, horizon, test, seed), y_test, np.random.default_rng(seed + 3))
    rows.append(dict(dataset=name, model="BTYD", config="--", pit_ks=sc["pit_ks"], CRPS=sc["CRPS"]))
    for cfg_name, cfg in CONFIGS.items():
        for model, fn in [("PoissonGBM", poisson_gbm), ("QuantileGBM", quantile_gbm)]:
            pred = fn(X[train], y[train], X[test], cfg, seed=seed + 4)
            sc = score_forecast(pred, y_test, np.random.default_rng(seed + 5))
            rows.append(dict(dataset=name, model=model, config=cfg_name,
                             pit_ks=sc["pit_ks"], CRPS=sc["CRPS"]))
    return rows


def main():
    from simulate import DatasetParams, simulate_dataset
    from datasets import load_summary
    cases = [("Simulated", simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=1500, T=52.0),
                                            rng=np.random.default_rng(1)), 26),
             ("OnlineRetailII", *load_summary("OnlineRetailII"))]
    rows = []
    for name, df, h in cases:
        rows += run(name, df, h, seed=0)
    out = pd.DataFrame(rows)
    out.to_csv(RES / "ml_tuning_summary.csv", index=False)

    print("=== ML hyperparameter sensitivity: PIT-KS (structure vs ML across settings) ===")
    for name, _, _ in cases:
        d = out[out.dataset == name]
        btyd = d[d.model == "BTYD"]["pit_ks"].iloc[0]
        print(f"\n {name}:  BTYD PIT-KS = {btyd:.3f}")
        print(f"  {'model':13s}" + "".join(f"{c:>9s}" for c in CONFIGS) + f"{'range':>9s}")
        for model in ["PoissonGBM", "QuantileGBM"]:
            vals = [d[(d.model == model) & (d.config == c)]["pit_ks"].iloc[0] for c in CONFIGS]
            rng = max(vals) - min(vals)
            print(f"  {model:13s}" + "".join(f"{v:>9.3f}" for v in vals) + f"{rng:>9.3f}")
    print(f"\n[saved] {RES/'ml_tuning_summary.csv'}")


if __name__ == "__main__":
    main()
