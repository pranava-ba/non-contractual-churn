import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulate import DatasetParams, simulate_dataset
from estimate import _pnbd_loglik, fit_mcmc, fit_mle
from estimate_ggg import fit_ggg


def test_mle_estimation_runs_and_bounds():
    params = DatasetParams(E_lambda=0.2, CV_lambda=1.2, E_mu=0.1, CV_mu=1.0, N=300, T=52.0)
    rng = np.random.default_rng(10)
    df = simulate_dataset(params, rng=rng)
    
    mle = fit_mle(df, seed=1)
    assert "r" in mle and "alpha" in mle and "s" in mle and "beta" in mle
    assert mle["r"] > 0 and mle["alpha"] > 0
    assert mle["E_lambda"] > 0


def test_mcmc_estimation_runs():
    params = DatasetParams(E_lambda=0.2, CV_lambda=1.2, E_mu=0.1, CV_mu=1.0, N=100, T=52.0)
    rng = np.random.default_rng(20)
    df = simulate_dataset(params, rng=rng)
    
    mc = fit_mcmc(df, n_draws=200, burn_in=50, thin=2, seed=2)
    assert mc.pop_draws.shape == (75, 4)
    assert mc.lam.shape == (75, 100)
    summary = mc.pop_summary()
    assert summary["E_lambda"] > 0


def test_ggg_estimation_runs():
    from simulate_misspec import simulate_dataset_ggg
    params = DatasetParams(E_lambda=0.2, CV_lambda=1.2, E_mu=0.1, CV_mu=1.0, N=80, T=52.0)
    rng = np.random.default_rng(30)
    df = simulate_dataset_ggg(params, k=1.5, rng=rng)

    ggg = fit_ggg(df, n_draws=100, burn_in=30, thin=2, seed=3, n_quad=10)
    assert len(ggg.k_draws) == 35
    assert ggg.k_draws.mean() > 0


def test_parameter_recovery():
    """MLE and MCMC recover the true mean purchase rate E(lambda) on a large cohort.
    A loose tolerance still catches gross failures such as the optimiser-overflow bug
    that returned E(lambda) off by an order of magnitude."""
    truth = DatasetParams(E_lambda=0.15, CV_lambda=1.2, E_mu=0.08, CV_mu=1.0, N=2000, T=52.0)
    rng = np.random.default_rng(123)
    df = simulate_dataset(truth, rng=rng)

    mle = fit_mle(df, seed=1)
    mc = fit_mcmc(df, n_draws=1500, burn_in=500, thin=5, seed=2)
    for est in (mle["E_lambda"], mc.pop_summary()["E_lambda"]):
        assert 0.5 * truth.E_lambda < est < 1.5 * truth.E_lambda
    # the two estimators agree with each other, the paper's central finding
    assert abs(mle["E_lambda"] - mc.pop_summary()["E_lambda"]) < 0.25 * truth.E_lambda


# ------------------------- heavy-buyer underflow regression ------------------------ #
# Before the fix, _pnbd_loglik computed term1 = 1/(alpha+T)^(r+x)/(beta+T)^s and the
# hyp2f1-based A0 directly (not in log space): for a heavy buyer (large x) both
# underflow to exactly 0.0, and `np.log(np.maximum(inner, 1e-300))` silently replaced
# the true (and here strongly *positive*) log-likelihood contribution with a fixed
# clamp-floor value, independent of the actual parameters -- corrupting `fit_mle`'s
# optimisation for any cohort containing such a customer.

def test_pnbd_loglik_heavy_buyer_matches_mpmath_reference():
    """x=1500 at (r, alpha, s, beta) = (1.44, 5.62, 0.85, 31.8): before the fix this
    returned a clamp-floor-derived 8784.2 instead of the true log-likelihood. The
    reference is derived from the independent mpmath 50-digit p_alive value for these
    exact params (see tests/test_forecast_closed_form.py::MPMATH_REFERENCE) via the
    identity log L = p1 + log(term1) - log(p_alive)."""
    from scipy.special import gammaln

    r, alpha, s, beta = 1.44, 5.62, 0.85, 31.8
    x, t_x, T = np.array([1500.0]), np.array([50.0]), np.array([52.0])
    params = np.log([r, alpha, s, beta])

    ll = _pnbd_loglik(params, x, t_x, T)
    assert np.isfinite(ll)

    p_alive_mpmath = 2.3456971872730111469e-20
    p1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha) + s * np.log(beta)
    log_term1 = -(r + x) * np.log(alpha + T) - s * np.log(beta + T)
    ll_ref = (p1 + log_term1 - np.log(p_alive_mpmath)).item()

    assert float(ll) == pytest.approx(ll_ref, rel=1e-9)
    # the pre-fix clamp-floor output for these exact params was 8784.2040...;
    # confirm we're no longer producing that wrong value
    assert float(ll) != pytest.approx(8784.2040, abs=1.0)


