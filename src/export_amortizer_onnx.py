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
        for node in graph.node:
            if node.op_type == "Reshape" and output_name in node.output:
                shape_input_name = node.input[1]
                for init in graph.initializer:
                    if init.name == shape_input_name:
                        new_shape = np.array([-1, n_outputs], dtype=np.int64)
                        init.CopyFrom(numpy_helper.from_array(new_shape, name=init.name))
        graph.output[0].type.tensor_type.shape.dim[1].dim_value = n_outputs

    Path(path).write_bytes(onnx_model.SerializeToString())
