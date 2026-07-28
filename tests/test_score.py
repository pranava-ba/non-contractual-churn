import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from score import crps_samples, randomized_pit, coverage, log_score_smoothed, score_forecast


def test_crps_samples_exact_known_value():
    # If pred is deterministic and equals y, CRPS = 0
    pred = np.array([[2.0, 5.0], [2.0, 5.0]])
    y = np.array([2.0, 5.0])
    crps = crps_samples(pred, y)
    np.testing.assert_allclose(crps, [0.0, 0.0])


def test_log_score_smoothed():
    pred = np.array([[0, 1], [0, 2], [0, 1]])
    y = np.array([0, 1])
    score = log_score_smoothed(pred, y, eps=1e-5)
    assert np.isfinite(score)
    assert score >= 0.0


def test_coverage():
    rng = np.random.default_rng(42)
    # Generate 1000 draws for 500 customers from Normal(0, 1)
    pred = rng.normal(0.0, 1.0, size=(1000, 500))
    # True values sampled from the same distribution
    y = rng.normal(0.0, 1.0, size=500)
    cov = coverage(pred, y, levels=(0.5, 0.95))
    assert cov[0.5] == pytest.approx(0.5, abs=0.08)
    assert cov[0.95] == pytest.approx(0.95, abs=0.05)


def test_score_forecast_battery():
    rng = np.random.default_rng(42)
    pred = rng.poisson(lam=2.0, size=(100, 30))
    y_true = rng.poisson(lam=2.0, size=30)
    
    scores = score_forecast(pred, y_true, rng)
    assert "CRPS" in scores
    assert "log_score" in scores
    assert "cov95" in scores
    assert "pit_ks" in scores