def test_pnbd_loglik_reviewer_repro_case_x400_alpha5_beta8():
    """Reviewer's direct repro: x=400, alpha=5, beta=8 drove both term1 and the
    hyp2f1-based A0 to exactly 0.0 in the pre-fix direct (non-log) computation, so the
    1e-300 clamp fired and the returned log-likelihood (+1313.41) was independent of
    the true parameters. Cross-validated here against the (separately tested,
    heavy-buyer-safe) closed-form p_alive via the shared likelihood identity
    log L = p1 + log(term1) - log(p_alive)."""
    from scipy.special import gammaln

    from forecast_closed_form import p_alive

    r, alpha, s, beta = 1.0, 5.0, 1.0, 8.0
    x, t_x, T = np.array([400.0]), np.array([50.0]), np.array([52.0])
    params = np.log([r, alpha, s, beta])

    ll = _pnbd_loglik(params, x, t_x, T)
    assert np.isfinite(ll)

    pa = p_alive(r, alpha, s, beta, x, t_x, T)
    p1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha) + s * np.log(beta)
    log_term1 = -(r + x) * np.log(alpha + T) - s * np.log(beta + T)
    ll_ref = (p1 + log_term1 - np.log(pa)).item()

    assert float(ll) == pytest.approx(ll_ref, rel=1e-9)
    # the pre-fix clamp-floor output for these exact params was +1313.41
    assert float(ll) != pytest.approx(1313.4140495391416, abs=1.0)


def test_pnbd_loglik_finite_and_varies_across_heavy_buyers():
    """Across the x range that used to underflow (x>=~160 at these realistic,
    grocery-cohort-fitted parameters), the log-likelihood must stay finite and keep
    varying smoothly with x -- not collapse to a shared clamp-floor value."""
    r, alpha, s, beta = (0.8059470521600479, 6.0845154066843135,
                         0.38478978618776155, 5.917397141875596)
    t_x, T = 68.0, 69.28
    lls = []
    for x_val in (80, 160, 200, 400, 800, 1500, 3000):
        x = np.array([float(x_val)])
        params = np.log([r, alpha, s, beta])
        ll = _pnbd_loglik(params, x, np.array([t_x]), np.array([T]))
        assert np.isfinite(ll)
        lls.append(float(ll))
    assert all(b > a for a, b in zip(lls, lls[1:]))


def test_fit_mle_cohort_with_heavy_buyer_runs_and_fits_sensibly():
    """Integration regression: a cohort containing a heavy-buyer customer must not
    silently corrupt fit_mle. Pre-fix, that customer's per-customer log-likelihood
    could underflow to a parameter-independent clamp floor at the candidate parameter
    vectors the optimiser visits, either tripping fit_mle's own coarse overflow guard
    (``-10 < res.fun``) and discarding an otherwise-good start, or -- if the spurious
    contribution wasn't large enough to trip that guard -- silently biasing the fit."""
    truth = DatasetParams(E_lambda=0.15, CV_lambda=1.2, E_mu=0.08, CV_mu=1.0, N=500, T=52.0)
    rng = np.random.default_rng(42)
    df = simulate_dataset(truth, rng=rng)
    heavy = df.iloc[[0]].copy()
    heavy["x"] = 300.0
    heavy["t_x"] = 50.0
    heavy["T_cal"] = 52.0
    df = pd.concat([df, heavy], ignore_index=True)

    mle = fit_mle(df, seed=1)
    assert np.isfinite(mle["loglik"])
    assert mle["r"] > 0 and mle["alpha"] > 0 and mle["s"] > 0 and mle["beta"] > 0
    # the 500 ordinary customers still dominate and drive a sensible recovered rate
    assert 0.5 * truth.E_lambda < mle["E_lambda"] < 2.0 * truth.E_lambda
