import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from export_amortizer_onnx import train_amortizer, export_scalers


def test_train_amortizer_returns_expected_keys():
    am = train_amortizer(seed=0, n_cohorts=50)
    assert set(am.keys()) == {"mlp", "xs", "ys"}
    assert am["mlp"].coefs_[0].shape[0] == 11  # 11 input features
    assert am["mlp"].coefs_[-1].shape[1] == 4  # 4 output log-params


def test_export_scalers_writes_expected_json(tmp_path):
    am = train_amortizer(seed=0, n_cohorts=50)
    out_path = tmp_path / "scalers.json"
    export_scalers(am, out_path)

    data = json.loads(out_path.read_text())
    assert set(data.keys()) == {"x_mean", "x_scale", "y_mean", "y_scale"}
    assert len(data["x_mean"]) == 11
    assert len(data["y_mean"]) == 4
    assert data["x_mean"] == am["xs"].mean_.tolist()
    assert data["y_scale"] == am["ys"].scale_.tolist()
