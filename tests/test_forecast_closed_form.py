"""Verification of the closed-form Pareto/NBD forecasts in src/forecast_closed_form.py.

Four independent lines of evidence:
  1. sanity: ranges / finiteness over a wide input grid, incl. heavy buyers;
  2. exactness: agreement with (a) an independent 1-D quadrature of the defining
     integrals (no hyp2f1) and (b) mpmath 50-digit reference values, and exact
     consistency with the already-tested likelihood ``estimate._pnbd_loglik``;
  3. monotonicity: recency / frequency / horizon scenarios with clear expected order;
  4. cross-validation against this repo's MCMC ground truth on simulated cohorts
     (``score.conditional_individual_draws`` at the MLE, and the full ``fit_mcmc``
     posterior, with ``score.spp_predict`` simulation for future purchases).
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import integrate, stats
from scipy.special import gammaln

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forecast_closed_form import (_log_alive_odds, _log_alive_odds_quad,
                                  expected_purchases, expected_purchases_exact, p_alive)
from estimate import _pnbd_loglik, fit_mcmc, fit_mle
from score import conditional_individual_draws, spp_predict
from simulate import DatasetParams, simulate_dataset

# (r, alpha, s, beta): both hypergeometric branches, s == 1 exactly, s < 1, s > 1
PARAM_SETS = [
    (0.7, 5.0, 0.6, 8.0),      # alpha < beta
    (0.7, 9.0, 0.6, 4.0),      # alpha >= beta
    (2.0, 10.0, 1.0, 10.0),    # alpha == beta, s == 1
    (1.44, 5.62, 0.85, 31.8),  # MLE-like values from a simulated cohort
    (0.3, 2.0, 2.5, 30.0),
    (5.0, 0.5, 0.1, 100.0),    # extreme alpha << beta (hyp2f1 overflow region)
]


# ------------------------------ 1. sanity ---------------------------------- #
@pytest.mark.parametrize("params", PARAM_SETS)
def test_ranges_and_finiteness_over_grid(params):
    xs, rec, Ts = [0, 1, 2, 5, 20, 100, 500, 2000], [0.0, 0.1, 0.5, 0.9, 0.99, 1.0], [1.0, 26.0, 52.0, 100.0]
    X, F, TT = (a.ravel() for a in np.meshgrid(xs, rec, Ts, indexing="ij"))
    tx = np.where(X > 0, F * TT, 0.0)
    pa = p_alive(*params, X, tx, TT)
    assert np.all(np.isfinite(pa))
    assert np.all((pa >= 0.0) & (pa <= 1.0))
    for h in (0.0, 13.0, 52.0):
        ea = expected_purchases(*params, X, tx, TT, h)
        ex = expected_purchases_exact(*params, X, tx, TT, h)
        assert np.all(np.isfinite(ea)) and np.all(np.isfinite(ex))
        assert np.all(ea >= 0.0) and np.all(ex >= 0.0)
        # documented direction of the approximation: never below the exact value
        assert np.all(ea >= ex * (1 - 1e-12))
        if h == 0.0:
            assert np.all(ea == 0.0) and np.all(ex == 0.0)


def test_shapes_scalars_and_validation():
    r, a, s, b = PARAM_SETS[0]
    assert np.ndim(p_alive(r, a, s, b, 3, 20.0, 40.0)) == 0
    assert p_alive(r, a, s, b, np.ones((2, 3)), np.ones((2, 3)), 40.0).shape == (2, 3)
    with pytest.raises(ValueError):
        p_alive(r, a, s, b, 3, 41.0, 40.0)           # t_x > T
    with pytest.raises(ValueError):
        p_alive(r, a, s, b, -1, 1.0, 40.0)           # x < 0
    with pytest.raises(ValueError):
        p_alive(-r, a, s, b, 3, 20.0, 40.0)          # invalid population parameter
    with pytest.raises(ValueError):
        expected_purchases(r, a, s, b, 3, 20.0, 40.0, -1.0)


# ------------------------------ 2. exactness ------------------------------- #
def _quadrature_reference(r, a, s, b, x, tx, T, h):
    """P(alive) and exact E[Y] from 1-D integrals, independent of hyp2f1.
    Scaled by (a+T)^(r+x) (b+T)^s:  alive mass = 1,
    dead mass = int_tx^T s (a+T)^(r+x) (b+T)^s / ((a+tau)^(r+x) (b+tau)^(s+1)) dtau,
    future = (r+x)/(a+T) * int_0^h ((b+T)/(b+T+u))^s du  (alive-branch mass)."""
    f = lambda tau: ((a + T) / (a + tau)) ** (r + x) * s / (b + tau) * ((b + T) / (b + tau)) ** s
    dead = integrate.quad(f, tx, T, epsabs=0, epsrel=1e-12, limit=500)[0]
    g = lambda u: ((b + T) / (b + T + u)) ** s
    fut = (r + x) / (a + T) * integrate.quad(g, 0, h, epsabs=0, epsrel=1e-12, limit=500)[0]
    return 1.0 / (1.0 + dead), fut / (1.0 + dead)


@pytest.mark.parametrize("params", PARAM_SETS[:5])
@pytest.mark.parametrize("cust", [(3, 20.0, 40.0), (0, 0.0, 30.0), (8, 39.0, 40.0),
                                  (5, 5.0, 50.0), (12, 30.0, 45.0), (40, 51.0, 52.0)])
@pytest.mark.parametrize("h", [13.0, 52.0])
def test_matches_independent_quadrature(params, cust, h):
    x, tx, T = cust
    q_pa, q_e = _quadrature_reference(*params, x, tx, T, h)
    assert float(p_alive(*params, x, tx, T)) == pytest.approx(q_pa, rel=1e-8, abs=1e-14)
    assert float(expected_purchases_exact(*params, x, tx, T, h)) == pytest.approx(q_e, rel=1e-8, abs=1e-14)


# mpmath (50 significant digits) evaluation of term1/(term1+term2) with exactly the
# _pnbd_loglik parameterisation.  The last three are in the region where scipy's
# hyp2f1 overflows and p_alive takes the quadrature fallback.
MPMATH_REFERENCE = [
    ((5.0, 0.5, 0.1, 100.0, 200, 51.0, 52.0), 0.99163241068804212445),
    ((1.44, 5.62, 0.85, 31.8, 1500, 50.0, 52.0), 2.3456971872730111469e-20),
    ((1.44, 0.3, 0.85, 31.8, 800, 51.5, 52.0), 0.40630331273034994),
    ((5.0, 0.5, 0.1, 100.0, 3000, 51.9, 52.0), 0.99649010242791427062),
    ((1.44, 0.3, 0.85, 31.8, 2000, 51.75, 52.0), 0.20504350338569229),
    ((1.44, 0.3, 0.85, 31.8, 2000, 51.8, 52.0), 0.63811002628707075),
]


@pytest.mark.parametrize("args,ref", MPMATH_REFERENCE)
def test_matches_mpmath_reference_including_overflow_region(args, ref):
    assert float(p_alive(*args)) == pytest.approx(ref, rel=1e-9)


@pytest.mark.parametrize("params", PARAM_SETS[:5])
def test_quadrature_fallback_agrees_with_hyp2f1_path(params):
    rng = np.random.default_rng(0)
    x = rng.integers(0, 60, 40).astype(float)
    T = rng.uniform(10, 80, 40)
    tx = np.where(x > 0, T * rng.uniform(size=40) ** 0.3, 0.0)
    main = _log_alive_odds(*params, x, tx, T)
    quad = np.array([_log_alive_odds_quad(*params, *c) for c in zip(x, tx, T)])
    finite = np.isfinite(main)
    assert np.array_equal(finite, np.isfinite(quad))
    np.testing.assert_allclose(np.exp(-np.abs(main[finite] - quad[finite])), 1.0, atol=1e-8)


@pytest.mark.parametrize("params", PARAM_SETS[:5])
def test_consistent_with_pnbd_loglik(params):
    """log L_i = p1_i + log(term1_i) - log(p_alive_i), summed, must reproduce the
    repo's own (tested) closed-form likelihood exactly."""
    r, a, s, b = params
    rng = np.random.default_rng(1)
    x = rng.integers(0, 15, 60).astype(float)
    T = rng.uniform(20, 60, 60)
    tx = np.where(x > 0, rng.uniform(size=60) * T, 0.0)
    p1 = gammaln(r + x) - gammaln(r) + r * np.log(a) + s * np.log(b)
    log_term1 = -(r + x) * np.log(a + T) - s * np.log(b + T)
    mine = np.sum(p1 + log_term1 - np.log(p_alive(r, a, s, b, x, tx, T)))
    assert mine == pytest.approx(_pnbd_loglik(np.log(params), x, tx, T), rel=1e-11)


