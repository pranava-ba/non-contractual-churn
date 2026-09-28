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
    """Generate a synthetic cohort (all customers have repeat transactions,
    so none are filtered out by fit_gamma_gamma's internal x>0 & m_obs>0
    mask) via a Gamma-Gamma-*like* data-generating process, fit it with the
    real Python fit_gamma_gamma, and record the fitted (p, q, v) as a fixed
    reference point for cross-language MLE parity checking.

    Note this is NOT a parameter-recovery test: m_obs here is drawn as a
    single Gamma(true_p, nu/true_p) sample per customer, whereas the
    Gamma-Gamma model assumes m_obs is the *average* of x repeat
    transactions (Gamma(p*x, v/(p*x))). That mismatch means the data
    process is misspecified relative to the model, so the MLE fit (p, q, v)
    does not recover true_p/true_q/true_v — the fitted values (p~0.97,
    q~2.41, v~10.4) land far from the (3.0, 4.0, 20.0) generating constants
    below. That's fine for this fixture's actual purpose: a fixed,
    reproducible, well-identified optimum for checking that a C++ port of
    fit_gamma_gamma's Nelder-Mead MLE converges to the same point as SciPy's
    — not for checking that either implementation recovers ground-truth
    parameters."""
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
