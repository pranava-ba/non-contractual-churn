"""
Closed-form per-customer Pareto/NBD forecasts for the fast (non-MCMC) scoring path.

Given population parameters (r, alpha, s, beta) -- e.g. from the amortized neural
estimator or ``estimate.fit_mle`` -- and a customer's calibration summary
(x = repeat purchases, t_x = recency, T = observed length, all acquisition-relative),
this module returns:

  * ``p_alive``                  -- EXACT P(alive at T | x, t_x, T)
                                    (Schmittlein, Morrison & Colombo 1987, in the
                                    Fader & Hardie 2005 parameterisation)
  * ``expected_purchases``       -- documented APPROXIMATION of E[Y(T, T+h) | x, t_x, T]
  * ``expected_purchases_exact`` -- the exact conditional expectation (Schmittlein et
                                    al. 1987), derived in its docstring and provided so
                                    the approximation's gap can be quantified

Parameterisation. ``p_alive`` reuses term-for-term the likelihood decomposition of
``estimate._pnbd_loglik`` (same ``maxab``, ``absum``, ``rsx``, ``param2`` and the same
hyp2f1-based ``A0``):

    L_i   = p1_i * (term1_i + term2_i)
    term1 = 1 / ((alpha+T)^(r+x) (beta+T)^s)        # alive-at-T branch
    term2 = (s / (r+s+x)) * A0                      # died-in-(t_x, T] branch
    P(alive) = term1 / (term1 + term2) = 1 / (1 + R),   R = term2 / term1

Numerics. term1 and A0 both underflow for heavy buyers, so R is formed in log space
(``_log_alive_odds``) rather than as a quotient of two tiny floats -- mathematically
identical.  In the alpha < beta branch the hypergeometric factor itself can overflow
for very heavy buyers ((r+x) * log((beta+t_x)/(alpha+t_x)) > ~709, e.g. x ~ 400+ with
beta/alpha ~ 6); for exactly those customers R is evaluated from its defining 1-D
integral by adaptive quadrature (``_log_alive_odds_quad``), which needs no hyp2f1.

Inputs: r, alpha, s, beta are positive scalars; x, t_x, T are array-likes of equal
(broadcastable) shape with x >= 0 and 0 <= t_x <= T.  Outputs are float ndarrays.
"""

from __future__ import annotations

import numpy as np
from scipy import integrate
from scipy.special import expit, hyp2f1


def _as_arrays(x, t_x, T):
    x = np.asarray(x, dtype=float)
    t_x = np.asarray(t_x, dtype=float)
    T = np.asarray(T, dtype=float)
    x, t_x, T = np.broadcast_arrays(x, t_x, T)
    if np.any(x < 0) or np.any(t_x < 0) or np.any(t_x > T):
        raise ValueError("require x >= 0 and 0 <= t_x <= T")
    return x, t_x, T


def _check_params(r, alpha, s, beta):
    vals = [float(v) for v in (r, alpha, s, beta)]
    if not all(np.isfinite(v) and v > 0 for v in vals):
        raise ValueError(f"r, alpha, s, beta must be finite and > 0, got {vals}")
    return vals


def _log_alive_odds_quad(r, alpha, s, beta, x, t_x, T):
    """log R for ONE customer from the defining integral (no hyp2f1).

    term2 = s * int_{t_x}^{T} (alpha+tau)^-(r+x) (beta+tau)^-(s+1) dtau  (= (s/rsx) A0;
    the dropout time tau integrated against the Gamma mixing distributions), so

      R = int_{t_x}^{T} s/(beta+tau) * exp(E(tau)) dtau,
      E(tau) = (r+x) log((alpha+T)/(alpha+tau)) + s log((beta+T)/(beta+tau)),

    with E decreasing in tau.  E(t_x) is factored out so the integrand is in (0, 1]."""
    if t_x >= T:
        return -np.inf

    def E(tau):
        return ((r + x) * (np.log(alpha + T) - np.log(alpha + tau))
                + s * (np.log(beta + T) - np.log(beta + tau)))

    e_max = E(t_x)
    # integrand decays from t_x on a scale ~ 1 / (decay rate of E); hint quad at it
    scale = 1.0 / ((r + x) / (alpha + t_x) + s / (beta + t_x))
    pts = [p for p in (t_x + scale, t_x + 10 * scale, t_x + 100 * scale) if p < T]
    val, _ = integrate.quad(lambda tau: s / (beta + tau) * np.exp(E(tau) - e_max),
                            t_x, T, points=pts or None, epsabs=0.0, epsrel=1e-11,
                            limit=500)
    return e_max + np.log(val) if val > 0 else -np.inf


