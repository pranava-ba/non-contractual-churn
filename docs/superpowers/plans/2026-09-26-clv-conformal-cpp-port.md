# Gamma-Gamma CLV + Conformal Calibration C++ Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the product-relevant parts of the Gamma-Gamma probabilistic CLV
model ([src/clv.py](../../../src/clv.py)) and conformal (distributional)
calibration ([src/conformal.py](../../../src/conformal.py)) to the existing
C++ inference core, cross-checked against the real Python implementations.

**Architecture:** Builds directly on the `cpp/` CMake+vcpkg project from
Phase 1 (`amortized_inference` library, `unit_tests` Catch2 binary) — no new
scaffolding needed, only new source/test files added to the existing
targets. Unlike Phase 1, there is no ML model to export to ONNX here: every
function ported in this plan is either a closed-form formula (cross-checked
bit-for-bit against Python) or a numerical optimization / Monte Carlo
routine (cross-checked with a looser, appropriately-chosen tolerance, since
neither a from-scratch optimizer nor a random number stream is expected to
match another language's implementation exactly). A single small Python
script generates one committed golden-file fixture for the one case too
large to hardcode in a C++ test.

**Tech Stack:** C++20 (existing `cpp/` project — Catch2, nlohmann/json),
Python (existing `clv.py`/`conformal.py`/`score.py`, unmodified, used only
to generate golden-file reference values).

**Spec:** [docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md](../specs/2026-09-26-clv-forecasting-saas-design.md)
— this plan implements Phase 2 of that spec's §9 phased build order ("Port
Gamma-Gamma CLV + conformal calibration to C++, same golden-file
validation"). It depends on Phase 1's `cpp/` project already existing
(commits on the `worktree-amortized-onnx-cpp-inference` branch — this plan
continues on that same branch/worktree rather than starting a new one,
since it builds directly on Phase 1's C++ code, not a stable released
artifact of it).

## Global Constraints

- C++20, reusing the existing `cpp/CMakeLists.txt` (Release-by-default,
  vcpkg manifest already pins `catch2`, `nlohmann-json`, `onnxruntime` —
  this plan needs none of `onnxruntime` but the existing link is harmless
  to leave as-is; do not remove it).
- New namespace usage: everything added in this plan lives in the existing
  `pareto_nbd` namespace, in new files following the established
  `cpp/include/pareto_nbd/<name>.hpp` + `cpp/src/<name>.cpp` +
  `cpp/tests/test_<name>.cpp` layout.
- **Two different tolerance regimes, by function kind — do not use one
  blanket tolerance for everything:**
  - **Pure closed-form formulas** (`posterior_mean_nu`, `predict_clv_distribution`,
    `randomized_pit`, `apply_conformal_warp`): these involve no optimizer
    and no RNG, so a correct C++ port should match Python's `double`
    arithmetic almost exactly. Tolerance: relative **1e-9**.
  - **`fit_gamma_gamma`** (Nelder-Mead MLE): a from-scratch C++ Nelder-Mead
    implementation is not expected to walk the identical convergence path
    as SciPy's, even implementing the same algorithm with the same
    coefficients and initial simplex — different tie-breaking in
    floating-point comparisons can send it to a slightly different (but
    similarly optimal) point, especially on a somewhat flat likelihood
    surface. Tolerance: relative **5%** (0.05) on each of p/q/v. If the
    implementer's actual observed error is far outside this (e.g. an order
    of magnitude), that is a real bug to investigate, not a tolerance to
    loosen further — see Task 4's escalation guidance.
  - **`sample_posterior_nu`** (Monte Carlo): cannot be golden-file matched
    sample-by-sample (numpy's and C++'s random number streams differ by
    construction). Cross-checked instead by confirming the *empirical
    mean* over a large number of draws (>= 100,000) converges to the
    *analytical* posterior mean from `posterior_mean_nu` (Task 3) within
    relative **5%** — a statistical convergence check, not an exact-match
    golden-file test.
- The one golden-file fixture needed (the N=500 `fit_gamma_gamma` case,
  too large to hardcode) is committed at
  `models/clv_conformal_golden.json`, generated with a fixed seed
  (`seed=123`) by a new Python script — same pattern as Phase 1's
  `models/amortizer_*` artifacts.
- Toolchain: same as Phase 1 — MSVC/CMake/Ninja only on PATH inside a
  Developer environment; use the PowerShell tool for build commands (the
  Bash tool's worktree-isolation guard has refused this exact kind of
  compound `cmd /c '...vcvars64.bat...'` invocation before). Do not delete
  `cpp/build/` — its cache holds the local, uncommitted `VCPKG_INSTALLED_DIR`
  fix for this machine's space-in-username path issue (see Phase 1's
  ledger/plan for detail); reconfiguring against the existing build dir
  when CMakeLists.txt changes is fine and expected.

---

### Task 1: Golden-file generator for `fit_gamma_gamma`

**Files:**
- Create: `src/export_clv_golden.py`
- Create (generated, then committed): `models/clv_conformal_golden.json`

**Interfaces:**
- Consumes: `fit_gamma_gamma` from [src/clv.py](../../../src/clv.py)
  (existing, unmodified).
