"""
Phase 2, Step 5: Conformalized BTYD -- post-hoc recalibration of the Pareto/NBD predictive.

The benchmark showed BTYD miscalibrates where its Poisson assumption breaks (Online Retail II
PIT-KS 0.21, Dunnhumby 0.17). This module *repairs* that without changing BTYD's fit, using
distributional recalibration (Kuleshov, Fenner & Ermon 2018) with a conformal-style held-out
split: learn an isotonic quantile-warp from a calibration set's PIT values, then apply it to the
BTYD predictive on the test set. If the forecasts are already calibrated (PIT ~ Uniform), the warp
is the identity and does no harm; if the PIT is skewed, it restores uniformity -- letting a firm
keep BTYD's cheap fit and interpretability while fixing coverage where it matters.

The recalibrated predictive is returned as samples, so it scores under the same CRPS/PIT/coverage
engine as everything else.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import randomized_pit  # noqa: E402


def recalibrate_samples(pred_cal, y_cal, pred_test, n_out: int = 500, seed: int = 0):
    """Distributional recalibration of a sample-based predictive.

    Learn the empirical distribution of the calibration-set randomized PITs u = F(y). The
    recalibrated predictive's p-quantile is the original R^{-1}(p)-quantile, where R is the CDF
    of u; so we sample it by drawing p ~ U(0,1), warping to w = quantile(u, p), and reading the
    w-quantile of each test customer's original samples. Uniform PITs => w = p => identity.

    pred_cal: (J, N_cal) predictive samples on the calibration split; y_cal: (N_cal,) truths.
    pred_test: (J, N_test) predictive samples on the test split.
    Returns (n_out, N_test) recalibrated integer predictive samples."""
    rng = np.random.default_rng(seed)
    u = np.clip(randomized_pit(pred_cal, y_cal, rng), 0.0, 1.0)   # calibration PITs
    p = rng.uniform(size=n_out)
    w = np.quantile(u, p)                                          # R^{-1}(p), shape (n_out,)
    ps = np.sort(pred_test, axis=0)                               # (J, N_test)
    J = ps.shape[0]
    idx = np.clip(np.round(w * (J - 1)).astype(int), 0, J - 1)    # warped quantile indices
    return ps[idx]                                                # (n_out, N_test)


def compare_conformal(df, horizon: int, recal_frac: float = 0.5, seed: int = 0,
                      mcmc_draws: int = 2000, mcmc_burn: int = 700, mcmc_thin: int = 5):
    """Score BTYD before vs after conformal recalibration on a held-out split.

    BTYD is fit on the whole cohort; customers are split into a recalibration set (to learn the
    warp) and a disjoint test set (to evaluate). Returns {(method, cond): scores} for
    method in {BTYD_raw, BTYD_recal}."""
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    n = len(df)

    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_recal = int(round(recal_frac * n))
    recal_idx = np.sort(idx[:n_recal])
    test_idx = np.sort(idx[n_recal:])

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=mcmc_burn, thin=mcmc_thin, seed=seed + 1)
    pred_all = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    pred_recal, y_recal = pred_all[:, recal_idx], y[recal_idx]
    pred_test, y_test = pred_all[:, test_idx], y[test_idx]

    pred_test_recal = recalibrate_samples(pred_recal, y_recal, pred_test, seed=seed + 9)

    active_test = xcal[test_idx] > 0
    out = {}
    for name, pred in [("BTYD_raw", pred_test), ("BTYD_recal", pred_test_recal)]:
        for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active_test)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 6))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "cov95": sc["cov95"], "cov50": sc["cov50"],
                                 "pit_ks": sc["pit_ks"], "nMAE": sc["nMAE"]}
    out["_n_test"] = len(test_idx)
    out["_pct_active_test"] = float(active_test.mean())
    return out


ML_FUNCS = ("PoissonGBM", "HurdleGBM", "QuantileGBM")


def compare_conformal_ml(df, horizon: int, ml_methods=("PoissonGBM", "QuantileGBM"),
                         train_frac: float = 0.4, recal_frac: float = 0.3, seed: int = 0,
                         mcmc_draws: int = 1500, mcmc_burn: int = 500, mcmc_thin: int = 5):
    """Conformal (distributional) recalibration applied to the ML forecasters — gap M3.

    Closes the interval-comparison asymmetry: the ML benchmark (`ml_benchmark.py`) reports
    parametric predictives (Poisson/hurdle) that can be miscalibrated, and a distribution-free
    QuantileGBM. Here every forecaster — BTYD and each ML method — is wrapped in the SAME
    distribution-free recalibration used for Conformalized BTYD (`recalibrate_samples`), giving
    all methods marginal-coverage-repaired intervals scored on a common test set.

    Three-way split so the supervised ML models get an honest pipeline:
      - train  (fit the ML RFM->x* models; BTYD ignores it, it is unsupervised on the full cohort)
      - recal  (learn the conformal quantile-warp from this split's PITs)
      - test   (evaluate raw vs recalibrated, identical customers for every method)

    Returns {(f"{method}_raw"|f"{method}_recal", cond): scores} for method in
    {BTYD} + ml_methods, cond in {all, x>0}. Recalibration of an already-calibrated
    distribution-free method (QuantileGBM) is ~identity and should not harm it."""
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast
    from ml_benchmark import (rfm_features, poisson_gbm_forecast,
                              hurdle_gbm_forecast, quantile_gbm_forecast)

    funcs = {"PoissonGBM": poisson_gbm_forecast, "HurdleGBM": hurdle_gbm_forecast,
             "QuantileGBM": quantile_gbm_forecast}

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    n = len(df)

    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_train = int(round(train_frac * n))
    n_recal = int(round(recal_frac * n))
    train_idx = np.sort(idx[:n_train])
    recal_idx = np.sort(idx[n_train:n_train + n_recal])
    test_idx = np.sort(idx[n_train + n_recal:])

    # BTYD: unsupervised fit on the whole cohort, predict everyone, then index the splits
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=mcmc_burn, thin=mcmc_thin, seed=seed + 1)
    pred_all = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    preds = {"BTYD": (pred_all[:, recal_idx], pred_all[:, test_idx])}

    # ML: fit on the train split, predict recal+test in one call (fit once), then split
    X = rfm_features(df)
    X_eval = np.vstack([X[recal_idx], X[test_idx]])
    n_r = len(recal_idx)
    for m in ml_methods:
        p_eval = funcs[m](X[train_idx], y[train_idx], X_eval, seed=seed + 3)
        preds[m] = (p_eval[:, :n_r], p_eval[:, n_r:])

    y_recal, y_test = y[recal_idx], y[test_idx]
    active_test = xcal[test_idx] > 0
    keep = ("CRPS", "cov95", "cov50", "pit_ks", "nMAE", "sharpness_std")
    out = {}
    for name, (p_recal, p_test) in preds.items():
        p_test_recal = recalibrate_samples(p_recal, y_recal, p_test, seed=seed + 9)
        for tag, pred in [(f"{name}_raw", p_test), (f"{name}_recal", p_test_recal)]:
            for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active_test)]:
                if mask.sum() < 15:
                    continue
                sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 6))
                out[(tag, cond)] = {k: sc[k] for k in keep}
    out["_n_test"] = len(test_idx)
    out["_pct_active_test"] = float(active_test.mean())
    return out


if __name__ == "__main__":
    from datasets import load_summary
    from empirical import load_grocery, elog_to_summary

    cases = [("OnlineRetailII", *load_summary("OnlineRetailII")),
             ("Dunnhumby", *load_summary("Dunnhumby")),
             ("Grocery", elog_to_summary(load_grocery(), 52, 26), 26)]
    print(f"{'dataset':15s}{'cond':5s}{'PIT-KS raw':>12s}{'PIT-KS recal':>14s}"
          f"{'CRPS raw':>10s}{'CRPS recal':>12s}")
    for name, df, h in cases:
        res = compare_conformal(df, h, seed=1, mcmc_draws=1500)
        for cond in ["all", "x>0"]:
            if ("BTYD_raw", cond) in res:
                r = res[("BTYD_raw", cond)]; c = res[("BTYD_recal", cond)]
                print(f"{name:15s}{cond:5s}{r['pit_ks']:>12.3f}{c['pit_ks']:>14.3f}"
                      f"{r['CRPS']:>10.3f}{c['CRPS']:>12.3f}")
