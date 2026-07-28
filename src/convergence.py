"""
MCMC convergence diagnostics for the appendix: split-Rhat and effective sample size
(ESS) for the four population parameters (and the behavioural means E[lambda], E[mu])
of the Abe/BTYDplus Gibbs sampler, on a representative simulated cohort and on CDNow.
Also saves a 4-chain trace figure. This is the reviewer defense for the "MCMC = MLE"
null: the null is not an artefact of a poorly-mixed sampler.

Run:  python src/convergence.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib                                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
from simulate import DatasetParams, simulate_dataset                # noqa: E402
from estimate import fit_mcmc                                       # noqa: E402
from empirical import load_cdnow, elog_to_summary                   # noqa: E402

FIG = Path(__file__).resolve().parent.parent / "results" / "figures"


def split_rhat(chains: np.ndarray) -> float:
    """Split-Rhat (Gelman-Rubin) for a (n_chains, n_draws) array of one scalar param."""
    m0, n0 = chains.shape
    half = n0 // 2
    s = np.concatenate([chains[:, :half], chains[:, half:2 * half]], axis=0)  # (2m, n/2)
    m, n = s.shape
    means = s.mean(axis=1)
    B = n * means.var(ddof=1)
    W = s.var(axis=1, ddof=1).mean()
    var = (n - 1) / n * W + B / n
    return float(np.sqrt(var / W))


def ess(chains: np.ndarray) -> float:
    """Effective sample size across chains (Vehtari et al. 2021, basic version)."""
    m, n = chains.shape
    means = chains.mean(axis=1)
    W = chains.var(axis=1, ddof=1).mean()
    B = n * means.var(ddof=1)
    var_plus = (n - 1) / n * W + B / n
    # combined autocorrelation via averaged within-chain autocovariance
    acov = np.zeros(n)
    for c in chains:
        cc = c - c.mean()
        full = np.correlate(cc, cc, mode="full")[n - 1:]
        acov += full / n
    acov /= m
    rho = 1.0 - (W - acov) / var_plus
    # Geyer initial monotone: sum pairs until negative
    s = 0.0
    t = 1
    while t + 1 < n:
        pair = rho[t] + rho[t + 1]
        if pair < 0:
            break
        s += pair
        t += 2
    tau = 1.0 + 2.0 * s
    return float(m * n / max(tau, 1e-6))


# overdispersed starting points for the four population parameters
INITS = [dict(r=0.5, alpha=5.0, s=0.5, beta=5.0),
         dict(r=2.0, alpha=30.0, s=2.0, beta=30.0),
         dict(r=1.0, alpha=15.0, s=0.3, beta=3.0),
         dict(r=0.3, alpha=3.0, s=1.5, beta=40.0)]


def diagnose(name, df, horizon=26, n_draws=40000, burn=10000, thin=5):
    from score import spp_predict, randomized_pit, crps_samples, coverage
    cols = ["r", "alpha", "s", "beta"]
    chains = {c: [] for c in cols + ["E_lambda", "E_mu"]}
    raw_El, per_chain_scores = [], []
    y = df[f"x_star_{horizon}"].to_numpy(float)
    Tcal = df["T_cal"].to_numpy(float)
    for ch, ini in enumerate(INITS):
        mc = fit_mcmc(df, n_draws=n_draws, burn_in=burn, thin=thin, seed=100 + ch, init=ini)
        pd_ = mc.pop_draws                       # (n_keep, 4)
        for j, c in enumerate(cols):
            chains[c].append(pd_[:, j])
        chains["E_lambda"].append(pd_[:, 0] / pd_[:, 1])
        chains["E_mu"].append(pd_[:, 2] / pd_[:, 3])
        raw_El.append(pd_[:, 0] / pd_[:, 1])
        # forecast scores from THIS chain only (reproducibility across chains)
        pred = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(500 + ch))
        pit = randomized_pit(pred, y, np.random.default_rng(600 + ch))
        per_chain_scores.append((crps_samples(pred, y).mean(),
                                 coverage(pred, y)[0.95],
                                 float(np.max(np.abs(np.sort(pit) - np.arange(1, len(pit) + 1) / len(pit))))))
    kept = len(raw_El[0])
    print(f"\n=== {name} (N={len(df)}, 4 overdispersed chains x {n_draws} draws, "
          f"{kept} kept/chain) ===")
    print(f"  {'param':10s}{'Rhat':>8s}{'ESS':>9s}")
    worst_rhat, worst_ess = 0.0, 1e18
    for c in cols + ["E_lambda", "E_mu"]:
        arr = np.array(chains[c])
        rh = split_rhat(arr); es = ess(arr)
        worst_rhat = max(worst_rhat, rh); worst_ess = min(worst_ess, es)
        print(f"  {c:10s}{rh:>8.3f}{es:>9.0f}")
    print(f"  --> max Rhat = {worst_rhat:.3f}, min ESS = {worst_ess:.0f}")
    ps = np.array(per_chain_scores)
    print(f"  forecast-score reproducibility across the 4 chains (all customers):")
    print(f"     CRPS   = {ps[:,0].mean():.4f} +/- {ps[:,0].std():.4f}  (range {ps[:,0].min():.4f}-{ps[:,0].max():.4f})")
    print(f"     cov95  = {ps[:,1].mean():.4f} +/- {ps[:,1].std():.4f}")
    print(f"     PIT-KS = {ps[:,2].mean():.4f} +/- {ps[:,2].std():.4f}")
    return raw_El, worst_rhat, worst_ess


def main():
    rng = np.random.default_rng(7)
    sim = simulate_dataset(DatasetParams(0.15, 1.3, 0.08, 1.2, N=800, T=52.0), rng=rng)
    el_sim, rh_s, es_s = diagnose("Simulated cohort", sim)
    cdnow = elog_to_summary(load_cdnow(), 39, 26)
    el_cd, rh_c, es_c = diagnose("CDNow", cdnow)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    for ax, (title, el) in zip(axes, [("Simulated cohort (N=800)", el_sim),
                                      ("CDNow (N=2357)", el_cd)]):
        for ch in el:
            ax.plot(ch, lw=0.6, alpha=0.8)
        ax.set_title(f"{title}: $E(\\lambda)$ traces, 4 chains")
        ax.set_xlabel("kept draw"); ax.set_ylabel("$E(\\lambda)$")
    fig.suptitle("MCMC mixing of the population mean purchase rate "
                 f"(max $\\hat R$ = {max(rh_s, rh_c):.3f})")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = FIG / "fig6_convergence.png"
    fig.savefig(out, dpi=140); print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
