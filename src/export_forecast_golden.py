"""Generate a golden-file fixture for cross-checking the C++ port of the closed-form
Pareto/NBD forecasts (cpp/src/forecast.cpp) against src/forecast_closed_form.py.

Every case records two independent reference values:

  * ``p_alive`` / ``expected_purchases`` -- the Python oracle itself
    (``forecast_closed_form.p_alive`` and ``expected_purchases_exact``; scipy hyp2f1
    on the normal path, adaptive quadrature where scipy's hyp2f1 overflows);
  * ``p_alive_mpmath`` / ``expected_purchases_mpmath`` -- 50-digit mpmath evaluations
    of the DEFINING 1-D integrals (no hypergeometric function anywhere), i.e. the same
    construction as tests/test_forecast_closed_form.py's ``_quadrature_reference``:
        P(alive) = 1 / (1 + int_{t_x}^{T} s (a+T)^(r+x) (b+T)^s
                                 / ((a+tau)^(r+x) (b+tau)^(s+1)) dtau)
        E[Y]     = P(alive) * (r+x)/(a+T) * int_0^h ((b+T)/(b+T+u))^s du

Flags per case:

  * ``is_overflow_case`` -- True iff the Python oracle's hyp2f1 overflowed and it took
    its quadrature fallback (``_log_alive_odds_quad``) for this customer.  Detected by
    instrumenting that function, not by re-implementing the condition.
  * ``cpp_expect_throw`` -- True iff the C++ fast path is EXPECTED to throw
    ``pareto_nbd::ForecastOverflowError`` (its documented limitation: the hypergeometric
    series cannot converge within its term cap when min(alpha,beta)+t is tiny relative
    to max(alpha,beta)+t).  The reference values are still recorded for those cases.

Run:  python src/export_forecast_golden.py   (writes models/forecast_golden.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forecast_closed_form as fcf  # noqa: E402

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
mp.mp.dps = 50

# --------------------------------------------------------------------------- #
# Named cases: (name, (r, alpha, s, beta), (x, t_x, T), [horizons], cpp_expect_throw)
# --------------------------------------------------------------------------- #
NAMED = [
    # normal regime, both hypergeometric branches
    ("alpha<beta typical", (0.7, 5.0, 0.6, 8.0), (3, 20.0, 40.0), [13.0, 52.0], False),
    ("alpha>=beta typical", (0.7, 9.0, 0.6, 4.0), (12, 30.0, 45.0), [1.0, 26.0], False),
    ("MLE-like, zero repeat purchases", (1.44, 5.62, 0.85, 31.8), (0, 0.0, 30.0), [26.0], False),
    ("MLE-like, recent buyer", (1.44, 5.62, 0.85, 31.8), (8, 39.0, 40.0), [13.0, 52.0], False),
    ("MLE-like, heavy recent buyer", (1.44, 5.62, 0.85, 31.8), (200, 51.0, 52.0), [26.0], False),
    ("MLE-like, long-silent buyer", (1.44, 5.62, 0.85, 31.8), (5, 5.0, 50.0), [52.0], False),
    ("s>1, near-dead", (0.3, 2.0, 2.5, 30.0), (5, 5.0, 50.0), [52.0], False),
    ("alpha<<beta, x=0 (z~0.995, ~2k series terms)", (5.0, 0.5, 0.1, 100.0), (0, 0.0, 30.0), [26.0], False),
    ("alpha/beta=1e-4, x=0 (z=1-1e-4, ~3.6e5 series terms)", (0.7, 0.01, 0.6, 100.0), (0, 0.0, 30.0), [26.0], False),
    ("alpha/beta=1e4 (alpha>=beta branch, z=1-1e-4)", (0.7, 100.0, 0.6, 0.01), (0, 0.0, 30.0), [26.0], False),
    # alpha == beta (z = 0, hyp2f1 = 1) with s == 1 exactly (expm1 Taylor branch, a = 0)
    ("alpha==beta, s==1 exactly", (2.0, 10.0, 1.0, 10.0), (3, 20.0, 40.0), [13.0, 52.0], False),
    # s ~= 1: the removable singularity of (b+T)/(s-1) * [1 - ((b+T)/(b+T+h))^(s-1)]
    ("s=1-1e-10 (Taylor branch of expm1(a)/a)", (0.8, 6.0, 1.0 - 1e-10, 12.0), (4, 30.0, 40.0), [26.0], False),
    ("s=1+1e-6 (expm1 branch, near-singular)", (0.8, 6.0, 1.0 + 1e-6, 12.0), (4, 30.0, 40.0), [26.0], False),
    ("s=1+1e-3", (0.8, 6.0, 1.0 + 1e-3, 12.0), (4, 30.0, 40.0), [26.0], False),
    # boundaries
    ("t_x == T (purchase at end of calibration -> p_alive = 1)", (0.7, 5.0, 0.6, 8.0), (8, 40.0, 40.0), [26.0], False),
    ("horizon = 0", (1.44, 5.62, 0.85, 31.8), (3, 20.0, 40.0), [0.0], False),
    ("long horizon h=520", (1.44, 5.62, 0.85, 31.8), (3, 35.0, 40.0), [520.0], False),
    ("heavy buyer silent: p_alive ~ 1e-20", (1.44, 5.62, 0.85, 31.8), (1500, 50.0, 52.0), [26.0], False),
    ("heavy buyer silent long: p_alive underflows to 0", (0.5, 3.0, 0.8, 20.0), (3000, 10.0, 52.0), [26.0], False),
    # Python's overflow region (alpha < beta, very heavy buyer): scipy hyp2f1 overflows
    # and the oracle uses quadrature; the C++ log-space series evaluates these directly.
    ("overflow region: mpmath-pinned 0.9965", (5.0, 0.5, 0.1, 100.0), (3000, 51.9, 52.0), [13.0, 52.0], False),
    ("overflow region: mpmath-pinned 0.6381", (1.44, 0.3, 0.85, 31.8), (2000, 51.8, 52.0), [26.0], False),
    ("overflow region: mpmath-pinned 0.2050", (1.44, 0.3, 0.85, 31.8), (2000, 51.75, 52.0), [26.0], False),
    ("overflow region: p_alive ~ 1e-22", (1.44, 0.3, 0.85, 31.8), (1500, 50.0, 52.0), [26.0], False),
    ("overflow region: MLE-like params", (1.44, 5.62, 0.85, 31.8), (2000, 51.8, 52.0), [26.0], False),
    # C++ fast-path limitation: alpha/beta = 1e-8 with t_x = 0 puts z(t_x) = 1 - 1e-8; the
    # series would need ~4e9 terms, beyond the cap -> ForecastOverflowError.
    ("C++ limitation: alpha/beta=1e-8, x=0 -> ForecastOverflowError", (0.7, 1e-6, 0.6, 100.0), (0, 0.0, 30.0), [26.0], True),
]


def _random_sweep(n: int = 120, seed: int = 2026):
    """Seeded sweep over realistic-to-wide parameter ranges.  alpha, beta in [0.1, 100]
    keeps min/max(alpha, beta) >= 1e-3, comfortably inside the C++ series' convergence
    budget, so none of these are expected to throw."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        params = (10 ** rng.uniform(-1, 0.8), 10 ** rng.uniform(-1, 2),
                  10 ** rng.uniform(-1, 0.6), 10 ** rng.uniform(-1, 2))
        T = float(rng.uniform(5, 100))
        x = int(rng.choice([0, 1, 2, 5, 10, 30, 100, 500, 3000]))
        tx = 0.0 if x == 0 else float(T * rng.uniform() ** 0.3)
        h = float(rng.choice([1.0, 13.0, 26.0, 52.0, 104.0]))
        out.append((f"sweep #{i}", tuple(float(p) for p in params), (x, tx, T), [h], False))
    return out