def test_s_equal_one_limit_is_continuous():
    r, a, b = 0.8, 6.0, 12.0
    vals = [float(expected_purchases_exact(r, a, s, b, 4, 30.0, 40.0, 26.0))
            for s in (1.0 - 1e-6, 1.0, 1.0 + 1e-6)]
    assert vals[0] == pytest.approx(vals[1], rel=1e-5)
    assert vals[2] == pytest.approx(vals[1], rel=1e-5)
    q = _quadrature_reference(r, a, 1.0, b, 4, 30.0, 40.0, 26.0)[1]
    assert vals[1] == pytest.approx(q, rel=1e-8)


# ----------------------------- 3. monotonicity ----------------------------- #
P_MONO = (0.72, 4.78, 0.87, 9.0)


@pytest.mark.parametrize("x,tx_recent,tx_stale,T", [
    (1, 50.0, 10.0, 52.0),     # one repeat purchase, last week vs ~10 months ago
    (3, 51.0, 30.0, 52.0),
    (6, 40.0, 20.0, 52.0),
    (12, 25.0, 24.0, 26.0),
    (25, 70.0, 50.0, 72.0),
])
def test_more_recent_activity_means_more_likely_alive(x, tx_recent, tx_stale, T):
    pa_recent = p_alive(*P_MONO, x, tx_recent, T)
    pa_stale = p_alive(*P_MONO, x, tx_stale, T)
    assert pa_recent > pa_stale
    for fn in (expected_purchases, expected_purchases_exact):
        assert fn(*P_MONO, x, tx_recent, T, 26) > fn(*P_MONO, x, tx_stale, T, 26)


