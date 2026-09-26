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


import numpy as np
from onnx import numpy_helper
from skl2onnx import to_onnx
from skl2onnx.common.data_types import FloatTensorType


def export_mlp_onnx(am: dict, path) -> None:
    """Export only the MLPRegressor to ONNX. Scaling is handled separately
    (export_scalers) since StandardScaler is trivial affine math that does
    not need an ONNX graph."""
    n_features = am["xs"].mean_.shape[0]
    n_outputs = am["mlp"].n_outputs_
    onnx_model = to_onnx(
        am["mlp"],
        initial_types=[("input", FloatTensorType([None, n_features]))],
    )

    # Work around a skl2onnx converter limitation: convert_sklearn_mlp_regressor
    # (skl2onnx/operator_converters/multilayer_perceptron.py) unconditionally
    # reshapes the MLP's output to (-1, 1), which is only correct for
    # single-output regressors. For our 4-output MLP this yields a
    # [batch * 4, 1] tensor instead of [batch, 4]. The underlying values are
    # already correct and in row-major (batch, n_outputs) order, so we only
    # need to patch the final Reshape node's target shape.
    if n_outputs > 1:
        graph = onnx_model.graph
        output_name = graph.output[0].name
        patched = False
        for node in graph.node:
            if node.op_type == "Reshape" and output_name in node.output:
                shape_input_name = node.input[1]
                for init in graph.initializer:
                    if init.name == shape_input_name:
                        new_shape = np.array([-1, n_outputs], dtype=np.int64)
                        init.CopyFrom(numpy_helper.from_array(new_shape, name=init.name))
                        patched = True
        if not patched:
            # The workaround above assumes the specific graph shape produced
            # by skl2onnx's convert_sklearn_mlp_regressor as of skl2onnx
            # 1.20.0 (a single Reshape node feeding the graph output, with a
            # [-1, 1] int64 shape initializer as its second input). pyproject
            # pins skl2onnx>=1.16.0 with no upper bound, so a newer/older
            # version could change this graph shape (e.g. fix the bug
            # natively, or restructure the Reshape). Silently leaving the
            # output as [batch * n_outputs, 1] would produce an
            # internally-consistent-looking but WRONG-shaped ONNX file that
            # onnx.checker and onnxruntime both load without error — fail
            # loudly instead so this doesn't ship as silent data corruption
            # for the C++ consumer.
            raise RuntimeError(
                "export_mlp_onnx: could not find the expected Reshape node/"
                "shape-initializer pattern to patch the multi-output MLP's "
                "output shape from skl2onnx's export. This workaround "
                "assumes the graph structure produced by skl2onnx==1.20.0's "
                "convert_sklearn_mlp_regressor; if skl2onnx was "
                "upgraded/downgraded, its output-reshape behavior may have "
                "changed and this function needs to be revisited."
            )
        graph.output[0].type.tensor_type.shape.dim[1].dim_value = n_outputs

    Path(path).write_bytes(onnx_model.SerializeToString())


import numpy as np

from simulate import DatasetParams, simulate_dataset  # noqa: E402
from amortized import cohort_features, amortized_params  # noqa: E402

_GOLDEN_PARAMS = [
    DatasetParams(0.15, 1.3, 0.08, 1.2, N=1200, T=52.0),
    DatasetParams(0.05, 0.8, 0.03, 1.8, N=600, T=26.0),
    DatasetParams(0.25, 2.0, 0.15, 0.6, N=900, T=39.0),
]


def generate_golden_cases(am: dict, path, seed: int = 0) -> None:
    """Simulate a handful of fixed cohorts, run them through the real
    amortized_params() pipeline, and record (features -> params) pairs that
    a C++ port must reproduce."""
    rng = np.random.default_rng(seed)
    cases = []
    for params in _GOLDEN_PARAMS:
        df = simulate_dataset(params, rng=rng)
        features = cohort_features(df)
        r, alpha, s, beta, _, _ = amortized_params(am, df)
        cases.append({
            "features": features.tolist(),
            "r": r, "alpha": alpha, "s": s, "beta": beta,
        })
    Path(path).write_text(json.dumps(cases, indent=2))


if __name__ == "__main__":
    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(exist_ok=True)

    print("Training amortizer (seed=0, 4000 cohorts)...", flush=True)
    am = train_amortizer(seed=0)

    export_scalers(am, models_dir / "amortizer_scalers.json")
    export_mlp_onnx(am, models_dir / "amortizer_mlp.onnx")
    generate_golden_cases(am, models_dir / "amortizer_golden.json", seed=1)
    print(f"Wrote artifacts to {models_dir}")