- Produces: `models/clv_conformal_golden.json` with keys `{"x": [500
  floats], "m_obs": [500 floats], "p": float, "q": float, "v": float}` —
  consumed by Task 4 (fit_gamma_gamma cross-check) and Task 5
  (sample_posterior_nu statistical check).

- [ ] **Step 1: Write the script**

```python
# src/export_clv_golden.py
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
```

- [ ] **Step 2: Run it**

Run: `python src/export_clv_golden.py`
Expected: prints `Wrote .../models/clv_conformal_golden.json (p=0.971999,
q=2.414917, v=10.438763)` (values should match — this is a deterministic
seed=123 run).

- [ ] **Step 3: Verify**

Run: `python -c "import json; d = json.load(open('models/clv_conformal_golden.json')); print(len(d['x']), len(d['m_obs']), d['p'], d['q'], d['v'])"`
Expected: `500 500 0.9719990896408482 2.414916971476059 10.43876307368964`

- [ ] **Step 4: Commit**

```bash
git add src/export_clv_golden.py models/clv_conformal_golden.json
git commit -m "feat: generate golden-file fixture for fit_gamma_gamma C++ cross-check"
```

---

### Task 2: `nelder_mead` — generic simplex optimizer

**Files:**
- Create: `cpp/include/pareto_nbd/nelder_mead.hpp`
- Create: `cpp/src/nelder_mead.cpp`
- Create: `cpp/tests/test_nelder_mead.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `pareto_nbd::nelder_mead(objective, x0) -> NelderMeadResult{x,
  fval, iterations}`, where `objective` is a
  `std::function<double(const std::vector<double>&)>` — a generic,
  reusable minimizer with no knowledge of Gamma-Gamma. Consumed by Task 4's
  `fit_gamma_gamma`.

- [ ] **Step 1: Write the failing test and interface**

```cpp
// cpp/include/pareto_nbd/nelder_mead.hpp
#pragma once
#include <functional>
#include <vector>

namespace pareto_nbd {

struct NelderMeadResult {
    std::vector<double> x;
    double fval;
    int iterations;
};

// Minimizes `objective` starting from `x0` using the Nelder-Mead simplex
// method (Nelder & Mead 1965): standard reflection/expansion/contraction/
// shrink coefficients (1, 2, 0.5, 0.5), and the same initial-simplex
// construction and default tolerances as
// scipy.optimize.minimize(method="Nelder-Mead") — a 5% step per dimension
// (or 0.00025 if that coordinate is exactly 0), xatol=1e-4, fatol=1e-4,
// maxiter=200*n. Not expected to walk an identical convergence path to
// SciPy's implementation, only to converge near the same optimum.
NelderMeadResult nelder_mead(
    const std::function<double(const std::vector<double>&)>& objective,
    const std::vector<double>& x0);

}  // namespace pareto_nbd
```

```cpp
// cpp/tests/test_nelder_mead.cpp
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <vector>
#include "pareto_nbd/nelder_mead.hpp"

