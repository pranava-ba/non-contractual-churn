"""Export the amortized Pareto/NBD estimator (amortized.py) to ONNX plus a
JSON sidecar for its input/output StandardScalers, and generate golden-file
reference cases for cross-checking a C++ port."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amortized import generate_training_data, fit_amortizer  # noqa: E402


def train_amortizer(seed: int = 0, n_cohorts: int = 4000) -> dict:
    """Train the amortizer exactly as amortized.py's __main__ does, exposed
    as a reusable function for the export pipeline."""
    X, Y = generate_training_data(n_cohorts=n_cohorts, seed=seed)
    return fit_amortizer(X, Y, seed=seed)


def export_scalers(am: dict, path) -> None:
    """Write the input/output StandardScaler parameters as JSON.
    StandardScaler is a pure affine transform (x - mean) / scale, so the
    C++ side applies it directly with no ONNX graph needed for this part."""
    data = {
        "x_mean": am["xs"].mean_.tolist(),
        "x_scale": am["xs"].scale_.tolist(),
        "y_mean": am["ys"].mean_.tolist(),
        "y_scale": am["ys"].scale_.tolist(),
    }
    Path(path).write_text(json.dumps(data, indent=2))
