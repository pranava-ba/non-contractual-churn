"""
Gap V3: the compute-cost table and cost-accuracy Pareto frontier.

Simon (2025) repeatedly asserts MCMC and ML are "more expensive" than MLE but reports no
wall-clock numbers. We time fit+predict for every estimation route across cohort size N, pair each
with its forecast accuracy (CRPS on a common held-out split), and identify the Pareto frontier --
the methods that are not dominated (worse on *both* cost and accuracy) by some alternative. Turns
"MCMC is expensive" into an actionable frontier and delivers the analysis's Contribution #1.

Methods: heuristic, MLE plug-in, Laplace (E4), MCMC, amortized net (one-time training amortised
over cohorts), Poisson-GBM. Unsupervised routes fit on the full cohort and predict the test split;
supervised routes (GBM) train on the train split -- footnote that asymmetry when reading cost.

Saves results/cost_benchmark_summary.csv + results/figures/fig_cost_frontier.png; prints the table.

Run:  python src/run_cost_benchmark.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams, simulate_dataset            # noqa: E402
from estimate import fit_mle, fit_mcmc                          # noqa: E402
from score import (spp_predict, conditional_individual_draws,   # noqa: E402
                   score_forecast)
from laplace import laplace_predict                             # noqa: E402
from ml_benchmark import rfm_features, poisson_gbm_forecast     # noqa: E402
from run_study import heuristic_point                           # noqa: E402
import amortized as amz                                         # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
FIG = RES / "figures"
N_GRID = [500, 1000, 2000, 4000, 8000]
REPS = 2
HORIZON = 26
BEHAVIOUR = dict(E_lambda=0.15, CV_lambda=1.3, E_mu=0.08, CV_mu=1.2, T=52.0)


def _crps(pred, y):
    return score_forecast(pred, y, np.random.default_rng(0))["CRPS"]


def time_methods(df, test_idx, train_idx, am, seed):
    """Return {method: (seconds, pred_on_test)} timing fit+predict for each route."""
    Tcal = df["T_cal"].to_numpy(float)
    x = df["x"].to_numpy(float)
    y = df[f"x_star_{HORIZON}"].to_numpy(float)
    out = {}

    t = time.time()
    hp = np.round(heuristic_point(df, HORIZON)).astype(int)
    pred = np.repeat(hp[None, :], 60, axis=0)
    out["heuristic"] = (time.time() - t, pred[:, test_idx])

    t = time.time()
    mle = fit_mle(df, seed=seed)
    lam, mu, tau = conditional_individual_draws(df, mle["r"], mle["alpha"], mle["s"], mle["beta"],
                                                n_draws=400, seed=seed + 1)
    pred = spp_predict(lam, mu, tau, Tcal, HORIZON, np.random.default_rng(seed + 2))
    out["MLE_multistart"] = (time.time() - t, pred[:, test_idx])

    # single-start MLE (method-of-moments init, no multistart hardening): isolates how much of the
    # MLE cost is the robustness hardening rather than the optimisation itself
    t = time.time()
    mle1 = fit_mle(df, seed=seed, n_start=1)
    lam, mu, tau = conditional_individual_draws(df, mle1["r"], mle1["alpha"], mle1["s"], mle1["beta"],
                                                n_draws=400, seed=seed + 1)
    pred = spp_predict(lam, mu, tau, Tcal, HORIZON, np.random.default_rng(seed + 2))
    out["MLE_1start"] = (time.time() - t, pred[:, test_idx])

    t = time.time()
    pred, _ = laplace_predict(df, HORIZON, n_draws=400, seed=seed + 10)
    out["Laplace"] = (time.time() - t, pred[:, test_idx])

    t = time.time()
    mc = fit_mcmc(df, n_draws=1200, burn_in=400, thin=4, seed=seed + 20)
    pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, HORIZON, np.random.default_rng(seed + 21))
    out["MCMC"] = (time.time() - t, pred[:, test_idx])

    t = time.time()
    r, a, s, b, _, _ = amz.amortized_params(am, df)
    lam, mu, tau = conditional_individual_draws(df, r, a, s, b, n_draws=400, seed=seed + 30)
    pred = spp_predict(lam, mu, tau, Tcal, HORIZON, np.random.default_rng(seed + 31))
    out["Amortized"] = (time.time() - t, pred[:, test_idx])

    t = time.time()
    X = rfm_features(df)
    pred = poisson_gbm_forecast(X[train_idx], y[train_idx], X[test_idx], seed=seed + 40)
    out["PoissonGBM"] = (time.time() - t, pred)          # already on test
    return out


def pareto_frontier(costs, accs):
    """Indices of non-dominated points (minimise both cost and accuracy=CRPS)."""
    order = np.argsort(costs)
    best, front = np.inf, []
    for i in order:
        if accs[i] < best - 1e-12:
            front.append(i); best = accs[i]
    return set(front)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    print("Training the amortizer once (one-time cost)...", flush=True)
    t = time.time()
    X, Y = amz.generate_training_data(n_cohorts=800, seed=0)
    am = amz.fit_amortizer(X, Y, seed=0)
    t_train = time.time() - t
    print(f"  amortizer trained on 800 cohorts in {t_train:.0f}s (one-time, amortised)", flush=True)

    rows = []
    for N in N_GRID:
        for rep in range(REPS):
            seed = 5000 + 13 * N + rep
            df = simulate_dataset(DatasetParams(N=N, **BEHAVIOUR), rng=np.random.default_rng(seed))
            y = df[f"x_star_{HORIZON}"].to_numpy(float)
            n = len(df)
            rng = np.random.default_rng(seed + 1)
            idx = rng.permutation(n)
            n_test = int(round(0.3 * n))
            test_idx, train_idx = np.sort(idx[:n_test]), np.sort(idx[n_test:])
            res = time_methods(df, test_idx, train_idx, am, seed)
            for m, (secs, pred) in res.items():
                rows.append(dict(N=N, rep=rep, method=m, secs=secs,
                                 CRPS=_crps(pred, y[test_idx])))
        print(f"[N={N}] {REPS} reps done", flush=True)

    raw = pd.DataFrame(rows)
    g = raw.groupby(["N", "method"]).agg(secs=("secs", "mean"), CRPS=("CRPS", "mean")).reset_index()
    g.to_csv(RES / "cost_benchmark_summary.csv", index=False)

    methods = ["heuristic", "MLE_1start", "MLE_multistart", "Laplace", "Amortized", "MCMC", "PoissonGBM"]
    print("\n=== Fit+predict wall-clock (seconds), mean over reps ===")
    print(f"{'N':>7s}" + "".join(f"{m:>12s}" for m in methods))
    for N in N_GRID:
        cells = "".join(f"{g[(g.N == N) & (g.method == m)]['secs'].iloc[0]:>12.3f}" for m in methods)
        print(f"{N:>7d}{cells}")

    # frontier at the largest N (most discriminating on cost)
    Nf = N_GRID[-1]
    sub = g[g.N == Nf].set_index("method").loc[methods]
    front = pareto_frontier(sub["secs"].to_numpy(), sub["CRPS"].to_numpy())
    print(f"\n=== Cost-accuracy Pareto frontier at N={Nf} (secs vs CRPS) ===")
    print(f"{'method':12s}{'secs':>10s}{'CRPS':>10s}{'  frontier?':>12s}")
    for i, m in enumerate(methods):
        tag = "ON FRONTIER" if i in front else "dominated"
        print(f"{m:12s}{sub.loc[m,'secs']:>10.3f}{sub.loc[m,'CRPS']:>10.3f}{tag:>12s}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for m in methods:
            s = g[g.method == m].sort_values("N")
            ax.plot(s["secs"], s["CRPS"], "o-", ms=4, label=m, alpha=0.85)
        ax.set_xscale("log")
        ax.set_xlabel("fit + predict wall-clock (s, log scale)")
        ax.set_ylabel("CRPS (lower = better)")
        ax.set_title("Cost-accuracy frontier across N (500 to 8000)")
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(FIG / "fig_cost_frontier.png", dpi=130)
        print(f"\n[saved] {RES/'cost_benchmark_summary.csv'} and {FIG/'fig_cost_frontier.png'}")
    except Exception as e:
        print(f"\n[saved] {RES/'cost_benchmark_summary.csv'}  (figure skipped: {e})")


if __name__ == "__main__":
    main()
