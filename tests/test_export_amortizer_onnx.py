import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from export_amortizer_onnx import train_amortizer


def test_train_amortizer_returns_expected_keys():
    am = train_amortizer(seed=0, n_cohorts=50)
    assert set(am.keys()) == {"mlp", "xs", "ys"}
    assert am["mlp"].coefs_[0].shape[0] == 11  # 11 input features
    assert am["mlp"].coefs_[-1].shape[1] == 4  # 4 output log-params
