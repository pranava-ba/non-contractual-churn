"""
Phase 2, Step 7 (covariate value): what are demographic covariates actually worth?

BTYD ignores covariates; ML can ingest them. On the ~801 Dunnhumby households that carry
demographics (age, income, marital status, home-ownership, household composition/size, kids), we
compare three forecasters of the future purchase count under CRPS/PIT/coverage:
  - BTYD               : covariate-free structural (Pareto/NBD, MCMC)
  - GBM (RFM)          : covariate-free ML (Poisson GBM on recency/frequency features)
  - GBM (RFM + demo)   : covariate-aware ML (same, plus encoded demographics)

The covariate value is the gap between the last two: if demographics help, RFM alone was missing
something; if not, RFM already captures what matters for calibration.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from datasets import load_summary                                     # noqa: E402
from ml_benchmark import rfm_features, poisson_gbm_forecast           # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"

_AGE = {"19-24": 1, "25-34": 2, "35-44": 3, "45-54": 4, "55-64": 5, "65+": 6}
_INCOME = {"Under 15K": 1, "15-24K": 2, "25-34K": 3, "35-49K": 4, "50-74K": 5, "75-99K": 6,
           "100-124K": 7, "125-149K": 8, "150-174K": 9, "175-199K": 10, "200-249K": 11, "250K+": 12}
_SIZE = {"1": 1, "2": 2, "3": 3, "4": 4, "5+": 5}
_KIDS = {"None/Unknown": 0, "1": 1, "2": 2, "3+": 3}


def load_demographics() -> pd.DataFrame:
    """Encode Dunnhumby household demographics: ordinals -> integers, nominals -> one-hot."""
    d = pd.read_csv(DATA / "dunnhumby" / "hh_demographic.csv")
    out = pd.DataFrame({"cust": d["household_key"]})
    out["age"] = d["AGE_DESC"].map(_AGE).fillna(3)
    out["income"] = d["INCOME_DESC"].map(_INCOME).fillna(4)
    out["hh_size"] = d["HOUSEHOLD_SIZE_DESC"].map(_SIZE).fillna(2)
    out["kids"] = d["KID_CATEGORY_DESC"].map(_KIDS).fillna(0)
    for col in ["MARITAL_STATUS_CODE", "HOMEOWNER_DESC", "HH_COMP_DESC"]:
        out = pd.concat([out, pd.get_dummies(d[col], prefix=col).astype(float).reset_index(drop=True)],
                        axis=1)
    return out


def compare_covariate_value(horizon: int = 26, test_frac: float = 0.3, seed: int = 0,
                            mcmc_draws: int = 1500):
    """Score BTYD, GBM(RFM) and GBM(RFM+demo) on the demographics-carrying Dunnhumby subset."""
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast

    cohort, h = load_summary("Dunnhumby")
    demo = load_demographics()
    df = cohort.merge(demo, on="cust", how="inner").reset_index(drop=True)
    demo_cols = [c for c in demo.columns if c != "cust"]

    y = df[f"x_star_{h}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    n = len(df)

    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test_idx, train_idx = np.sort(idx[:n_test]), np.sort(idx[n_test:])

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    pred_btyd = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, h, np.random.default_rng(seed + 2))[:, test_idx]

    X_rfm = rfm_features(df)
    X_demo = df[demo_cols].to_numpy(float)
    X_full = np.hstack([X_rfm, X_demo])
    preds = {
        "BTYD": pred_btyd,
        "GBM_RFM": poisson_gbm_forecast(X_rfm[train_idx], y[train_idx], X_rfm[test_idx], seed=seed + 3),
        "GBM_RFM+demo": poisson_gbm_forecast(X_full[train_idx], y[train_idx], X_full[test_idx], seed=seed + 4),
    }
    y_test, active = y[test_idx], xcal[test_idx] > 0
    out = {}
    for name, pred in preds.items():
        for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 5))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "pit_ks": sc["pit_ks"], "cov95": sc["cov95"]}
    out["_N"] = n
    return out


if __name__ == "__main__":
    from scipy import stats
    rows = {m: {"CRPS": [], "pit_ks": []} for m in ["BTYD", "GBM_RFM", "GBM_RFM+demo"]}
    N = 0
    for seed in range(10):
        res = compare_covariate_value(seed=seed)
        N = res["_N"]
        for m in rows:
            for k in ["CRPS", "pit_ks"]:
                rows[m][k].append(res[(m, "all")][k])
    print(f"Dunnhumby demographic subset (N={N}), 10 seeds, all customers:")
    print(f"  {'method':14s}{'CRPS':>10s}{'PIT-KS':>10s}")
    for m in rows:
        print(f"  {m:14s}{np.mean(rows[m]['CRPS']):>10.3f}{np.mean(rows[m]['pit_ks']):>10.3f}")
    p = stats.wilcoxon(rows["GBM_RFM"]["pit_ks"], rows["GBM_RFM+demo"]["pit_ks"]).pvalue
    print(f"\n  covariate value (PIT-KS, RFM vs RFM+demo): paired Wilcoxon p={p:.3f}")
