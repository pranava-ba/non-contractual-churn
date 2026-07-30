"""
Phase 2, Step 6: amortized neural inference for the Pareto/NBD.

MCMC (and even MLE) fits each cohort from scratch. Here we learn the inference ONCE: simulate
many cohorts with known behavioural parameters, and train a neural network to map a cohort's
summary statistics -> its parameters. For any new cohort, inference is then a single forward pass
(microseconds), with no sampler and no per-cohort optimisation. The scientific question follows
the paper's theme: is this instant, amortized estimation route as calibrated as MCMC?

This is amortized *point* estimation feeding a plug-in predictive (the paper already showed
population-parameter uncertainty is second-order for forecast calibration, so a plug-in at the
amortized estimate is the right scope). A full neural posterior estimator (sbi/torch) is a heavier
extension whose extra value -- the posterior over theta -- is exactly the second-order piece.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset, moments_to_gamma  # noqa: E402


FEATURE_NAMES = ["log_N", "mean_x", "sd_x", "frac_zero", "frac_one", "p90_x",
                 "mean_tx_active", "mean_T", "recency_ratio", "since_last_ratio", "frac_active"]


def cohort_features(df) -> np.ndarray:
    """Forecast-time summary statistics of a cohort (no holdout info)."""
    x = df["x"].to_numpy(float)
    tx = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)
    act = x > 0
    Ta = np.maximum(T[act], 1e-9)
    m = lambda a: float(a.mean()) if a.size else 0.0     # noqa: E731
    return np.array([
        np.log(len(x)), x.mean(), x.std(), (x == 0).mean(), (x == 1).mean(),
        np.quantile(x, 0.9), m(tx[act]), T.mean(),
        m(tx[act] / Ta), m((T[act] - tx[act]) / Ta), act.mean(),
    ])


def generate_training_data(n_cohorts: int = 4000, seed: int = 0):
    """Simulate cohorts with known (E_lambda, CV_lambda, E_mu, CV_mu) and record
    (summary features -> log behavioural params). Targets are logged for stability."""
    rng = np.random.default_rng(seed)
    X, Y = [], []
    for _ in range(n_cohorts):
        El, CVl = rng.uniform(0.02, 0.30), rng.uniform(0.5, 2.5)
        Em, CVm = rng.uniform(0.02, 0.20), rng.uniform(0.5, 2.5)
        p = DatasetParams(El, CVl, Em, CVm, N=int(rng.integers(200, 1500)),
                          T=float(rng.uniform(26, 72)))
        df = simulate_dataset(p, rng=rng)
        X.append(cohort_features(df))
        Y.append([np.log(El), np.log(Em), np.log(CVl), np.log(CVm)])
    return np.array(X), np.array(Y)


def fit_amortizer(X, Y, seed: int = 0):
    """Train the amortized inference network (summary stats -> log behavioural params)."""
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler
    xs, ys = StandardScaler().fit(X), StandardScaler().fit(Y)
    mlp = MLPRegressor(hidden_layer_sizes=(128, 64), activation="relu", max_iter=1000,
                       early_stopping=True, n_iter_no_change=25, random_state=seed)
    mlp.fit(xs.transform(X), ys.transform(Y))
    return {"mlp": mlp, "xs": xs, "ys": ys}


def amortized_params(am, df):
    """Instant Pareto/NBD parameters (r, alpha, s, beta) for a cohort: one forward pass."""
    f = cohort_features(df)[None, :]
    y = am["ys"].inverse_transform(am["mlp"].predict(am["xs"].transform(f)))[0]
    El, Em, CVl, CVm = np.exp(y)
    r, alpha = moments_to_gamma(El, CVl)
    s, beta = moments_to_gamma(Em, CVm)
    return r, alpha, s, beta, El, Em


def compare_amortized_vs_mcmc(df, horizon: int, am, seed: int = 0, mcmc_draws: int = 1500):
    """Score MCMC against the amortized plug-in predictive on the full cohort (both unsupervised)."""
    import time
    from estimate import fit_mcmc
    from score import spp_predict, conditional_individual_draws, score_forecast

    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    xcal = df["x"].to_numpy(float)

    t0 = time.time()
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    pred_mcmc = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    t_mcmc = time.time() - t0

    t0 = time.time()
    r, a, s, b, El, Em = amortized_params(am, df)
    lam, mu, tau = conditional_individual_draws(df, r, a, s, b, n_draws=400, seed=seed + 3)
    pred_am = spp_predict(lam, mu, tau, Tcal, horizon, np.random.default_rng(seed + 4))
    t_am = time.time() - t0

    active = xcal > 0
    out = {}
    for name, pred in [("MCMC", pred_mcmc), ("Amortized", pred_am)]:
        for cond, mask in [("all", np.ones(len(y), bool)), ("x>0", active)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y[mask], np.random.default_rng(seed + 5))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "pit_ks": sc["pit_ks"], "cov95": sc["cov95"]}
    out["_time"] = {"MCMC": t_mcmc, "Amortized": t_am}
    out["_El"] = {"MCMC": mc.pop_summary()["E_lambda"], "Amortized": El}
    return out


if __name__ == "__main__":
    import time
    from empirical import load_cdnow, load_grocery, elog_to_summary
    from datasets import load_summary

    print("Generating training cohorts + fitting amortizer...", flush=True)
    t = time.time()
    X, Y = generate_training_data(n_cohorts=4000, seed=0)
    am = fit_amortizer(X, Y, seed=0)
    print(f"  trained on {len(X)} simulated cohorts in {time.time()-t:.0f}s\n")

    rng = np.random.default_rng(99)
    sim = simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=1200, T=52.0), rng=rng)
    cases = [("Simulated", sim, 26),
             ("CDNow", elog_to_summary(load_cdnow(), 39, 26), 26),
             ("Grocery", elog_to_summary(load_grocery(), 52, 26), 26),
             ("OnlineRetailII", *load_summary("OnlineRetailII"))]
    print(f"{'dataset':15s}{'method':10s}{'CRPS':>8s}{'PIT-KS':>9s}{'cov95':>8s}{'E(lam)':>9s}{'time(s)':>9s}")
    for name, df, h in cases:
        res = compare_amortized_vs_mcmc(df, h, am, seed=1)
        for method in ["MCMC", "Amortized"]:
            s = res[(method, "all")]
            print(f"{name:15s}{method:10s}{s['CRPS']:>8.3f}{s['pit_ks']:>9.3f}{s['cov95']:>8.3f}"
                  f"{res['_El'][method]:>9.3f}{res['_time'][method]:>9.3f}")
