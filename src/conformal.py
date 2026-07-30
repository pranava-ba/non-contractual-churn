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
