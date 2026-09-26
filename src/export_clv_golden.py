"""Generate a golden-file fixture for cross-checking a C++ port of
fit_gamma_gamma (src/clv.py) against the real Python implementation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clv import fit_gamma_gamma  # noqa: E402


def generate_fit_gamma_gamma_case(seed: int = 123, n: int = 500) -> dict:
    """A well-conditioned synthetic Gamma-Gamma cohort (all customers have
    repeat transactions, so none are filtered out by fit_gamma_gamma's
    internal x>0 & m_obs>0 mask) with known-plausible true parameters, so
    the MLE lands at a well-identified (non-degenerate) point."""
    rng = np.random.default_rng(seed)
    true_p, true_q, true_v = 3.0, 4.0, 20.0
    x = rng.integers(1, 15, size=n).astype(float)
    nu = true_v / rng.gamma(true_q, 1.0, size=n)
    m_obs = rng.gamma(true_p, nu / true_p)

    fit = fit_gamma_gamma(x, m_obs)
    return {
        "x": x.tolist(),
        "m_obs": m_obs.tolist(),
        "p": fit["p"],
        "q": fit["q"],
        "v": fit["v"],
    }


if __name__ == "__main__":
    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    case = generate_fit_gamma_gamma_case()
    out_path = models_dir / "clv_conformal_golden.json"
    out_path.write_text(json.dumps(case, indent=2))
    print(f"Wrote {out_path} (p={case['p']:.6f}, q={case['q']:.6f}, v={case['v']:.6f})")
