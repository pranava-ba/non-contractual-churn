import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulate import DatasetParams, simulate_dataset
import mcmc_cli


def _cohort_csv(tmp_path, n=120):
    params = DatasetParams(E_lambda=0.2, CV_lambda=1.2, E_mu=0.1, CV_mu=1.0, N=n, T=52.0)
    df = simulate_dataset(params, rng=np.random.default_rng(3))
    path = tmp_path / "cohort.csv"
    df[["x", "t_x", "T_cal"]].to_csv(path, index=False)
    return path, n


def test_cli_writes_posterior_means_and_draws(tmp_path):
    cohort, n = _cohort_csv(tmp_path)
    out, draws = tmp_path / "fit.json", tmp_path / "draws.npz"
    code = mcmc_cli.main(["--cohort", str(cohort), "--out", str(out), "--draws", str(draws),
                          "--n-draws", "80", "--burn-in", "20", "--thin", "4"])
    assert code == 0
    fit = json.loads(out.read_text())
    for k in ("r", "alpha", "s", "beta"):
        assert np.isfinite(fit[k]) and fit[k] > 0
    assert fit["n_customers"] == n and fit["n_keep"] == 15
    z = np.load(draws)
    assert z["pop_draws"].shape == (15, 4)
    assert z["lam"].shape == (15, n) and z["mu"].shape == (15, n)


def test_cli_rejects_missing_column_and_writes_no_json(tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"x": [1], "t_x": [1.0]}).to_csv(bad, index=False)
    out = tmp_path / "fit.json"
    code = mcmc_cli.main(["--cohort", str(bad), "--out", str(out), "--draws", str(tmp_path / "d.npz")])
    assert code == 2
    assert not out.exists()


def test_cli_rejects_empty_cohort(tmp_path):
    empty = tmp_path / "empty.csv"
    pd.DataFrame({"x": [], "t_x": [], "T_cal": []}).to_csv(empty, index=False)
    assert mcmc_cli.main(["--cohort", str(empty), "--out", str(tmp_path / "o.json"),
                          "--draws", str(tmp_path / "d.npz")]) == 2
