import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulate import DatasetParams, simulate_dataset
from simulate_misspec import simulate_dataset_ggg, simulate_dataset_mixture


def test_simulate_dataset_columns_and_shape():
    params = DatasetParams(E_lambda=0.15, CV_lambda=1.2, E_mu=0.08, CV_mu=1.0, N=200, T=52.0)
    rng = np.random.default_rng(42)
    df = simulate_dataset(params, rng=rng)
    
    assert len(df) == 200
    expected_cols = {"cust", "x", "t_x", "T_cal", "x_star_26", "x_star_13", "x_star_52"}
    assert expected_cols.issubset(df.columns)
    assert (df["x"] >= 0).all()
    assert (df["t_x"] <= df["T_cal"]).all()


def test_simulate_dataset_ggg_columns():
    params = DatasetParams(E_lambda=0.15, CV_lambda=1.2, E_mu=0.08, CV_mu=1.0, N=150, T=52.0)
    rng = np.random.default_rng(123)
    df = simulate_dataset_ggg(params, k=2.0, rng=rng)
    
    assert len(df) == 150
    assert "litt" in df.columns
    assert (df["x"] >= 0).all()


def test_simulate_dataset_mixture():
    rng = np.random.default_rng(99)
    df = simulate_dataset_mixture(N=100, T=52.0, E_lambda=0.15, ratio=5.0, E_mu=0.08, CV_mu=1.0, p_heavy=0.2, rng=rng)
    
    assert len(df) == 100
    assert (df["x"] >= 0).all()
