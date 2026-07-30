import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulate import DatasetParams, simulate_dataset
from estimate import fit_mcmc, fit_mle
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