@pytest.mark.parametrize("x_low,x_high,tx,T", [
    (1, 3, 50.0, 52.0),        # both bought last fortnight; one bought 3x as often
    (3, 6, 50.0, 52.0),
    (6, 12, 51.0, 52.0),
    (2, 10, 25.5, 26.0),
    (0, 1, 52.0, 52.0),        # zero-repeat vs one repeat purchase at the very end
])
def test_more_purchases_with_recent_activity_means_more_expected(x_low, x_high, tx, T):
    tx_low = tx if x_low > 0 else 0.0
    for fn in (expected_purchases, expected_purchases_exact):
        assert fn(*P_MONO, x_high, tx, T, 26) > fn(*P_MONO, x_low, tx_low, T, 26)


def test_frequent_buyer_gone_quiet_is_less_likely_alive():
    """The well-known Pareto/NBD property that makes 'more purchases => more expected'
    only a *general* rule: with the SAME long silence, a customer who used to buy
    often is more surely gone than an occasional buyer."""
    pa = p_alive(*P_MONO, np.array([1, 3, 6, 12]), 10.0, 52.0)
    assert np.all(np.diff(pa) < 0)


def test_horizon_monotonicity_and_growing_approximation_gap():
    hs = [1.0, 13.0, 26.0, 52.0, 104.0]
    ex = [float(expected_purchases_exact(*P_MONO, 4, 45.0, 52.0, h)) for h in hs]
    ea = [float(expected_purchases(*P_MONO, 4, 45.0, 52.0, h)) for h in hs]
    assert np.all(np.diff(ex) > 0) and np.all(np.diff(ea) > 0)
    ratio = np.array(ea) / np.array(ex)
    assert np.all(ratio > 1.0) and np.all(np.diff(ratio) > 0)


# ----------------- 4. cross-validation vs MCMC ground truth ----------------- #
COHORTS = {
    "slow_churn_heavy_tail": (11, DatasetParams(E_lambda=0.15, CV_lambda=1.2, E_mu=0.08,
                                                CV_mu=1.0, N=800, T=52.0)),
    "frequent_low_churn": (12, DatasetParams(E_lambda=0.25, CV_lambda=0.8, E_mu=0.04,
                                             CV_mu=1.5, N=800, T=40.0)),
}
HORIZONS = (13, 26, 52)


@pytest.fixture(scope="module", params=list(COHORTS))
def cohort(request):
    seed, truth = COHORTS[request.param]
    df = simulate_dataset(truth, rng=np.random.default_rng(seed))
    x, tx, T = (df[c].to_numpy(float) for c in ("x", "t_x", "T_cal"))
    mle = fit_mle(df, seed=1)
    pars = (mle["r"], mle["alpha"], mle["s"], mle["beta"])
    # MLE plug-in individual posterior: SAME target as the closed form, by MCMC
    lam, mu, tau = conditional_individual_draws(df, *pars, n_draws=1000, burn_in=200,
                                                thin=2, seed=3)
    # full Bayesian posterior (adds population-parameter uncertainty)
    mc = fit_mcmc(df, n_draws=4000, burn_in=1000, thin=3, seed=5)
    return dict(name=request.param, df=df, x=x, tx=tx, T=T, pars=pars,
                cond=(lam, mu, tau), full=(mc.lam, mc.mu, mc.tau))