def _log_alive_odds(r, alpha, s, beta, x, t_x, T):
    """log(term2 / term1) of the ``estimate._pnbd_loglik`` decomposition, vectorised.

    With m = max(alpha, beta), H(t) = 2F1(rsx, param2; rsx+1; |alpha-beta|/(m+t)):
      l1 = log H(t_x) - rsx log(m+t_x),   l2 = log H(T) - rsx log(m+T)   (l1 >= l2)
      log A0 = l1 + log(1 - exp(l2 - l1))
      log R  = log(s/rsx) + log A0 + (r+x) log(alpha+T) + s log(beta+T)."""
    maxab = max(alpha, beta)
    absum = abs(alpha - beta)
    rsx = r + s + x
    param2 = (s + 1.0) if alpha >= beta else (r + x)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        H_tx = hyp2f1(rsx, param2, rsx + 1.0, absum / (maxab + t_x))
        H_T = hyp2f1(rsx, param2, rsx + 1.0, absum / (maxab + T))
        ok = np.isfinite(H_tx) & np.isfinite(H_T) & (H_tx > 0) & (H_T > 0)
        l1 = np.log(H_tx) - rsx * np.log(maxab + t_x)
        # l2 - l1 computed as a difference of small pieces (accurate when t_x ~ T)
        d = (np.log(H_T) - np.log(H_tx)
             - rsx * np.log1p((T - t_x) / (maxab + t_x)))                # <= 0
        log_one_minus = np.where(d < 0, np.log(-np.expm1(np.minimum(d, -1e-300))),
                                 -np.inf)                                # d >= 0 -> A0 = 0
        log_R = (np.log(s) - np.log(rsx) + l1 + log_one_minus
                 + (r + x) * np.log(alpha + T) + s * np.log(beta + T))
    log_R = np.where(ok, log_R, np.nan)
    for i in zip(*np.nonzero(~ok)):        # rare: hyp2f1 overflow -> exact quadrature
        log_R[i] = _log_alive_odds_quad(r, alpha, s, beta, x[i], t_x[i], T[i])
    return log_R


def p_alive(r, alpha, s, beta, x, t_x, T) -> np.ndarray:
    """EXACT Pareto/NBD probability that a customer is alive at the end of calibration.

    P(alive | x, t_x, T; r, alpha, s, beta) = term1 / (term1 + term2), where term1 and
    term2 are the alive-at-T and died-in-(t_x, T] branches of the Fader & Hardie (2005)
    likelihood exactly as written in ``estimate._pnbd_loglik`` (Schmittlein, Morrison &
    Colombo 1987): P(alive) is the alive branch's share of the total likelihood mass.
    Vectorised over customers; always in [0, 1].
    """
    r, alpha, s, beta = _check_params(r, alpha, s, beta)
    x, t_x, T = _as_arrays(x, t_x, T)
    log_R = _log_alive_odds(r, alpha, s, beta, np.atleast_1d(x), np.atleast_1d(t_x),
                            np.atleast_1d(T))
    out = expit(-log_R).reshape(x.shape)   # 1/(1+R); log_R = +inf -> 0, -inf -> 1
    if not np.all(np.isfinite(out)):
        raise FloatingPointError("p_alive produced non-finite values for these inputs")
    return out


