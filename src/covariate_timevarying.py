"""
Gap G2 (time-varying covariate): does a known promotional calendar carry forecast value that
RFM and covariate-blind BTYD miss?

The static-demographics test (`covariate_benchmark.py`) found demographics add nothing over RFM.
That leaves the harder, more practitioner-relevant case: a *time-varying* covariate. We simulate a
chain-wide promotional calendar promo(t) in {0,1} (a `promo_len`-week promo every `cycle` weeks)
with heterogeneous per-customer responsiveness e_i, so the alive purchase rate is

    rate_i(t) = lambda_i * (1 + delta * e_i * promo(t)).

A retailer knows its own future promo calendar and each customer's loyalty segment, so the ex-ante
covariate is each customer's *forecast-window promo exposure*  z_i = e_i * (promo fraction of that
customer's forecast window). We then score three forecasters of the future count under the same
CRPS/PIT/coverage lens:

  - BTYD             : covariate-blind structural (Pareto/NBD, MCMC) -- extrapolates a flat rate
  - GBM (RFM)        : covariate-blind ML
  - GBM (RFM + promo): covariate-aware ML (RFM plus z_i)

The covariate value is the gap between the last two; BTYD's degradation shows what a purely
stationary model loses when the forecast window's promo intensity departs from the calibration
average. Everything reuses the existing simulator-free pipeline (rfm_features, poisson_gbm_forecast,
fit_mcmc, score_forecast); only the DGP is new (a thinned time-varying-rate Poisson process).

Run:  python src/covariate_timevarying.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, WEEKS_PER_90_DAYS            # noqa: E402
from ml_benchmark import rfm_features, poisson_gbm_forecast      # noqa: E402

CYCLE = 8.0        # weeks between promo onsets
PROMO_LEN = 2.0    # promo duration (weeks)
DELTA = 1.0        # max multiplicative uplift at e_i = 1 (rate up to 2x during promo)


def promo_active(t: np.ndarray) -> np.ndarray:
    """Chain-wide promotional calendar: active for PROMO_LEN weeks every CYCLE weeks."""
    return (np.mod(t, CYCLE) < PROMO_LEN).astype(float)


def _promo_fraction(a: float, b: float, grid: int = 400) -> float:
    """Fraction of the interval (a, b] that is promotional (fine-grid quadrature)."""
    if b <= a:
        return 0.0
    ts = np.linspace(a, b, grid)
    return float(promo_active(ts).mean())


def _sim_customer(lam_i, tau_i, e_i, horizon, delta, rng):
    """Repeat-purchase times in (0, horizon] from a thinned time-varying-rate Poisson process,
    truncated at dropout tau_i. Instantaneous rate lam_i*(1 + delta*e_i*promo(t))."""
    end = min(tau_i, horizon)
    if end <= 0:
        return np.empty(0)
    lam_max = lam_i * (1.0 + delta * e_i)
    times, t = [], 0.0
    while True:
        batch = rng.exponential(1.0 / lam_max, size=max(16, int(lam_max * end * 2) + 8))
        cs = t + np.cumsum(batch)
        cand = cs[cs <= end]
        if cand.size:
            accept_p = (1.0 + delta * e_i * promo_active(cand)) / (1.0 + delta * e_i)
            times.append(cand[rng.uniform(size=cand.size) < accept_p])
        if cand.size < batch.size:       # last gap overshot -> process complete
            break
        t = cs[-1]
    return np.concatenate(times) if times else np.empty(0)


def simulate_promo_cohort(params: DatasetParams, horizon: int = 26, delta: float = DELTA,
                          seed: int = 0) -> pd.DataFrame:
    """One cohort under the promotional DGP. Same summary columns as `simulate.simulate_dataset`
    plus `e_resp` (true responsiveness) and `promo_fc` (the ex-ante forecast-window covariate z_i)."""
    rng = np.random.default_rng(seed)
    N = params.N
    lam = rng.gamma(params.r, 1.0 / params.alpha, size=N)
    mu = rng.gamma(params.s, 1.0 / params.beta, size=N)
    tau = rng.exponential(1.0 / mu)
    e = rng.uniform(0.5, 1.5, size=N)                       # heterogeneous responsiveness
    acq = rng.uniform(0.0, WEEKS_PER_90_DAYS, size=N)
    T_i = params.T - acq

    rows = []
    for i in range(N):
        cal_len = T_i[i]
        path = _sim_customer(lam[i], tau[i], e[i], cal_len + horizon, delta, rng)
        cal = path[path <= cal_len]
        x = int(cal.size)
        future = path[(path > cal_len) & (path <= cal_len + horizon)]
        rows.append({
            "cust": i, "x": x, "t_x": float(cal.max()) if x else 0.0, "T_cal": cal_len,
            "alive_at_T": bool(tau[i] > cal_len),
            "lambda_true": lam[i], "mu_true": mu[i], "tau_true": tau[i], "e_resp": e[i],
            f"x_star_{horizon}": int(future.size),
            # ex-ante covariate: responsiveness x promo intensity of this customer's fc window
            "promo_fc": e[i] * _promo_fraction(cal_len, cal_len + horizon),
        })
    return pd.DataFrame(rows)


def compare_timevarying_covariate(params: DatasetParams, horizon: int = 26, test_frac: float = 0.3,
                                  seed: int = 0, mcmc_draws: int = 1200):
    """Score BTYD, GBM(RFM), GBM(RFM+promo) on a promo cohort. Returns {(method,cond): scores}."""
    from estimate import fit_mcmc
    from score import spp_predict, score_forecast

    df = simulate_promo_cohort(params, horizon, seed=seed)
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)
    n = len(df)

    rng = np.random.default_rng(seed + 100)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test_idx, train_idx = np.sort(idx[:n_test]), np.sort(idx[n_test:])

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=400, thin=4, seed=seed + 1)
    pred_btyd = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon,
                            np.random.default_rng(seed + 2))[:, test_idx]

    X_rfm = rfm_features(df)
    X_full = np.hstack([X_rfm, df[["promo_fc"]].to_numpy(float)])
    preds = {
        "BTYD": pred_btyd,
        "GBM_RFM": poisson_gbm_forecast(X_rfm[train_idx], y[train_idx], X_rfm[test_idx], seed=seed + 3),
        "GBM_RFM+promo": poisson_gbm_forecast(X_full[train_idx], y[train_idx], X_full[test_idx], seed=seed + 4),
    }
    y_test, active = y[test_idx], xcal[test_idx] > 0
    out = {}
    for name, pred in preds.items():
        for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 5))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "pit_ks": sc["pit_ks"],
                                 "cov95": sc["cov95"], "nMAE": sc["nMAE"]}
    out["_N"] = n
    out["_mean_xstar"] = float(y.mean())
    return out


if __name__ == "__main__":
    from scipy import stats

    base = DatasetParams(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, N=2000, T=52.0)
    methods = ["BTYD", "GBM_RFM", "GBM_RFM+promo"]
    acc = {m: {"CRPS": [], "pit_ks": [], "nMAE": []} for m in methods}
    mean_xs = []
    for seed in range(8):
        res = compare_timevarying_covariate(base, seed=seed)
        mean_xs.append(res["_mean_xstar"])
        for m in methods:
            for k in ("CRPS", "pit_ks", "nMAE"):
                acc[m][k].append(res[(m, "all")][k])
    print(f"Promo DGP (N={base.N}, delta={DELTA}, promo {PROMO_LEN:.0f}w/{CYCLE:.0f}w cycle), "
          f"8 seeds, mean x*={np.mean(mean_xs):.2f}")
    print(f"  {'method':16s}{'CRPS':>9s}{'PIT-KS':>9s}{'nMAE':>9s}")
    for m in methods:
        print(f"  {m:16s}{np.mean(acc[m]['CRPS']):>9.3f}{np.mean(acc[m]['pit_ks']):>9.3f}"
              f"{np.mean(acc[m]['nMAE']):>9.3f}")
    for k in ("CRPS", "pit_ks"):
        p = stats.wilcoxon(acc["GBM_RFM"][k], acc["GBM_RFM+promo"][k]).pvalue
        print(f"  covariate value ({k}, RFM vs RFM+promo): paired Wilcoxon p={p:.3f}")