TEST_CASE("nelder_mead finds the minimum of a simple quadratic", "[nelder_mead]") {
    // f(x, y) = (x - 3)^2 + (y + 2)^2 + 5, minimum at (3, -2), fval 5.
    auto objective = [](const std::vector<double>& v) {
        double dx = v[0] - 3.0;
        double dy = v[1] + 2.0;
        return dx * dx + dy * dy + 5.0;
    };
    auto result = pareto_nbd::nelder_mead(objective, {0.0, 0.0});

    REQUIRE(result.x[0] == Catch::Approx(3.0).margin(1e-3));
    REQUIRE(result.x[1] == Catch::Approx(-2.0).margin(1e-3));
    REQUIRE(result.fval == Catch::Approx(5.0).margin(1e-3));
}
```

Modify `cpp/CMakeLists.txt`: add `src/nelder_mead.cpp` to
`amortized_inference`'s sources, and `tests/test_nelder_mead.cpp` to
`unit_tests`'s sources.

- [ ] **Step 2: Build to verify it fails**

Run (from `cpp/`, via vcvars64.bat as in Phase 1): `cmake --preset default && cmake --build build`
Expected: FAIL — `CMake Error: Cannot find source file: src/nelder_mead.cpp`

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/src/nelder_mead.cpp
#include "pareto_nbd/nelder_mead.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>

namespace pareto_nbd {
namespace {

constexpr double kAlpha = 1.0;  // reflection
constexpr double kGamma = 2.0;  // expansion
constexpr double kRho = 0.5;    // contraction
constexpr double kSigma = 0.5;  // shrink

std::vector<double> add_scaled(const std::vector<double>& a, const std::vector<double>& b,
                                double scale) {
    std::vector<double> out(a.size());
    for (size_t i = 0; i < a.size(); ++i) out[i] = a[i] + scale * b[i];
    return out;
}

std::vector<double> subtract(const std::vector<double>& a, const std::vector<double>& b) {
    std::vector<double> out(a.size());
    for (size_t i = 0; i < a.size(); ++i) out[i] = a[i] - b[i];
    return out;
}

}  // namespace

NelderMeadResult nelder_mead(
    const std::function<double(const std::vector<double>&)>& objective,
    const std::vector<double>& x0) {
    const size_t n = x0.size();
    const double xatol = 1e-4;
    const double fatol = 1e-4;
    const int maxiter = 200 * static_cast<int>(n);

    std::vector<std::vector<double>> simplex(n + 1, x0);
    for (size_t i = 0; i < n; ++i) {
        double step = (x0[i] != 0.0) ? 0.05 * x0[i] : 0.00025;
        simplex[i + 1][i] += step;
    }

    std::vector<double> fvals(n + 1);
    for (size_t i = 0; i <= n; ++i) fvals[i] = objective(simplex[i]);

    auto sort_simplex = [&]() {
        std::vector<size_t> order(n + 1);
        std::iota(order.begin(), order.end(), 0);
        std::sort(order.begin(), order.end(), [&](size_t a, size_t b) { return fvals[a] < fvals[b]; });
        std::vector<std::vector<double>> new_simplex(n + 1);
        std::vector<double> new_fvals(n + 1);
        for (size_t i = 0; i <= n; ++i) {
            new_simplex[i] = simplex[order[i]];
            new_fvals[i] = fvals[order[i]];
        }
        simplex = new_simplex;
        fvals = new_fvals;
    };

    sort_simplex();

    int iter = 0;
    while (iter < maxiter) {
        double x_spread = 0.0;
        for (size_t i = 1; i <= n; ++i) {
            double d = 0.0;
            for (size_t j = 0; j < n; ++j) d = std::max(d, std::abs(simplex[i][j] - simplex[0][j]));
            x_spread = std::max(x_spread, d);
        }
        double f_spread = 0.0;
        for (size_t i = 1; i <= n; ++i) f_spread = std::max(f_spread, std::abs(fvals[i] - fvals[0]));
        if (x_spread <= xatol && f_spread <= fatol) break;

        std::vector<double> centroid(n, 0.0);
        for (size_t i = 0; i < n; ++i)
            for (size_t j = 0; j < n; ++j) centroid[j] += simplex[i][j];
        for (size_t j = 0; j < n; ++j) centroid[j] /= static_cast<double>(n);

        std::vector<double> xr = add_scaled(centroid, subtract(centroid, simplex[n]), kAlpha);
        double fr = objective(xr);

        if (fr < fvals[0]) {
            std::vector<double> xe = add_scaled(centroid, subtract(xr, centroid), kGamma);
            double fe = objective(xe);
            if (fe < fr) {
                simplex[n] = xe;
                fvals[n] = fe;
            } else {
                simplex[n] = xr;
                fvals[n] = fr;
            }
        } else if (fr < fvals[n - 1]) {
            simplex[n] = xr;
            fvals[n] = fr;
        } else {
            bool shrink = false;
            if (fr < fvals[n]) {
                std::vector<double> xc = add_scaled(centroid, subtract(xr, centroid), kRho);
                double fc = objective(xc);
                if (fc <= fr) {
                    simplex[n] = xc;
                    fvals[n] = fc;
                } else {
                    shrink = true;
                }
            } else {
                std::vector<double> xc = add_scaled(centroid, subtract(simplex[n], centroid), kRho);
                double fc = objective(xc);
                if (fc < fvals[n]) {
                    simplex[n] = xc;
                    fvals[n] = fc;
                } else {
                    shrink = true;
                }
            }
            if (shrink) {
                for (size_t i = 1; i <= n; ++i) {
                    simplex[i] = add_scaled(simplex[0], subtract(simplex[i], simplex[0]), kSigma);
                    fvals[i] = objective(simplex[i]);
                }
            }
        }

        sort_simplex();
        ++iter;
    }

    return {simplex[0], fvals[0], iter};
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Build and run tests**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS (adds 1 test case to whatever Phase 1 left passing).

- [ ] **Step 5: Commit**

```bash
git add cpp/CMakeLists.txt cpp/include/pareto_nbd/nelder_mead.hpp cpp/src/nelder_mead.cpp cpp/tests/test_nelder_mead.cpp
git commit -m "feat(cpp): generic Nelder-Mead simplex optimizer"
```

---

### Task 3: `clv` — `posterior_mean_nu` and `predict_clv_distribution`

**Files:**
- Create: `cpp/include/pareto_nbd/clv.hpp`
- Create: `cpp/src/clv.cpp`
- Create: `cpp/tests/test_clv.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `struct GammaGammaParams{double p, q, v;}`;
  `pareto_nbd::posterior_mean_nu(x, m_obs, params) -> std::vector<double>`
  (the deterministic Inverse-Gamma posterior mean, mirroring the analytical
  formula inside Python's `amortized.py`-adjacent `clv.py` usage: `shape =
  x>0 ? p*x+q : q`, `scale = x>0 ? p*x*m_obs+v : v`, mean `=
  scale/(shape-1)`); `pareto_nbd::predict_clv_distribution(pred_x_star,
  nu_draws, discount_rate) -> std::vector<std::vector<double>>` (elementwise
  product times `exp(-discount_rate)`). Both consumed by Task 5's
  statistical check and available for later product code.

- [ ] **Step 1: Write the failing test and interface**

```cpp
// cpp/include/pareto_nbd/clv.hpp
#pragma once
#include <vector>

namespace pareto_nbd {

struct GammaGammaParams {
    double p;
    double q;
    double v;
};

// Analytical posterior mean of a customer's mean transaction value nu_i,
// given fitted Gamma-Gamma parameters. Mirrors the formula used in
// clv.py's sample_posterior_nu docstring: shape = p*x_i+q (or q if x_i==0),
// scale = p*x_i*m_obs_i+v (or v if x_i==0), posterior mean = scale/(shape-1).
// Pure closed-form arithmetic — no optimizer, no RNG.
std::vector<double> posterior_mean_nu(const std::vector<double>& x,
                                       const std::vector<double>& m_obs,
                                       const GammaGammaParams& params);

// CLV_i = x_star_i * nu_i * exp(-discount_rate), elementwise over an
// (n_draws x N) grid. Mirrors clv.predict_clv_distribution exactly.
std::vector<std::vector<double>> predict_clv_distribution(
    const std::vector<std::vector<double>>& pred_x_star,
    const std::vector<std::vector<double>>& nu_draws,
    double discount_rate);

}  // namespace pareto_nbd
```

```cpp
// cpp/tests/test_clv.cpp
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <vector>
#include "pareto_nbd/clv.hpp"

TEST_CASE("posterior_mean_nu matches the Python reference", "[clv]") {
    std::vector<double> x     = {0, 1, 2, 0, 3, 1, 0, 5, 4, 2};
    std::vector<double> m_obs = {0, 10.0, 15.5, 0, 20.0, 8.0, 0, 30.0, 25.0, 12.0};
    pareto_nbd::GammaGammaParams params{2.5, 3.2, 12.0};

    auto mean = pareto_nbd::posterior_mean_nu(x, m_obs, params);

    std::vector<double> expected = {
        5.454545454545454, 7.872340425531915, 12.430555555555557, 5.454545454545454,
        16.701030927835053, 6.808510638297872, 5.454545454545454, 26.3265306122449,
        21.475409836065577, 10.000000000000002,
    };
    REQUIRE(mean.size() == expected.size());
    for (size_t i = 0; i < expected.size(); ++i) {
        REQUIRE(mean[i] == Catch::Approx(expected[i]).epsilon(1e-9));
    }
}

TEST_CASE("predict_clv_distribution matches the Python reference", "[clv]") {
    std::vector<std::vector<double>> pred_x_star = {{1.0, 2.0, 3.0}, {2.0, 1.0, 4.0}};
    std::vector<std::vector<double>> nu_draws    = {{10.0, 5.0, 2.0}, {8.0, 6.0, 3.0}};

    auto out = pareto_nbd::predict_clv_distribution(pred_x_star, nu_draws, 0.1);

    std::vector<std::vector<double>> expected = {
        {9.048374180359595, 9.048374180359595, 5.4290245082157575},
        {14.477398688575352, 5.4290245082157575, 10.858049016431515},
    };
    REQUIRE(out.size() == expected.size());
    for (size_t d = 0; d < expected.size(); ++d) {
        for (size_t i = 0; i < expected[d].size(); ++i) {
            REQUIRE(out[d][i] == Catch::Approx(expected[d][i]).epsilon(1e-9));
        }
    }
}
```

Modify `cpp/CMakeLists.txt`: add `src/clv.cpp` to `amortized_inference`'s
sources, and `tests/test_clv.cpp` to `unit_tests`'s sources.

- [ ] **Step 2: Build to verify it fails**

Run: `cmake --preset default && cmake --build build`
Expected: FAIL — `CMake Error: Cannot find source file: src/clv.cpp`

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/src/clv.cpp
#include "pareto_nbd/clv.hpp"

#include <cmath>

namespace pareto_nbd {

std::vector<double> posterior_mean_nu(const std::vector<double>& x,
                                       const std::vector<double>& m_obs,
                                       const GammaGammaParams& params) {
    std::vector<double> out(x.size());
    for (size_t i = 0; i < x.size(); ++i) {
        double shape, scale;
        if (x[i] > 0.0) {
            shape = params.p * x[i] + params.q;
            scale = params.p * x[i] * m_obs[i] + params.v;
        } else {
            shape = params.q;
            scale = params.v;
        }
        out[i] = scale / (shape - 1.0);
    }
    return out;
}

std::vector<std::vector<double>> predict_clv_distribution(
    const std::vector<std::vector<double>>& pred_x_star,
    const std::vector<std::vector<double>>& nu_draws,
    double discount_rate) {
    double dfactor = std::exp(-discount_rate);
    std::vector<std::vector<double>> out(pred_x_star.size());
    for (size_t d = 0; d < pred_x_star.size(); ++d) {
        out[d].resize(pred_x_star[d].size());
        for (size_t i = 0; i < pred_x_star[d].size(); ++i) {
            out[d][i] = pred_x_star[d][i] * nu_draws[d][i] * dfactor;
        }
    }
    return out;
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Build and run tests**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS (2 new test cases).

- [ ] **Step 5: Commit**

```bash
git add cpp/CMakeLists.txt cpp/include/pareto_nbd/clv.hpp cpp/src/clv.cpp cpp/tests/test_clv.cpp
git commit -m "feat(cpp): port posterior_mean_nu and predict_clv_distribution"
```

---

### Task 4: `clv` — `fit_gamma_gamma`

**Files:**
- Modify: `cpp/include/pareto_nbd/clv.hpp`
- Modify: `cpp/src/clv.cpp`
- Modify: `cpp/tests/test_clv.cpp`

**Interfaces:**
- Consumes: `pareto_nbd::nelder_mead` (Task 2).
- Produces: `pareto_nbd::fit_gamma_gamma(x, m_obs) -> GammaGammaParams` —
  consumed by Task 5's statistical check (and available for later product
  code needing to fit a fresh cohort's spend model).

- [ ] **Step 1: Write the failing test and interface addition**

```cpp
// append to cpp/include/pareto_nbd/clv.hpp, inside namespace pareto_nbd
// Fits (p, q, v) by maximum likelihood via Nelder-Mead, mirroring
// clv.fit_gamma_gamma exactly: filters to customers with x>0 and
// m_obs>0, optimizes the same log-space negative log-likelihood from the
// same x0 = log([2.0, 2.0, 10.0]) starting point. A from-scratch
// optimizer is not expected to land on bit-identical (p,q,v) to SciPy's
// — see the plan's Global Constraints for the tolerance this is checked
// against.
GammaGammaParams fit_gamma_gamma(const std::vector<double>& x, const std::vector<double>& m_obs);
```

```cpp
// append to cpp/tests/test_clv.cpp
#include <fstream>
#include <nlohmann/json.hpp>

TEST_CASE("fit_gamma_gamma matches the Python reference within 5% relative", "[clv]") {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/clv_conformal_golden.json");
    nlohmann::json golden;
    f >> golden;

    std::vector<double> x = golden["x"].get<std::vector<double>>();
    std::vector<double> m_obs = golden["m_obs"].get<std::vector<double>>();

    auto fit = pareto_nbd::fit_gamma_gamma(x, m_obs);

    REQUIRE(fit.p == Catch::Approx(golden["p"].get<double>()).epsilon(0.05));
    REQUIRE(fit.q == Catch::Approx(golden["q"].get<double>()).epsilon(0.05));
    REQUIRE(fit.v == Catch::Approx(golden["v"].get<double>()).epsilon(0.05));
}
```

This test needs `PROJECT_MODELS_DIR` — already defined for the
`unit_tests` target by Phase 1's Task 10 (`target_compile_definitions(unit_tests
PRIVATE PROJECT_MODELS_DIR="${CMAKE_SOURCE_DIR}/../models")`); no CMake
change needed for this alone.

- [ ] **Step 2: Build to verify it fails**

Run: `cmake --build build`
Expected: FAIL — linker error, undefined reference to `pareto_nbd::fit_gamma_gamma`
(the header declares it but `clv.cpp` doesn't define it yet).

- [ ] **Step 3: Write the implementation**

```cpp
// append to cpp/src/clv.cpp
#include "pareto_nbd/nelder_mead.hpp"

namespace pareto_nbd {
namespace {

double gamma_gamma_neg_loglik(const std::vector<double>& log_params,
                               const std::vector<double>& x_val,
                               const std::vector<double>& m_val) {
    double p = std::exp(log_params[0]);
    double q = std::exp(log_params[1]);
    double v = std::exp(log_params[2]);

    double ll = 0.0;
    for (size_t i = 0; i < x_val.size(); ++i) {
        double xi = x_val[i];
        double mi = m_val[i];
        ll += std::lgamma(p * xi + q) - std::lgamma(p * xi) - std::lgamma(q)
              + q * std::log(v) + (p * xi - 1.0) * std::log(mi)
              + (p * xi) * std::log(p * xi)
              - (p * xi + q) * std::log(p * xi * mi + v);
    }
    return -ll;
}

}  // namespace

GammaGammaParams fit_gamma_gamma(const std::vector<double>& x, const std::vector<double>& m_obs) {
    std::vector<double> x_val, m_val;
    for (size_t i = 0; i < x.size(); ++i) {
        if (x[i] > 0.0 && m_obs[i] > 0.0) {
            x_val.push_back(x[i]);
            m_val.push_back(m_obs[i]);
        }
    }

    auto objective = [&](const std::vector<double>& log_params) {
        return gamma_gamma_neg_loglik(log_params, x_val, m_val);
    };

    std::vector<double> x0 = {std::log(2.0), std::log(2.0), std::log(10.0)};
    auto result = nelder_mead(objective, x0);

    return {std::exp(result.x[0]), std::exp(result.x[1]), std::exp(result.x[2])};
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Build and run tests**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -V`
Expected: PASS. Note the actual achieved relative error in the verbose
output — it should be well under 5% given the golden case is a
well-conditioned, non-degenerate fit (see Task 1's fixture design).

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/clv.hpp cpp/src/clv.cpp cpp/tests/test_clv.cpp
git commit -m "feat(cpp): port fit_gamma_gamma via Nelder-Mead MLE"
```

**Escalation note:** if the achieved relative error is far outside 5% (e.g.
>20%), do not just widen the tolerance — that usually means either the
objective function was transcribed incorrectly (double-check every term
against `src/clv.py:36-42`) or the Nelder-Mead port has a bug (check against
Task 2's own passing test first, in isolation, before suspecting the
objective). Report as BLOCKED with the actual numbers if you can't
determine which.

---

### Task 5: `clv` — `sample_posterior_nu` (statistical convergence check)

**Files:**
- Modify: `cpp/include/pareto_nbd/clv.hpp`
- Modify: `cpp/src/clv.cpp`
- Modify: `cpp/tests/test_clv.cpp`

**Interfaces:**
- Consumes: `GammaGammaParams`, `posterior_mean_nu` (Task 3); reuses the
  golden JSON's `x`/`m_obs`/`p`/`q`/`v` (Task 1/4).
- Produces: `pareto_nbd::sample_posterior_nu(x, m_obs, params, n_draws,
  seed) -> std::vector<std::vector<double>>` (an `n_draws x N` matrix of
  Monte Carlo posterior draws of each customer's mean spend) — available
  for later product code combining with purchase-count forecasts into full
  probabilistic CLV.

- [ ] **Step 1: Write the failing test and interface addition**

```cpp
// append to cpp/include/pareto_nbd/clv.hpp, inside namespace pareto_nbd
#include <cstdint>

// Monte Carlo posterior draws of each customer's mean transaction value
// nu_i: draw g ~ Gamma(shape, rate=scale) and return nu = 1/g (nu has an
// Inverse-Gamma posterior; sampling a Gamma directly would invert the
// scale — see clv.py's sample_posterior_nu docstring). NOT expected to
// reproduce numpy's specific random draws — cross-checked only via
// statistical convergence of the empirical mean to posterior_mean_nu's
// analytical answer (see the plan's Global Constraints).
std::vector<std::vector<double>> sample_posterior_nu(const std::vector<double>& x,
                                                      const std::vector<double>& m_obs,
                                                      const GammaGammaParams& params,
                                                      size_t n_draws, uint64_t seed);
```

```cpp
// append to cpp/tests/test_clv.cpp
TEST_CASE("sample_posterior_nu's empirical mean converges to the analytical posterior mean", "[clv]") {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/clv_conformal_golden.json");
    nlohmann::json golden;
    f >> golden;

    std::vector<double> x = golden["x"].get<std::vector<double>>();
    std::vector<double> m_obs = golden["m_obs"].get<std::vector<double>>();
    pareto_nbd::GammaGammaParams params{
        golden["p"].get<double>(), golden["q"].get<double>(), golden["v"].get<double>()};

    auto analytical = pareto_nbd::posterior_mean_nu(x, m_obs, params);
    auto draws = pareto_nbd::sample_posterior_nu(x, m_obs, params, 200000, 7);

    REQUIRE(draws.size() == 200000);
    REQUIRE(draws[0].size() == x.size());

    // Empirical mean per customer over all draws.
    std::vector<double> empirical_mean(x.size(), 0.0);
    for (const auto& draw : draws) {
        for (size_t i = 0; i < x.size(); ++i) empirical_mean[i] += draw[i];
    }
    for (double& m : empirical_mean) m /= static_cast<double>(draws.size());

    // Check a sample of customers (checking all 500 with per-customer
    // Monte Carlo noise would make this test flaky; the mean absolute
    // relative error across a subset is a stabler statistic).
    double total_rel_err = 0.0;
    for (size_t i = 0; i < x.size(); i += 25) {  // every 25th customer, ~20 checks
        total_rel_err += std::abs(empirical_mean[i] - analytical[i]) / analytical[i];
    }
    double mean_rel_err = total_rel_err / (x.size() / 25 + 1);
    REQUIRE(mean_rel_err < 0.05);
}
```

- [ ] **Step 2: Build to verify it fails**

Run: `cmake --build build`
Expected: FAIL — linker error, undefined reference to `pareto_nbd::sample_posterior_nu`.

- [ ] **Step 3: Write the implementation**

```cpp
// append to cpp/src/clv.cpp
#include <random>

namespace pareto_nbd {

std::vector<std::vector<double>> sample_posterior_nu(const std::vector<double>& x,
                                                      const std::vector<double>& m_obs,
                                                      const GammaGammaParams& params,
                                                      size_t n_draws, uint64_t seed) {
    const size_t N = x.size();
    std::vector<double> shape(N), scale(N);
    for (size_t i = 0; i < N; ++i) {
        if (x[i] > 0.0) {
            shape[i] = params.p * x[i] + params.q;
            scale[i] = params.p * x[i] * m_obs[i] + params.v;
        } else {
            shape[i] = params.q;
            scale[i] = params.v;
        }
    }

    std::vector<std::gamma_distribution<double>> dists;
    dists.reserve(N);
    for (size_t i = 0; i < N; ++i) {
        dists.emplace_back(shape[i], 1.0 / scale[i]);  // Gamma(shape, scale=1/scale_i)
    }

    std::mt19937_64 rng(seed);
    std::vector<std::vector<double>> nu(n_draws, std::vector<double>(N));
    for (size_t d = 0; d < n_draws; ++d) {
        for (size_t i = 0; i < N; ++i) {
            nu[d][i] = 1.0 / dists[i](rng);
        }
    }
    return nu;
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Build and run tests**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS. (This test allocates a 200000 x 500 matrix of doubles —
~800MB; if that's prohibitive on the build machine, reduce `n_draws` to
50000 and note the change in the commit message, keeping the 0.05
relative-error threshold.)

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/clv.hpp cpp/src/clv.cpp cpp/tests/test_clv.cpp
git commit -m "feat(cpp): port sample_posterior_nu, verified by MC convergence"
```

---

### Task 6: `conformal` — `randomized_pit`

**Files:**
- Create: `cpp/include/pareto_nbd/conformal.hpp`
- Create: `cpp/src/conformal.cpp`
- Create: `cpp/tests/test_conformal.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `pareto_nbd::randomized_pit(pred, y, tie_break) ->
  std::vector<double>` — a deterministic variant of `score.randomized_pit`
  that takes the uniform tie-breaking draws as an input vector instead of
  an RNG (so it's exactly golden-file testable; production code generates
  `tie_break` itself before calling this). Consumed by Task 7 in describing
  the full conformal pipeline (though Task 7's own function takes the
  already-computed PITs `u` directly, per the plan's design — see Task 7).

- [ ] **Step 1: Write the failing test and interface**

```cpp
// cpp/include/pareto_nbd/conformal.hpp
#pragma once
#include <vector>

namespace pareto_nbd {

// Randomized PIT for count forecasts (Czado, Gneiting & Held 2009),
// mirroring score.randomized_pit exactly except that the tie-breaking
// uniform draws are passed in as `tie_break` (one per customer) instead
// of generated from an RNG internally — this makes the function pure and
// exactly golden-file testable; a caller generates `tie_break` itself
// (e.g. via std::uniform_real_distribution) before calling this.
// pred: (J x N) predictive draws. y: (N,) truths. tie_break: (N,) in [0,1).
std::vector<double> randomized_pit(const std::vector<std::vector<double>>& pred,
                                    const std::vector<double>& y,
                                    const std::vector<double>& tie_break);

}  // namespace pareto_nbd
```

```cpp
// cpp/tests/test_conformal.cpp
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <vector>
#include "pareto_nbd/conformal.hpp"

TEST_CASE("randomized_pit matches the Python reference", "[conformal]") {
    std::vector<std::vector<double>> pred = {
        {0, 1, 2, 5},
        {1, 1, 3, 6},
        {1, 2, 2, 4},
        {2, 2, 2, 5},
        {0, 3, 1, 7},
        {1, 1, 2, 5},
    };
    std::vector<double> y = {1.0, 2.0, 2.0, 5.0};
    std::vector<double> tie_break = {0.3, 0.6, 0.9, 0.1};

    auto pit = pareto_nbd::randomized_pit(pred, y, tie_break);

    std::vector<double> expected = {
        0.4833333333333333, 0.7, 0.7666666666666666, 0.21666666666666667,
    };
    REQUIRE(pit.size() == expected.size());
    for (size_t i = 0; i < expected.size(); ++i) {
        REQUIRE(pit[i] == Catch::Approx(expected[i]).epsilon(1e-9));
    }
}
```

Modify `cpp/CMakeLists.txt`: add `src/conformal.cpp` to
`amortized_inference`'s sources, and `tests/test_conformal.cpp` to
`unit_tests`'s sources.

- [ ] **Step 2: Build to verify it fails**

Run: `cmake --preset default && cmake --build build`
Expected: FAIL — `CMake Error: Cannot find source file: src/conformal.cpp`

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/src/conformal.cpp
#include "pareto_nbd/conformal.hpp"

namespace pareto_nbd {

std::vector<double> randomized_pit(const std::vector<std::vector<double>>& pred,
                                    const std::vector<double>& y,
                                    const std::vector<double>& tie_break) {
    const size_t J = pred.size();
    const size_t N = y.size();
    std::vector<double> out(N);
    for (size_t i = 0; i < N; ++i) {
        size_t below_count = 0, at_count = 0;
        for (size_t j = 0; j < J; ++j) {
            if (pred[j][i] < y[i]) ++below_count;
            if (pred[j][i] == y[i]) ++at_count;
        }
        double below = static_cast<double>(below_count) / static_cast<double>(J);
        double at = static_cast<double>(at_count) / static_cast<double>(J);
        out[i] = below + tie_break[i] * at;
    }
    return out;
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Build and run tests**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cpp/CMakeLists.txt cpp/include/pareto_nbd/conformal.hpp cpp/src/conformal.cpp cpp/tests/test_conformal.cpp
git commit -m "feat(cpp): port randomized_pit"
```

---

### Task 7: `conformal` — `apply_conformal_warp`

**Files:**
- Modify: `cpp/include/pareto_nbd/conformal.hpp`
- Modify: `cpp/src/conformal.cpp`
- Modify: `cpp/tests/test_conformal.cpp`

**Interfaces:**
- Produces: `pareto_nbd::apply_conformal_warp(u, p, pred_test) ->
  std::vector<std::vector<double>>` — the deterministic core of
  `conformal.recalibrate_samples`: given already-computed calibration PITs
  `u` and already-drawn output-quantile levels `p` (production code
  generates `p` itself, e.g. via `std::uniform_real_distribution`, before
  calling this — same "randomness as an input, math as the tested part"
  split as Task 6), returns the recalibrated predictive samples. This is
  the last function in this plan; together with Tasks 3-6 it completes the
  product-relevant CLV + conformal surface, ready for whatever later phase
  wires it into an actual forecast-serving pipeline.

- [ ] **Step 1: Write the failing test and interface addition**

```cpp
// append to cpp/include/pareto_nbd/conformal.hpp, inside namespace pareto_nbd
#include <cstddef>

// Deterministic core of conformal.recalibrate_samples: given calibration
// PITs `u` (N_cal values, from randomized_pit), output-quantile draws `p`
// (n_out values in [0,1), already generated by the caller), and the raw
// test-set predictive samples `pred_test` (J x N_test, NOT pre-sorted —
// this function sorts internally, matching
// np.sort(pred_test, axis=0) in the Python original), returns the (n_out x
// N_test) recalibrated predictive. Uses the same linear-interpolation
// quantile method as numpy's default (see cohort_features.cpp's
// quantile_linear for the same formula applied elsewhere in this project).
std::vector<std::vector<double>> apply_conformal_warp(
    const std::vector<double>& u, const std::vector<double>& p,
    const std::vector<std::vector<double>>& pred_test);
```

```cpp
// append to cpp/tests/test_conformal.cpp
TEST_CASE("apply_conformal_warp matches the Python reference", "[conformal]") {
    std::vector<double> u = {0.1, 0.9, 0.3, 0.5, 0.7, 0.2, 0.95, 0.05, 0.6, 0.4};
    std::vector<double> p = {0.25, 0.75, 0.5};
    std::vector<std::vector<double>> pred_test = {
        {1, 2, 3}, {4, 5, 6}, {7, 8, 9}, {10, 11, 12}, {13, 14, 15},
    };

    auto out = pareto_nbd::apply_conformal_warp(u, p, pred_test);

    std::vector<std::vector<double>> expected = {
        {4.0, 5.0, 6.0}, {10.0, 11.0, 12.0}, {7.0, 8.0, 9.0},
    };
    REQUIRE(out.size() == expected.size());
    for (size_t k = 0; k < expected.size(); ++k) {
        REQUIRE(out[k].size() == expected[k].size());
        for (size_t i = 0; i < expected[k].size(); ++i) {
            REQUIRE(out[k][i] == Catch::Approx(expected[k][i]).epsilon(1e-9));
        }
    }
}
```

- [ ] **Step 2: Build to verify it fails**

Run: `cmake --build build`
Expected: FAIL — linker error, undefined reference to `pareto_nbd::apply_conformal_warp`.

- [ ] **Step 3: Write the implementation**

```cpp
// append to cpp/src/conformal.cpp
#include <algorithm>
#include <cmath>

namespace pareto_nbd {
namespace {

// numpy.quantile's default ("linear") interpolation method, over an
// already-sorted vector. Same formula as cohort_features.cpp's
// quantile_linear, duplicated here since these two files have no shared
// dependency and each is small enough to keep self-contained.
double quantile_linear_sorted(const std::vector<double>& sorted, double q) {
    double h = q * static_cast<double>(sorted.size() - 1);
    size_t lo = static_cast<size_t>(std::floor(h));
    size_t hi = static_cast<size_t>(std::ceil(h));
    if (lo == hi) return sorted[lo];
    double frac = h - static_cast<double>(lo);
    return sorted[lo] + frac * (sorted[hi] - sorted[lo]);
}

}  // namespace

std::vector<std::vector<double>> apply_conformal_warp(
    const std::vector<double>& u, const std::vector<double>& p,
    const std::vector<std::vector<double>>& pred_test) {
    const size_t J = pred_test.size();
    const size_t N_test = J > 0 ? pred_test[0].size() : 0;

    // Sort each column (across the J draws) independently.
    std::vector<std::vector<double>> ps(J, std::vector<double>(N_test));
    for (size_t i = 0; i < N_test; ++i) {
        std::vector<double> col(J);
        for (size_t j = 0; j < J; ++j) col[j] = pred_test[j][i];
        std::sort(col.begin(), col.end());
        for (size_t j = 0; j < J; ++j) ps[j][i] = col[j];
    }

    std::vector<double> u_sorted = u;
    std::sort(u_sorted.begin(), u_sorted.end());

    const size_t n_out = p.size();
    std::vector<std::vector<double>> out(n_out);
    for (size_t k = 0; k < n_out; ++k) {
        double w = quantile_linear_sorted(u_sorted, p[k]);
        long idx = std::lround(w * static_cast<double>(J - 1));
        idx = std::max<long>(0, std::min<long>(idx, static_cast<long>(J) - 1));
        out[k] = ps[static_cast<size_t>(idx)];
    }
    return out;
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Build and run tests**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -V`
Expected: PASS — all test cases across this plan's 7 tasks green
(nelder_mead, clv x4, conformal x2 — 6 new test cases on top of Phase 1's
4, for 10 total).

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/conformal.hpp cpp/src/conformal.cpp cpp/tests/test_conformal.cpp
git commit -m "feat(cpp): port apply_conformal_warp"
```

---

## Definition of done

Running `ctest --test-dir cpp/build` passes all 10 test cases (4 from
Phase 1, 6 from this plan). The four closed-form functions
(`posterior_mean_nu`, `predict_clv_distribution`, `randomized_pit`,
`apply_conformal_warp`) match Python bit-for-bit within 1e-9 relative
tolerance; `fit_gamma_gamma` matches within 5% relative on a well-
conditioned synthetic cohort; `sample_posterior_nu`'s Monte Carlo output
converges to the analytical posterior mean within 5%. This closes the
product-relevant surface of Phase 2 (the paper-only evaluation harnesses in
`clv.py`/`conformal.py` — `score_clv_forecast`, `compare_conformal*` — are
research/benchmarking code, not part of the SaaS product pipeline, and are
not in scope for this or any future phase of the app build). The next
phase (Arrow-based CSV ingestion, per spec §9) does not depend on anything
in this plan beyond `cpp/`'s existing structure.