def expected_purchases(r, alpha, s, beta, x, t_x, T, horizon) -> np.ndarray:
    """APPROXIMATE expected number of repeat purchases in (T, T + horizon].

        expected_purchases = p_alive * (r + x) / (alpha + T) * horizon

    Rationale.  (r + x) / (alpha + T) is the Gamma-Poisson posterior mean purchase rate
    E[lambda | r, alpha, x, T]: purchases ~ Poisson(lambda), lambda ~ Gamma(r, alpha) a
    priori, and after x purchases in an exposure of length T the posterior is
    Gamma(r + x, alpha + T), whose mean is (r + x) / (alpha + T).  (Within the Pareto/NBD
    this is exactly the posterior of lambda *conditional on being alive at T*, so
    p_alive * (r + x)/(alpha + T) = E[lambda * 1{alive at T}] with no approximation.)
    Multiplying by the horizon gives the expected future purchase count IF the
    customer's alive/dead status at T stayed fixed for the whole future window.

    Known gap -- this is NOT the literature's exact closed form.  A customer alive at T
    can still die partway through (T, T + horizon] and make no purchases after that;
    the exact expectation replaces ``horizon`` by the expected remaining active time in
    the window, E[(1 - exp(-mu*h)) / mu | alive at T] < h.  Hence, for every customer
    and horizon > 0, this approximation OVER-states the expectation, by the factor
        horizon / [(beta+T)/(s-1) * (1 - ((beta+T)/(beta+T+horizon))^(s-1))]
    which depends only on (s, beta, T, horizon) -- it grows with the horizon and with the
    dropout rate.  On simulated cohorts (tests/test_forecast_closed_form.py) the
    cohort-mean overstatement vs. MCMC + simulation ground truth was ~8-10% at h=13,
    ~16-19% at h=26 and ~30-36% at h=52 weeks.  Because the factor is shared by all
    customers with the same T, the approximation preserves per-customer rankings almost
    exactly.  Use ``expected_purchases_exact`` where the level matters.
    """
    x, t_x, T = _as_arrays(x, t_x, T)
    if not horizon >= 0:
        raise ValueError("horizon must be >= 0")
    pa = p_alive(r, alpha, s, beta, x, t_x, T)
    return pa * (r + x) / (alpha + T) * float(horizon)


def _expected_active_time(s, beta, T, horizon):
    """E[(1 - exp(-mu h)) / mu] for mu ~ Gamma(s, rate=beta+T): the expected time a
    customer alive at T stays alive within (T, T+h].  Equals
    (beta+T)/(s-1) * [1 - ((beta+T)/(beta+T+h))^(s-1)], evaluated as
    -(beta+T) * L * expm1(a)/a with L = log((beta+T)/(beta+T+h)), a = (s-1) L, which
    is exact for every s > 0 including the s -> 1 limit (beta+T) log((beta+T+h)/(beta+T))."""
    L = np.log(beta + T) - np.log(beta + T + horizon)                  # <= 0
    a = (s - 1.0) * L
    with np.errstate(invalid="ignore", divide="ignore"):
        phi = np.where(np.abs(a) < 1e-8, 1.0 + a / 2.0 + a * a / 6.0, np.expm1(a) / a)
    return -(beta + T) * L * phi                                         # in [0, h]


def expected_purchases_exact(r, alpha, s, beta, x, t_x, T, horizon) -> np.ndarray:
    """EXACT E[Y(T, T + horizon) | x, t_x, T] under the Pareto/NBD (Schmittlein et al. 1987).

        E = p_alive * (r+x)/(alpha+T) * (beta+T)/(s-1) * [1 - ((beta+T)/(beta+T+h))^(s-1)]

    Derivation.  Dead-at-T customers contribute 0.  Conditional on alive at T the
    posterior factorises: the alive branch of the likelihood is
    lambda^x e^{-lambda T} * e^{-mu T}, so lambda ~ Gamma(r+x, alpha+T) and
    mu ~ Gamma(s, beta+T), independently.  Given (lambda, mu) and alive at T, the
    memoryless exponential lifetime gives E[purchases in window] = lambda (1 - e^{-mu h})/mu.
    Taking expectations: E[lambda] = (r+x)/(alpha+T) and
        E[(1 - e^{-mu h})/mu] = int_0^h E[e^{-mu u}] du = int_0^h ((beta+T)/(beta+T+u))^s du
                              = (beta+T)/(s-1) * [1 - ((beta+T)/(beta+T+h))^(s-1)].
    Verified in tests against independent 1-D quadrature and against MCMC + simulation.
    """
    r, alpha, s, beta = _check_params(r, alpha, s, beta)
    x, t_x, T = _as_arrays(x, t_x, T)
    if not horizon >= 0:
        raise ValueError("horizon must be >= 0")
    pa = p_alive(r, alpha, s, beta, x, t_x, T)
    return pa * (r + x) / (alpha + T) * _expected_active_time(s, beta, T, float(horizon))
