"""
Gap G5: discounting in the CLV layer -- does the time-value of money reshuffle the Top-A% ranking?

CLV in the source literature is the expected *discounted* future cash flow (Gupta et al. 2006), but
`clv.py`'s only discount hook is a single flat factor exp(-delta) applied to every customer -- which,
being constant, cannot change any ranking. Proper discounting is *per customer*: a purchase at time
t inside the forecast window (T, T+T*] is worth exp(-delta*t). For a customer alive for an overlap
L_i = min(tau_i, T+T*) - T, with purchases approximately uniform on (0, L_i], the expected discount
factor is

    D_i(delta) = (1 - exp(-delta * L_i)) / (delta * L_i),      D_i -> 1 as delta*L_i -> 0,

so discounted CLV_i = x*_i * nu_i * D_i. Because D_i depends on the customer's alive-overlap L_i
(hence on churn timing), discounting is now customer-specific and *can* reshuffle the Top-A%.

We sweep the annual discount rate and the horizon, and report (i) total-CLV shrinkage, (ii) the
Top-10% membership overlap vs the undiscounted ranking, and (iii) the Spearman rank correlation.
Honest expectation: at realistic rates over a single finite horizon the reshuffle is small (timing
differences within one short window are minor next to spend/frequency differences); it grows with
the rate and the horizon -- the regime where discounting genuinely matters is long/multi-period CLV.

Saves results/clv_discount_summary.csv; prints the table.

Run:  python src/run_clv_discount.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

RES = Path(__file__).resolve().parent.parent / "results"
SEEDS = 4
ANNUAL_RATES = [0.10, 0.30, 1.00]        # -> weekly delta = ln(1+a)/52
HORIZONS = [26, 52]
TOP_A = 0.10


def discount_factor(L, delta):
    """Per-customer expected discount factor for purchases uniform on (0, L]."""
    dL = delta * L
    with np.errstate(divide="ignore", invalid="ignore"):
        D = np.where(dL > 1e-9, (1.0 - np.exp(-dL)) / dL, 1.0)
    return D


def one(df, horizon, seed, mcmc_draws=1500):
    from estimate import fit_mcmc
    from score import spp_predict
    from clv import fit_gamma_gamma, sample_posterior_nu

    Tcal = df["T_cal"].to_numpy(float)
    x = df["x"].to_numpy(float)
    m_bar = df["m_bar"].to_numpy(float)

    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    counts = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    L = np.clip(np.minimum(mc.tau, Tcal[None, :] + horizon) - Tcal[None, :], 0.0, None)  # (J, N)
    gg = fit_gamma_gamma(x, m_bar)
    nu = sample_posterior_nu(x, m_bar, gg["p"], gg["q"], gg["v"], n_draws=counts.shape[0], seed=seed + 3)

    clv_undisc = (counts * nu).mean(axis=0)                       # E[CLV] per customer, no discount
    out = []
    for a in ANNUAL_RATES:
        delta = np.log1p(a) / 52.0                                # weekly continuous rate
        clv_disc = (counts * nu * discount_factor(L, delta)).mean(axis=0)
        # Top-A% membership overlap + rank correlation vs the undiscounted ranking
        k = max(1, int(round(TOP_A * len(clv_undisc))))
        top_u = set(np.argsort(-clv_undisc)[:k])
        top_d = set(np.argsort(-clv_disc)[:k])
        overlap = len(top_u & top_d) / k
        rho = stats.spearmanr(clv_undisc, clv_disc).correlation
        out.append(dict(seed=seed, horizon=horizon, annual_rate=a,
                        clv_shrinkage=1.0 - clv_disc.sum() / max(clv_undisc.sum(), 1e-9),
                        topA_overlap=overlap, rank_corr=rho))
    return out


def main():
    from clv_data import load_clv_summary
    rows = []
    for name in ["OnlineRetailII", "Dunnhumby"]:
        df, _ = load_clv_summary(name)
        t = time.time()
        for seed in range(SEEDS):
            for h in HORIZONS:
                for rec in one(df, h, seed=8000 + seed):
                    rec["dataset"] = name
                    rows.append(rec)
        print(f"[{name}] {SEEDS} seeds x {len(HORIZONS)} horizons done ({time.time()-t:.0f}s)", flush=True)

    raw = pd.DataFrame(rows)
    summ = (raw.groupby(["dataset", "horizon", "annual_rate"])
            .mean(numeric_only=True).drop(columns="seed").reset_index())
    summ.to_csv(RES / "clv_discount_summary.csv", index=False)

    print("\n=== CLV discounting: effect on magnitude and Top-10% ranking (mean over seeds) ===")
    print(f"{'dataset':16s}{'horizon':>8s}{'annual%':>9s}{'CLV shrink':>12s}"
          f"{'top10 overlap':>15s}{'rank corr':>11s}")
    for _, r in summ.iterrows():
        print(f"{r.dataset:16s}{int(r.horizon):>8d}{100*r.annual_rate:>8.0f}%"
              f"{100*r.clv_shrinkage:>11.1f}%{100*r.topA_overlap:>14.1f}%{r.rank_corr:>11.4f}")
    print("\nRead: a flat discount cannot reshuffle a ranking; per-customer discounting can, but the")
    print("Top-10% overlap stays high at realistic rates/horizons -- discounting rescales CLV far")
    print("more than it reorders it within a single finite window.")
    print(f"[saved] {RES/'clv_discount_summary.csv'}")


if __name__ == "__main__":
    main()
