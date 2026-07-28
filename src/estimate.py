"""
Pareto/NBD estimation.

Faithful pure-numpy/scipy reproduction of the Abe (2009) / BTYDplus MCMC (Gibbs)
sampler used by Simon (2025), Appendix. Data augmentation gives the latent dropout
time tau_i, which turns every full-conditional into a closed-form draw:

  lambda_i | .  ~ Gamma(shape = x_i + r,  rate = alpha + min(tau_i, T_i))
  mu_i     | .  ~ Gamma(shape = s + 1,    rate = beta  + tau_i)
  z_i      | .  ~ Bernoulli( P(alive at T_i) )      (alive indicator)
  tau_i    | .  ~ T_i + Exp(mu_i)                   if alive (z_i = 1)
                ~ double-truncated Exp(lambda_i+mu_i) on (t_x,i, T_i)  if z_i = 0
  alpha    | .  ~ Gamma(a0 + n*r, b0 + sum lambda_i)   (conjugate)
  beta     | .  ~ Gamma(c0 + n*s, d0 + sum mu_i)       (conjugate)
  r        | .  via 1-D slice sampling  (shape of the lambda-Gamma)
  s        | .  via 1-D slice sampling  (shape of the mu-Gamma)

Also provides an MLE fit of the population parameters {r, alpha, s, beta} via the
closed-form Pareto/NBD likelihood (Fader & Hardie 2005) for the MLE-vs-MCMC contrast.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize
from scipy.special import gammaln, hyp2f1

# ---------------------------------------------------------------------------
# Weakly-informative hyper-priors (tunable). alpha,beta ~ Gamma(a0,b0)/(c0,d0);
# r,s ~ Gamma(ar,br)/(as_,bs). Set vague; note the choice in the paper's methods.
# ---------------------------------------------------------------------------
HYPER = dict(a0=1e-3, b0=1e-3, c0=1e-3, d0=1e-3, ar=1.0, br=1.0, as_=1.0, bs=1.0)


# ============================ MCMC (Gibbs) ================================= #
def _slice_sample(x0: float, logf, w: float = 1.0, lower: float = 1e-6,
                  m: int = 50, rng: np.random.Generator = None) -> float:
    """One univariate slice-sampler update (Neal 2003, stepping-out)."""
    y = logf(x0) + np.log(rng.uniform())
    # step out
    L = x0 - w * rng.uniform()
    R = L + w
    L = max(L, lower)
    j = int(m * rng.uniform()); k = m - 1 - j
    while j > 0 and L > lower and logf(L) > y:
        L = max(L - w, lower); j -= 1
    while k > 0 and logf(R) > y:
        R += w; k -= 1
    # shrink
    for _ in range(100):
        x1 = L + (R - L) * rng.uniform()
        if logf(x1) > y:
            return x1
        if x1 < x0:
            L = x1
        else:
            R = x1
    return x0


@dataclass
class MCMCResult:
    pop_draws: np.ndarray          # (n_keep, 4) columns r, alpha, s, beta
    lam: np.ndarray                # (n_keep, N) individual purchase rates
    mu: np.ndarray                 # (n_keep, N) individual dropout rates
    tau: np.ndarray                # (n_keep, N) individual latent lifetimes
    T_cal: np.ndarray              # (N,) individual calibration lengths

    def pop_summary(self) -> dict:
        m = self.pop_draws.mean(axis=0)
        return {"r": m[0], "alpha": m[1], "s": m[2], "beta": m[3],
                "E_lambda": m[0] / m[1], "E_mu": m[2] / m[3]}


def fit_mcmc(df, n_draws: int = 6000, burn_in: int = 2000, thin: int = 8,
             seed: int = 0, hyper: dict = None, init: dict = None) -> MCMCResult:
    """Run the Gibbs sampler on a simulated/empirical cohort dataframe with
    columns x, t_x, T_cal.  Returns kept draws (population + individual).

    Pass ``init`` (keys r, alpha, s, beta) to start from a dispersed point; this is
    used by the convergence diagnostics to run overdispersed chains for split-Rhat."""
    h = {**HYPER, **(hyper or {})}
    rng = np.random.default_rng(seed)
    x = df["x"].to_numpy(float)
    t_x = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)
    n = len(x)

    # init (overridable for overdispersed-start diagnostics)
    r, alpha, s, beta = 1.0, 10.0, 1.0, 10.0
    if init:
        r, alpha, s, beta = init["r"], init["alpha"], init["s"], init["beta"]
    lam = np.full(n, 0.1)
    mu = np.full(n, 0.1)
    tau = T + 1.0  # start everyone "alive"

    keep_pop, keep_lam, keep_mu, keep_tau = [], [], [], []
    for it in range(n_draws):
        # 2. lambda_i
        lam = rng.gamma(shape=x + r, scale=1.0 / (alpha + np.minimum(tau, T)))
        # 3. mu_i
        mu = rng.gamma(shape=s + 1.0, scale=1.0 / (beta + tau))
        # 4. alive indicator z_i
        rate = lam + mu
        d = T - t_x                        # time since last purchase
        ealive = np.exp(-rate * d)
        p_alive = ealive / (ealive + (mu / rate) * (1.0 - ealive))
        z = rng.uniform(size=n) < p_alive
        # 7-8. tau_i
        tau = np.empty(n)
        # alive: dropout after T
        tau[z] = T[z] + rng.exponential(1.0 / mu[z])
        # dropped: double-truncated Exp(rate) on (t_x, T)
        nz = ~z
        if nz.any():
            u = rng.uniform(size=nz.sum())
            rr = rate[nz]
            inside = (1 - u) * np.exp(-rr * t_x[nz]) + u * np.exp(-rr * T[nz])
            tau[nz] = -np.log(inside) / rr
        # 9. population params: alpha,beta conjugate; r,s via slice
        sum_lam, sum_mu = lam.sum(), mu.sum()
        sum_log_lam, sum_log_mu = np.log(lam).sum(), np.log(mu).sum()
        alpha = rng.gamma(shape=h["a0"] + n * r, scale=1.0 / (h["b0"] + sum_lam))
        beta = rng.gamma(shape=h["c0"] + n * s, scale=1.0 / (h["d0"] + sum_mu))

        def logf_r(rv, a=alpha, sl=sum_log_lam):
            if rv <= 0:
                return -np.inf
            return (n * rv * np.log(a) + (rv - 1) * sl - n * gammaln(rv)
                    + (h["ar"] - 1) * np.log(rv) - h["br"] * rv)

        def logf_s(sv, b=beta, sm=sum_log_mu):
            if sv <= 0:
                return -np.inf
            return (n * sv * np.log(b) + (sv - 1) * sm - n * gammaln(sv)
                    + (h["as_"] - 1) * np.log(sv) - h["bs"] * sv)

        r = _slice_sample(r, logf_r, w=max(0.5, r), rng=rng)
        s = _slice_sample(s, logf_s, w=max(0.5, s), rng=rng)

        if it >= burn_in and (it - burn_in) % thin == 0:
            keep_pop.append((r, alpha, s, beta))
            keep_lam.append(lam.copy()); keep_mu.append(mu.copy()); keep_tau.append(tau.copy())

    return MCMCResult(
        pop_draws=np.array(keep_pop),
        lam=np.array(keep_lam), mu=np.array(keep_mu), tau=np.array(keep_tau),
        T_cal=T,
    )


# ============================== MLE ======================================= #
def _pnbd_loglik(params, x, t_x, T):
    """Pareto/NBD log-likelihood, log-parameterised (Fader & Hardie 2005 form).

    r, alpha, s, beta are scalars; x, t_x, T are per-customer vectors. The
    alpha>=beta test is therefore a single dataset-level branch, and the second
    hypergeometric argument is s+1 (alpha>=beta) or r+x (alpha<beta)."""
    r, alpha, s, beta = np.exp(params)
    maxab = max(alpha, beta)
    absum = abs(alpha - beta)
    rsx = r + s + x
    param2 = (s + 1.0) if alpha >= beta else (r + x)
    A0 = (hyp2f1(rsx, param2, rsx + 1.0, absum / (maxab + t_x))
          / (maxab + t_x) ** rsx
          - hyp2f1(rsx, param2, rsx + 1.0, absum / (maxab + T))
          / (maxab + T) ** rsx)
    p1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha) + s * np.log(beta)
    inner = 1.0 / (alpha + T) ** (r + x) / (beta + T) ** s + (s / rsx) * A0
    term = np.log(np.maximum(inner, 1e-300))
    ll = np.sum(p1 + term)
    # guard: overflow/divergence in the power terms yields garbage (e.g. positive
    # log-liks of +1e6). Any non-finite total is invalid -> reject.
    return ll if np.isfinite(ll) else -np.inf


_LO, _HI = np.log(1e-5), np.log(1e5)  # log-param bounds to prevent divergence


def fit_mle(df, seed: int = 0, n_start: int = 3, x0=None) -> dict:
    """Maximum-likelihood estimate of {r, alpha, s, beta}.

    Robustified: (1) log-parameters bounded to [1e-5, 1e5] so the optimiser cannot
    wander into the overflow region that produces spurious positive log-liks;
    (2) a data-driven method-of-moments start (E(lambda)~mean(x)/mean(T), r=s=1);
    (3) multistart around it. Pass x0 (log-scale) to add a warm start."""
    x = df["x"].to_numpy(float)
    t_x = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)

    def neg(p):
        if np.any(p < _LO) or np.any(p > _HI):
            return 1e12
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            ll = _pnbd_loglik(p, x, t_x, T)
        return -ll if np.isfinite(ll) else 1e12

    # method-of-moments start
    mean_x = max(x.mean(), 0.1)
    mean_T = max(T.mean(), 1.0)
    El0 = min(max(mean_x / mean_T, 0.01), 0.5)
    Em0 = min(max(1.0 / mean_T, 0.005), 0.2)
    mom = np.log([1.0, 1.0 / El0, 1.0, 1.0 / Em0])

    rng = np.random.default_rng(seed)
    starts = [mom]
    if x0 is not None:
        starts.insert(0, np.clip(np.asarray(x0, float), _LO, _HI))
    for _ in range(max(0, n_start - 1)):
        starts.append(np.clip(mom + rng.normal(0, 0.6, size=4), _LO, _HI))

    best = None
    for st in starts:
        res = optimize.minimize(neg, st, method="Nelder-Mead",
                                options=dict(maxiter=3000, xatol=1e-5, fatol=1e-5))
        # sanity: legitimate log-lik is negative here; reject overflow solutions
        # (spurious large positive log-lik -> res.fun very negative).
        if -10.0 < res.fun < 1e11 and (best is None or res.fun < best.fun):
            best = res
    if best is None:  # last-resort: optimise from the (near-truth) MoM start only
        best = optimize.minimize(neg, mom, method="Nelder-Mead",
                                 options=dict(maxiter=3000))
    r, alpha, s, beta = np.exp(best.x)
    return {"r": r, "alpha": alpha, "s": s, "beta": beta, "logparams": best.x,
            "E_lambda": r / alpha, "E_mu": s / beta, "loglik": -best.fun}


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from simulate import DatasetParams, simulate_dataset

    # Parameter-recovery validation on a moderate cohort with known truth.
    truth = DatasetParams(E_lambda=0.15, CV_lambda=1.2, E_mu=0.08, CV_mu=1.0,
                          N=1500, T=52.0)
    rng = np.random.default_rng(7)
    df = simulate_dataset(truth, rng=rng)
    print("TRUE   :", {k: round(v, 4) for k, v in truth.as_dict().items()
                       if k in ("r", "alpha", "s", "beta", "E_lambda", "E_mu")})
    mle = fit_mle(df)
    print("MLE    :", {k: round(v, 4) for k, v in mle.items() if k != "loglik"})
    mc = fit_mcmc(df, n_draws=3000, burn_in=1000, thin=5, seed=1)
    print("MCMC   :", {k: round(v, 4) for k, v in mc.pop_summary().items()})