def _summ(a, b):
    return dict(pearson=stats.pearsonr(a, b)[0], spearman=stats.spearmanr(a, b)[0],
                mad=np.abs(a - b).mean(), mean_diff=a.mean() - b.mean())


def test_p_alive_vs_conditional_mcmc(cohort):
    x, tx, T, pars = cohort["x"], cohort["tx"], cohort["T"], cohort["pars"]
    lam, mu, tau = cohort["cond"]
    pa = p_alive(*pars, x, tx, T)
    assert np.all((pa >= 0) & (pa <= 1))
    m = _summ(pa, (tau > T[None, :]).mean(0))
    # observed: pearson ~0.999, spearman 0.94-0.998, MAD ~0.009 (pure MC noise of
    # 1000 Gibbs draws), mean diff < 0.001
    assert m["pearson"] > 0.99 and m["spearman"] > 0.90
    assert m["mad"] < 0.02 and abs(m["mean_diff"]) < 0.01
    # Rao-Blackwellised MCMC estimate (mean of the sampler's own P(alive | lam, mu)):
    # lower-variance, so it must sit even closer
    rate = lam + mu
    e = np.exp(-rate * (T - tx)[None, :])
    m_rb = _summ(pa, (e / (e + mu / rate * (1 - e))).mean(0))
    assert m_rb["pearson"] > 0.995 and m_rb["mad"] < 0.012


def test_p_alive_vs_full_mcmc_and_simulated_truth(cohort):
    x, tx, T, pars = cohort["x"], cohort["tx"], cohort["T"], cohort["pars"]
    pa = p_alive(*pars, x, tx, T)
    m = _summ(pa, (cohort["full"][2] > T[None, :]).mean(0))
    assert m["pearson"] > 0.99 and m["mad"] < 0.02 and abs(m["mean_diff"]) < 0.01
    # calibration-in-the-large against the simulator's true alive indicator
    assert abs(pa.mean() - cohort["df"]["alive_at_T"].mean()) < 0.03


@pytest.mark.parametrize("h", HORIZONS)
def test_expected_purchases_exact_vs_mcmc_simulation(cohort, h):
    x, tx, T, pars = cohort["x"], cohort["tx"], cohort["T"], cohort["pars"]
    ex = expected_purchases_exact(*pars, x, tx, T, h)
    for draws, tol in ((cohort["cond"], 0.03), (cohort["full"], 0.05)):
        lam, mu, tau = draws
        sim = spp_predict(lam, mu, tau, T, h, np.random.default_rng(4)).mean(0)
        m = _summ(ex, sim)
        # observed: cohort-mean rel diff <= 0.4% (conditional) / <= 2.5% (full MCMC,
        # whose population posterior differs slightly from the MLE plug-in)
        assert abs(m["mean_diff"]) / sim.mean() < tol
        assert m["pearson"] > 0.99


@pytest.mark.parametrize("h", HORIZONS)
def test_expected_purchases_approximation_gap_is_quantified(cohort, h):
    """The approximation must (i) rank customers like the ground truth, (ii) overstate
    the level by the documented amount, and (iii) have its gap fully explained by the
    die-during-the-window term, i.e. closed by the exact formula."""
    x, tx, T, pars = cohort["x"], cohort["tx"], cohort["T"], cohort["pars"]
    lam, mu, tau = cohort["cond"]
    ea = expected_purchases(*pars, x, tx, T, h)
    ex = expected_purchases_exact(*pars, x, tx, T, h)
    sim = spp_predict(lam, mu, tau, T, h, np.random.default_rng(4)).mean(0)
    # Rao-Blackwellised future mean (expected, not sampled, Poisson count): less noisy
    rb = (lam * np.clip(np.minimum(tau, T + h) - T, 0.0, None)).mean(0)
    assert _summ(ea, sim)["pearson"] > 0.99
    assert _summ(ea, rb)["spearman"] > 0.90
    over = ea.mean() / sim.mean() - 1.0
    # observed overstatement: h=13 8-10%, h=26 16-19%, h=52 30-36%
    lo, hi = {13: (0.04, 0.15), 26: (0.10, 0.25), 52: (0.20, 0.45)}[h]
    assert lo < over < hi
    # the exact formula closes >= 90% of that gap
    assert abs(ex.mean() - sim.mean()) < 0.1 * abs(ea.mean() - sim.mean())
