"""
Phase 2, Step 1: machine-learning comparator under the same proper-scoring lens.

The customer-base-analysis literature compares models on point error only; this module brings a
machine-learning forecaster into our CRPS / randomized-PIT / coverage framework so the question
becomes calibration, not just accuracy: does flexible ML produce better-*calibrated* purchase
forecasts than the parsimonious Pareto/NBD, or does BTYD's structure win on sparse, zero-inflated
count data?

The ML forecaster is deliberately a strong, standard baseline: gradient-boosted trees with a
POISSON objective on RFM features, whose predictive distribution is Poisson(rate_hat). It is
supervised (it learns RFM -> future count from customers whose future is already observed), which
is exactly the real-world setup: you train on past cohorts whose holdout is known, then apply to
current customers. BTYD is unsupervised (fit on calibration histories, never sees a holdout label).
Both are scored on the same held-out customers with the same engine, so the comparison is fair.

Predictive samples are (n_draws, N) integer arrays, identical in shape to `spp_predict`, so they
drop straight into `score.score_forecast`.
"""
from __future__ import annotations

import numpy as np


# ------------------------------- features -------------------------------------- #
FEATURE_NAMES = ["frequency_x", "recency_tx", "T_cal", "time_since_last", "rate_x_over_T"]


def rfm_features(df) -> np.ndarray:
    """Classic RFM(+) predictors from the calibration summary (all forecast-time info).

    frequency = repeat count x; recency = t_x (time of last purchase); T_cal = observation
    length; time_since_last = T_cal - t_x; rate = x / T_cal. For single/zero buyers t_x = 0."""
    x = df["x"].to_numpy(float)
    t_x = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)
    since_last = np.maximum(T - t_x, 0.0)
    rate = np.divide(x, T, out=np.zeros_like(x), where=T > 0)
    return np.column_stack([x, t_x, T, since_last, rate])


# ------------------------------- forecaster ------------------------------------ #
def poisson_gbm_forecast(X_train, y_train, X_test, n_draws: int = 400, seed: int = 0):
    """Fit a Poisson gradient-boosted model RFM -> future count, return Poisson predictive draws.

    Returns (n_draws, N_test) integer samples ~ Poisson(rate_hat_i)."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    model = HistGradientBoostingRegressor(
        loss="poisson", max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
        min_samples_leaf=30, l2_regularization=1.0, random_state=seed)
    model.fit(X_train, np.maximum(y_train, 0.0))
    rate = np.clip(model.predict(X_test), 1e-6, None)
    rng = np.random.default_rng(seed + 1)
    return rng.poisson(rate[None, :], size=(n_draws, rate.shape[0])).astype(float)


def hurdle_gbm_forecast(X_train, y_train, X_test, n_draws: int = 400, seed: int = 0):
    """Zero-inflated (hurdle) gradient boosting -- the count analog of the ZILN model
    (Wang et al. 2019). Two parts: a classifier for P(active) = P(x*>0), and a Poisson GBM
    on the positive counts (target x*-1, so the positive draw is 1 + Poisson). The predictive
    is the mixture: 0 with prob 1-p_active, else 1 + Poisson(m). Explicitly modelling the zero
    mass is the natural ML answer to the heavy zero-inflation of customer-base data."""
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    y_train = np.asarray(y_train, float)
    active = (y_train > 0).astype(int)
    n_test = X_test.shape[0]

    # part 1: P(active). Guard the degenerate all-active / all-inactive training case.
    if active.min() == active.max():
        p_active = np.full(n_test, float(active.mean()))
    else:
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05,
                                             max_leaf_nodes=15, min_samples_leaf=30,
                                             l2_regularization=1.0, random_state=seed)
        clf.fit(X_train, active)
        p_active = clf.predict_proba(X_test)[:, 1]

    # part 2: positive count model, Poisson GBM on (x*-1) over the positive training rows
    pos = active == 1
    if pos.sum() >= 20:
        reg = HistGradientBoostingRegressor(loss="poisson", max_iter=300, learning_rate=0.05,
                                            max_leaf_nodes=15, min_samples_leaf=20,
                                            l2_regularization=1.0, random_state=seed)
        reg.fit(X_train[pos], np.maximum(y_train[pos] - 1.0, 0.0))
        m = np.clip(reg.predict(X_test), 0.0, None)
    else:
        m = np.full(n_test, max(y_train[pos].mean() - 1.0, 0.0) if pos.any() else 0.0)

    rng = np.random.default_rng(seed + 1)
    is_active = rng.uniform(size=(n_draws, n_test)) < p_active[None, :]
    pos_count = 1 + rng.poisson(m[None, :], size=(n_draws, n_test))
    return (is_active * pos_count).astype(float)


QUANTILES = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95])


def quantile_gbm_forecast(X_train, y_train, X_test, n_draws: int = 400, seed: int = 0):
    """Distribution-free quantile gradient boosting. Fits a GBM per quantile, sorts them to
    enforce monotonicity, then samples by inverting the empirical quantile function. Makes no
    Poisson (or any parametric) assumption -- the flexible-ML end of the comparison."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    n_test = X_test.shape[0]
    preds = np.zeros((len(QUANTILES), n_test))
    for i, q in enumerate(QUANTILES):
        reg = HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=200,
                                            learning_rate=0.05, max_leaf_nodes=15,
                                            min_samples_leaf=30, random_state=seed)
        reg.fit(X_train, np.asarray(y_train, float))
        preds[i] = np.clip(reg.predict(X_test), 0.0, None)
    preds = np.sort(preds, axis=0)                          # enforce monotone quantiles

    # sample: draw u ~ U(0,1), linearly interpolate the per-customer quantile function
    rng = np.random.default_rng(seed + 1)
    u = rng.uniform(size=(n_draws, n_test))
    idx = np.clip(np.searchsorted(QUANTILES, u, side="right") - 1, 0, len(QUANTILES) - 2)
    q_lo, q_hi = QUANTILES[idx], QUANTILES[idx + 1]
    frac = (u - q_lo) / (q_hi - q_lo)
    col = np.arange(n_test)[None, :]
    val = preds[idx, col] * (1 - frac) + preds[idx + 1, col] * frac
    return np.clip(np.round(val), 0.0, None)