def _mpmath_reference(r, a, s, b, x, tx, T, h):
    r, a, s, b, x, tx, T, h = map(mp.mpf, (r, a, s, b, x, tx, T, h))
    if tx < T:
        f = lambda tau: ((a + T) / (a + tau)) ** (r + x) * s / (b + tau) * ((b + T) / (b + tau)) ** s
        # the integrand decays from t_x on a scale ~ 1/(decay rate); split there
        scale = 1 / ((r + x) / (a + tx) + s / (b + tx))
        pts = [tx] + [p for p in (tx + scale, tx + 10 * scale, tx + 100 * scale) if p < T] + [T]
        dead, err = mp.quad(f, pts, error=True)
        assert err <= mp.mpf(10) ** -25 * max(dead, mp.mpf(1)), (dead, err)
    else:
        dead = mp.mpf(0)
    pa = 1 / (1 + dead)
    if h > 0:
        g = lambda u: ((b + T) / (b + T + u)) ** s
        active, err = mp.quad(g, [0, h], error=True)
        assert err <= mp.mpf(10) ** -25 * active, (active, err)
    else:
        active = mp.mpf(0)
    return float(pa), float(pa * (r + x) / (a + T) * active)


def _python_reference(params, cust, h):
    """Oracle values, plus whether the oracle hit its hyp2f1-overflow quadrature path."""
    calls = []
    original = fcf._log_alive_odds_quad

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    fcf._log_alive_odds_quad = spy
    try:
        pa = float(fcf.p_alive(*params, *cust))
        ep = float(fcf.expected_purchases_exact(*params, *cust, h))
    finally:
        fcf._log_alive_odds_quad = original
    return pa, ep, len(calls) > 0


def build_cases():
    cases = []
    for name, params, cust, horizons, expect_throw in NAMED + _random_sweep():
        r, alpha, s, beta = params
        x, tx, T = cust
        for h in horizons:
            pa, ep, overflow = _python_reference(params, cust, h)
            pa_mp, ep_mp = _mpmath_reference(r, alpha, s, beta, x, tx, T, h)
            cases.append({
                "name": name,
                "r": r, "alpha": alpha, "s": s, "beta": beta,
                "x": float(x), "t_x": float(tx), "T": float(T), "horizon": float(h),
                "p_alive": pa, "expected_purchases": ep,
                "p_alive_mpmath": pa_mp, "expected_purchases_mpmath": ep_mp,
                "is_overflow_case": overflow,
                "cpp_expect_throw": expect_throw,
            })
    return cases


if __name__ == "__main__":
    MODELS_DIR.mkdir(exist_ok=True)
    cases = build_cases()
    named_overflow = [c["name"] for c in cases if c["is_overflow_case"]]
    doc = {
        "description": "Golden fixture for cpp/src/forecast.cpp: Python oracle "
                       "(src/forecast_closed_form.py p_alive / expected_purchases_exact) "
                       "plus independent 50-digit mpmath integrals, per case.",
        "generator": "src/export_forecast_golden.py",
        "cases": cases,
    }
    out_path = MODELS_DIR / "forecast_golden.json"
    out_path.write_text(json.dumps(doc, indent=2))
    worst = max(abs(c["p_alive"] - c["p_alive_mpmath"]) / c["p_alive_mpmath"]
                for c in cases if c["p_alive_mpmath"] > 1e-300)
    print(f"Wrote {out_path}: {len(cases)} cases, {len(named_overflow)} in the Python "
          f"hyp2f1-overflow (quadrature) region, "
          f"{sum(c['cpp_expect_throw'] for c in cases)} expected C++ throws; "
          f"oracle vs mpmath worst p_alive rel err {worst:.2e}")
