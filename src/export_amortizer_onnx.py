"""Export the amortized Pareto/NBD estimator (amortized.py) to ONNX plus a
JSON sidecar for its input/output StandardScalers, and generate golden-file
reference cases for cross-checking a C++ port."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amortized import generate_training_data, fit_amortizer  # noqa: E402


def train_amortizer(seed: int = 0, n_cohorts: int = 4000) -> dict:
    """Train the amortizer exactly as amortized.py's __main__ does, exposed
    as a reusable function for the export pipeline."""
    X, Y = generate_training_data(n_cohorts=n_cohorts, seed=seed)
    return fit_amortizer(X, Y, seed=seed)