# ---------------------- fair BTYD-vs-ML comparison ----------------------------- #
def compare_btyd_vs_gbm(df, horizon: int, test_frac: float = 0.3, seed: int = 0,
                        mcmc_draws: int = 2000, mcmc_burn: int = 700, mcmc_thin: int = 5):
    """Score Pareto/NBD (MCMC) against the Poisson-GBM on a held-out customer split.

    BTYD is fit on the whole cohort's calibration histories (unsupervised); the GBM is trained on
    the train split's (RFM -> realised x*) and both are scored on the test split. Returns a dict
    of per-method scores from `score.score_forecast` (all customers + x>0 subgroup)."""
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    n = len(df)

    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test_idx = np.sort(idx[:n_test])
    train_idx = np.sort(idx[n_test:])

    # BTYD: fit on ALL calibration data (never uses x*), predict everyone, score the test split
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=mcmc_burn, thin=mcmc_thin, seed=seed + 1)
    pred_btyd_all = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    pred_btyd = pred_btyd_all[:, test_idx]

    # GBM: train on train split (RFM -> x*), predict the test split
    X = rfm_features(df)
    pred_gbm = poisson_gbm_forecast(X[train_idx], y[train_idx], X[test_idx], seed=seed + 3)

    y_test = y[test_idx]
    active_test = xcal[test_idx] > 0
    out = {}
    for name, pred in [("BTYD", pred_btyd), ("GBM", pred_gbm)]:
        for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active_test)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 4))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "cov95": sc["cov95"],
                                 "cov50": sc["cov50"], "pit_ks": sc["pit_ks"], "nMAE": sc["nMAE"]}
    out["_n_test"] = int(n_test)
    out["_pct_active_test"] = float(active_test.mean())
    return out


def compare_all(df, horizon: int, test_frac: float = 0.3, seed: int = 0,
                mcmc_draws: int = 2000, mcmc_burn: int = 700, mcmc_thin: int = 5):
    """Score Pareto/NBD against three ML forecasters (Poisson-GBM, Hurdle-GBM, Quantile-GBM)
    on one held-out customer split. BTYD is fit unsupervised on the whole cohort; the ML
    models train on the split's (RFM -> realised x*); all are scored on the test split.
    Returns {(method, cond): scores} for method in {BTYD, PoissonGBM, HurdleGBM, QuantileGBM}."""
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    n = len(df)

    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test_idx = np.sort(idx[:n_test])
    train_idx = np.sort(idx[n_test:])

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=mcmc_burn, thin=mcmc_thin, seed=seed + 1)
    pred_btyd = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon,
                            np.random.default_rng(seed + 2))[:, test_idx]
    X = rfm_features(df)
    Xtr, ytr, Xte = X[train_idx], y[train_idx], X[test_idx]
    preds = {
        "BTYD": pred_btyd,
        "PoissonGBM": poisson_gbm_forecast(Xtr, ytr, Xte, seed=seed + 3),
        "HurdleGBM": hurdle_gbm_forecast(Xtr, ytr, Xte, seed=seed + 4),
        "QuantileGBM": quantile_gbm_forecast(Xtr, ytr, Xte, seed=seed + 5),
    }

    y_test = y[test_idx]
    active_test = xcal[test_idx] > 0
    out = {}
    for name, pred in preds.items():
        for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active_test)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 6))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "cov95": sc["cov95"], "cov50": sc["cov50"],
                                 "pit_ks": sc["pit_ks"], "nMAE": sc["nMAE"]}
    out["_n_test"] = int(n_test)
    out["_pct_active_test"] = float(active_test.mean())
    return out


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from simulate import DatasetParams, simulate_dataset
    from empirical import load_cdnow, load_grocery, elog_to_summary

    def show(name, res):
        print(f"\n=== {name}  (n_test={res['_n_test']}, active={100*res['_pct_active_test']:.1f}%) ===")
        print(f"  {'method':6s}{'cond':5s}{'CRPS':>9s}{'PIT-KS':>9s}{'cov95':>8s}{'cov50':>8s}{'nMAE':>8s}")
        for key, s in res.items():
            if isinstance(key, tuple) and isinstance(s, dict):
                m, c = key
                print(f"  {m:6s}{c:5s}{s['CRPS']:>9.3f}{s['pit_ks']:>9.3f}"
                      f"{s['cov95']:>8.3f}{s['cov50']:>8.3f}{s['nMAE']:>8.3f}")

    sim = simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=2000, T=52.0),
                           rng=np.random.default_rng(1))
    show("Simulated (N=2000)", compare_btyd_vs_gbm(sim, 26, seed=1))
    show("CDNow", compare_btyd_vs_gbm(elog_to_summary(load_cdnow(), 39, 26), 26, seed=2))
    show("Grocery", compare_btyd_vs_gbm(elog_to_summary(load_grocery(), 52, 26), 26, seed=3))
