"""Command-line wrapper around ``estimate.fit_mcmc`` for the C++ worker (spec phase 6).

The worker writes the ingested cohort (columns x, t_x, T_cal, in weeks) to a CSV, runs this
script, and reads posterior-mean Pareto/NBD parameters back from ``--out``. ``--out`` is
written LAST, so its presence with exit code 0 means everything else succeeded.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import fit_mcmc  # noqa: E402

REQUIRED = ("x", "t_x", "T_cal")


def run(cohort_csv, out_json, draws_npz, n_draws=6000, burn_in=2000, thin=8, seed=0) -> dict:
    df = pd.read_csv(cohort_csv)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"cohort CSV is missing column(s): {', '.join(missing)}")
    if len(df) == 0:
        raise ValueError("cohort CSV has no rows")
    t0 = time.time()
    res = fit_mcmc(df, n_draws=n_draws, burn_in=burn_in, thin=thin, seed=seed)
    m = res.pop_draws.mean(axis=0)
    np.savez_compressed(draws_npz, pop_draws=res.pop_draws,
                        lam=res.lam.astype(np.float32), mu=res.mu.astype(np.float32))
    fit = {"r": float(m[0]), "alpha": float(m[1]), "s": float(m[2]), "beta": float(m[3]),
           "n_keep": int(res.pop_draws.shape[0]), "n_customers": int(len(df)),
           "elapsed_s": round(time.time() - t0, 3)}
    Path(out_json).write_text(json.dumps(fit))
    return fit


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--draws", required=True)
    p.add_argument("--n-draws", type=int, default=6000)
    p.add_argument("--burn-in", type=int, default=2000)
    p.add_argument("--thin", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args(argv)
    try:
        run(a.cohort, a.out, a.draws, a.n_draws, a.burn_in, a.thin, a.seed)
    except Exception as e:  # noqa: BLE001 - CLI boundary: report and signal via exit code
        print(f"mcmc_cli: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
