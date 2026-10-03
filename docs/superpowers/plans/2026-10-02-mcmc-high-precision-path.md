# High-Precision MCMC Path (Spec Phase 6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a job opt into a high-precision Pareto/NBD fit (the Abe 2009 Gibbs sampler in `src/estimate.py`) via a Python subprocess, selectable three ways (per-upload mode, automatic for small cohorts, post-hoc "refit" button), keeping the posterior draws for later conformal-interval work.

**Architecture:** One job-level setting `fit_mode ∈ {auto, fast, mcmc}` drives all three triggers. The C++ worker decides (`ChooseFitMethod`), and for MCMC writes the ingested cohort to a small CSV, spawns `python src/mcmc_cli.py` with a wall-clock timeout, reads posterior-mean `r, alpha, s, beta` back from JSON and keeps the draws as an `.npz`. The existing C++ closed-form scoring then runs unchanged with those parameters. **Any MCMC failure (no Python, timeout, non-zero exit, bad JSON) falls back to the amortized fit** and records a user-readable `fit_note`; MCMC is an enhancement and must never fail a job.

**Tech Stack:** C++17 (Drogon, Catch2, nlohmann_json), Python 3.13 (numpy, pandas, scipy; pytest), SvelteKit + Vitest, Postgres.

**Spec:** `docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md` (§4.3 "Explicitly deferred", §9 item 6)

## Global Constraints

- The MCMC sampler stays in Python and is **not** ported to C++ (spec §4.3 "Explicitly deferred"; §10 "Native C++ MCMC" out of scope).
- Phase 6 is "Stretch, non-blocking" (spec §9.6): the fast path must behave exactly as before when MCMC is not chosen or fails.
- Worker never crashes on a job (existing contract in `worker.hpp`): all new failure paths degrade to the amortized fit.
- `db/schema.sql` is split on `;` by `ApplySchema` — **no semicolon anywhere inside SQL comments**.
- Windows build: C++ builds go through `vcvars64.bat`; tree is `cpp/build` (Ninja). After `--target unit_tests`, also build `api_server` and `worker` before any live run. Run api_server and worker from the same cwd.
- Frontend: `cd frontend && npm test` (add `-- --maxWorkers=2` if workers crash).
- Units: `x, t_x, T_cal` are in weeks, produced by `ingest_csv`, identical to what `fit_mcmc` expects.

## Review Focus

1. Python not installed / `PARETO_PYTHON` wrong → job still `done` via amortized fit, with a `fit_note` (tested in Task 4).
2. MCMC hangs → killed at timeout, job still `done` (tested in Task 3 and 4).
3. Explicit `mcmc` on an oversized cohort → fast fit used with an explanatory note rather than hours of compute (tested in Task 2).
4. `auto` on a tiny cohort (<50 customers) must NOT spawn Python — existing worker tests use 3 customers (tested in Task 2).
5. Refit on a job that is not `done` or doesn't exist → 409 / 404, never a queued orphan (tested in Task 5).
6. Invalid `fit_mode` query value → 400, not a silent default (tested in Task 5).

## File Structure

| File | Responsibility |
|---|---|
| `src/mcmc_cli.py` (new) | CLI wrapper around `fit_mcmc`: cohort CSV in → posterior-mean JSON + draws `.npz` out |
| `tests/test_mcmc_cli.py` (new) | pytest for the CLI |
| `db/schema.sql` | new `jobs` columns `fit_mode, fit_method, fit_note, source_job_id, mcmc_draws_path` |
| `cpp/include/pareto_nbd/fit_policy.hpp`, `cpp/src/fit_policy.cpp` (new) | `FitMode`, `ParseFitMode`, `ChooseFitMethod` — pure decision logic |
| `cpp/include/pareto_nbd/subprocess.hpp`, `cpp/src/subprocess.cpp` (new) | `RunWithTimeout` — cross-platform spawn + kill |
| `cpp/include/pareto_nbd/mcmc_fit.hpp`, `cpp/src/mcmc_fit.cpp` (new) | `RunMcmcFit` — builds files, calls CLI, parses result |
| `cpp/src/worker.cpp` | choose method, call MCMC or amortized, persist fit metadata |
| `cpp/src/api_routes.cpp` | `fit_mode` on `POST /uploads`, new `POST /jobs/{id}/refit`, fit fields on `GET /jobs/{id}` |
| `cpp/tests/*` | tests per task; `cpp/tests/fixtures/fake_mcmc_cli.py` stub |
| `frontend/src/lib/{types,api}.ts`, `routes/+page.svelte`, `routes/jobs/[id]/+page.svelte` | mode selector, fit badge, refit button |

---

### Task 1: Python MCMC CLI

**Files:**
- Create: `src/mcmc_cli.py`
- Test: `tests/test_mcmc_cli.py`

**Interfaces:**
- Produces: `python src/mcmc_cli.py --cohort C.csv --out O.json --draws D.npz [--n-draws N --burn-in B --thin T --seed S]`; exit 0 on success, 2 on bad input. `O.json` = `{"r","alpha","s","beta","n_keep","n_customers","elapsed_s"}` (posterior means). `D.npz` = `pop_draws (n_keep,4)`, `lam (n_keep,N)` float32, `mu (n_keep,N)` float32. `O.json` is written **last**.
- Also exposes `run(cohort_csv, out_json, draws_npz, n_draws=6000, burn_in=2000, thin=8, seed=0) -> dict` and `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing test** — `tests/test_mcmc_cli.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_mcmc_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcmc_cli'`

- [ ] **Step 3: Implement** — `src/mcmc_cli.py`

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_mcmc_cli.py -v`
Expected: 3 passed. If `n_keep` is not 15, recompute: `len(range(burn_in, n_draws, thin))` = `len(range(20, 80, 4))` = 15.

- [ ] **Step 5: Commit**

```bash
git add src/mcmc_cli.py tests/test_mcmc_cli.py
git commit -m "feat(py): mcmc_cli -- subprocess entry point for the high-precision Pareto/NBD fit"
```

---

### Task 2: Schema + fit policy (pure decision logic)

**Files:**
- Modify: `db/schema.sql` (append after the `data_quality` ALTER)
- Create: `cpp/include/pareto_nbd/fit_policy.hpp`, `cpp/src/fit_policy.cpp`
- Modify: `cpp/CMakeLists.txt` (add `src/fit_policy.cpp` to `amortized_inference`, `tests/test_fit_policy.cpp` to `unit_tests`)
- Test: `cpp/tests/test_fit_policy.cpp`

**Interfaces:**
- Produces:
  ```cpp
  enum class FitMode { Auto, Fast, Mcmc };
  enum class FitMethod { Amortized, Mcmc };
  inline constexpr size_t kAutoMcmcMinCustomers = 50;
  inline constexpr size_t kAutoMcmcMaxCustomers = 2000;
  inline constexpr size_t kMcmcMaxCustomers = 20000;
  std::optional<FitMode> ParseFitMode(const std::string& s);   // "auto"|"fast"|"mcmc"
  std::string ToString(FitMode m);
  struct FitDecision { FitMethod method; std::string note; };   // note empty = nothing to tell the user
  FitDecision ChooseFitMethod(FitMode mode, size_t n_customers);
  ```

- [ ] **Step 1: Write the failing test** — `cpp/tests/test_fit_policy.cpp`

```cpp
#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/fit_policy.hpp"

using namespace pareto_nbd;

TEST_CASE("ParseFitMode accepts the three modes and rejects anything else", "[fit_policy]") {
    REQUIRE(ParseFitMode("auto") == FitMode::Auto);
    REQUIRE(ParseFitMode("fast") == FitMode::Fast);
    REQUIRE(ParseFitMode("mcmc") == FitMode::Mcmc);
    REQUIRE_FALSE(ParseFitMode("MCMC").has_value());
    REQUIRE_FALSE(ParseFitMode("").has_value());
    REQUIRE(ToString(FitMode::Mcmc) == "mcmc");
}

TEST_CASE("auto picks MCMC only inside the small-cohort window", "[fit_policy]") {
    REQUIRE(ChooseFitMethod(FitMode::Auto, 3).method == FitMethod::Amortized);        // too tiny
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMinCustomers - 1).method == FitMethod::Amortized);
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMinCustomers).method == FitMethod::Mcmc);
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMaxCustomers).method == FitMethod::Mcmc);
    REQUIRE(ChooseFitMethod(FitMode::Auto, kAutoMcmcMaxCustomers + 1).method == FitMethod::Amortized);
    REQUIRE(ChooseFitMethod(FitMode::Auto, 10).note.empty());
}

TEST_CASE("fast never uses MCMC and explicit mcmc honours small cohorts", "[fit_policy]") {
    REQUIRE(ChooseFitMethod(FitMode::Fast, 100).method == FitMethod::Amortized);
    REQUIRE(ChooseFitMethod(FitMode::Mcmc, 3).method == FitMethod::Mcmc);
    REQUIRE(ChooseFitMethod(FitMode::Mcmc, kMcmcMaxCustomers).method == FitMethod::Mcmc);
}

TEST_CASE("explicit mcmc above the hard cap falls back with an explanatory note", "[fit_policy]") {
    auto d = ChooseFitMethod(FitMode::Mcmc, kMcmcMaxCustomers + 1);
    REQUIRE(d.method == FitMethod::Amortized);
    REQUIRE(d.note.find("20000") != std::string::npos);
}
```

- [ ] **Step 2: Run to verify it fails**

Run (from a `vcvars64.bat` shell): `cmake --build cpp/build --target unit_tests`
Expected: FAIL — `fit_policy.hpp` not found.

- [ ] **Step 3: Implement**

`cpp/include/pareto_nbd/fit_policy.hpp`:
```cpp
#pragma once
#include <cstddef>
#include <optional>
#include <string>

namespace pareto_nbd {

// How the user asked a job to be fitted. Stored verbatim in jobs.fit_mode.
enum class FitMode { Auto, Fast, Mcmc };
// What the worker actually used. Stored in jobs.fit_method.
enum class FitMethod { Amortized, Mcmc };

// auto = MCMC only for cohorts big enough for it to be meaningful and small enough to be quick.
inline constexpr size_t kAutoMcmcMinCustomers = 50;
inline constexpr size_t kAutoMcmcMaxCustomers = 2000;
// Hard ceiling even for an explicit request: the Gibbs sampler is O(draws x customers) in numpy.
inline constexpr size_t kMcmcMaxCustomers = 20000;

std::optional<FitMode> ParseFitMode(const std::string& s);
std::string ToString(FitMode m);

struct FitDecision {
    FitMethod method;
    std::string note;  // non-empty only when the user asked for MCMC and did not get it
};

FitDecision ChooseFitMethod(FitMode mode, size_t n_customers);

}  // namespace pareto_nbd
```
`cpp/src/fit_policy.cpp`:
```cpp
#include "pareto_nbd/fit_policy.hpp"

namespace pareto_nbd {

std::optional<FitMode> ParseFitMode(const std::string& s) {
    if (s == "auto") return FitMode::Auto;
    if (s == "fast") return FitMode::Fast;
    if (s == "mcmc") return FitMode::Mcmc;
    return std::nullopt;
}

std::string ToString(FitMode m) {
    switch (m) {
        case FitMode::Auto: return "auto";
        case FitMode::Fast: return "fast";
        case FitMode::Mcmc: return "mcmc";
    }
    return "auto";
}

FitDecision ChooseFitMethod(FitMode mode, size_t n) {
    switch (mode) {
        case FitMode::Fast:
            return {FitMethod::Amortized, ""};
        case FitMode::Auto:
            if (n >= kAutoMcmcMinCustomers && n <= kAutoMcmcMaxCustomers)
                return {FitMethod::Mcmc, ""};
            return {FitMethod::Amortized, ""};
        case FitMode::Mcmc:
            if (n <= kMcmcMaxCustomers) return {FitMethod::Mcmc, ""};
            return {FitMethod::Amortized,
                    "Cohort has " + std::to_string(n) + " customers, above the " +
                        std::to_string(kMcmcMaxCustomers) +
                        "-customer limit for the high-precision refit - used the fast estimator instead."};
    }
    return {FitMethod::Amortized, ""};
}

}  // namespace pareto_nbd
```
`db/schema.sql` (append; note: **no semicolons in the comment**):
```sql
-- Fit selection. fit_mode is what the user asked for (auto, fast or mcmc). fit_method is what
-- the worker actually used (amortized or mcmc, NULL until the job finishes). fit_note explains
-- a fallback (for example the high-precision refit could not run). source_job_id links a refit
-- job to the job it re-fits. mcmc_draws_path is the storage key of the saved posterior draws.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fit_mode TEXT NOT NULL DEFAULT 'auto' CHECK (fit_mode IN ('auto','fast','mcmc'));
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fit_method TEXT CHECK (fit_method IN ('amortized','mcmc'));
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fit_note TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_job_id UUID REFERENCES jobs(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS mcmc_draws_path TEXT;
```
CMake: add `src/fit_policy.cpp` after `src/forecast.cpp` and `tests/test_fit_policy.cpp` after `tests/test_forecast.cpp`.

- [ ] **Step 4: Run to verify it passes**

Run: `cmake --build cpp/build --target unit_tests && cpp/build/unit_tests "[fit_policy]"`
Expected: all `[fit_policy]` cases pass. Then run `cpp/build/unit_tests "[db]"` to confirm the schema still applies (needs `docker compose up -d`).

- [ ] **Step 5: Commit**

```bash
git add db/schema.sql cpp/include/pareto_nbd/fit_policy.hpp cpp/src/fit_policy.cpp cpp/tests/test_fit_policy.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): fit_mode schema columns and ChooseFitMethod policy"
```

---

### Task 3: Subprocess runner with timeout

**Files:**
- Create: `cpp/include/pareto_nbd/subprocess.hpp`, `cpp/src/subprocess.cpp`
- Modify: `cpp/CMakeLists.txt` (add `src/subprocess.cpp`, `tests/test_subprocess.cpp`)
- Test: `cpp/tests/test_subprocess.cpp`

**Interfaces:**
- Produces:
  ```cpp
  struct SubprocessResult { bool launched = false; bool timed_out = false; int exit_code = -1; };
  SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds);
  ```
  `launched=false` means the process could not be started at all. On timeout the process is killed and `timed_out=true`.

- [ ] **Step 1: Write the failing test** — `cpp/tests/test_subprocess.cpp`

```cpp
#include <catch2/catch_test_macros.hpp>
#include <chrono>
#include <cstdlib>
#include <string>
#include "pareto_nbd/subprocess.hpp"

namespace {
std::string Py() { const char* p = std::getenv("PARETO_PYTHON"); return p ? p : "python"; }
}

TEST_CASE("RunWithTimeout reports exit codes", "[subprocess]") {
    auto ok = pareto_nbd::RunWithTimeout({Py(), "-c", "import sys; sys.exit(0)"}, 20);
    if (!ok.launched) { SKIP("python not launchable"); }
    REQUIRE_FALSE(ok.timed_out);
    REQUIRE(ok.exit_code == 0);
    auto bad = pareto_nbd::RunWithTimeout({Py(), "-c", "import sys; sys.exit(3)"}, 20);
    REQUIRE(bad.exit_code == 3);
}

TEST_CASE("RunWithTimeout kills a process that exceeds the timeout", "[subprocess]") {
    auto probe = pareto_nbd::RunWithTimeout({Py(), "-c", "pass"}, 20);
    if (!probe.launched) { SKIP("python not launchable"); }
    auto t0 = std::chrono::steady_clock::now();
    auto r = pareto_nbd::RunWithTimeout({Py(), "-c", "import time; time.sleep(60)"}, 1);
    auto secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    REQUIRE(r.launched);
    REQUIRE(r.timed_out);
    REQUIRE(secs < 15.0);
}

TEST_CASE("RunWithTimeout reports launched=false for a missing executable", "[subprocess]") {
    auto r = pareto_nbd::RunWithTimeout({"definitely-not-a-real-binary-xyz"}, 5);
    // POSIX fork succeeds then exec fails with 127, Windows CreateProcess fails outright.
    REQUIRE((!r.launched || r.exit_code == 127));
}

TEST_CASE("RunWithTimeout passes arguments containing spaces and quotes intact", "[subprocess]") {
    auto probe = pareto_nbd::RunWithTimeout({Py(), "-c", "pass"}, 20);
    if (!probe.launched) { SKIP("python not launchable"); }
    auto r = pareto_nbd::RunWithTimeout(
        {Py(), "-c", "import sys; sys.exit(0 if sys.argv[1] == 'a \"b\" c' else 9)", "a \"b\" c"}, 20);
    REQUIRE(r.exit_code == 0);
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cmake --build cpp/build --target unit_tests`
Expected: FAIL — `subprocess.hpp` not found.

- [ ] **Step 3: Implement**

`cpp/include/pareto_nbd/subprocess.hpp`:
```cpp
#pragma once
#include <string>
#include <vector>

namespace pareto_nbd {

struct SubprocessResult {
    bool launched = false;   // false: the process could not be started at all
    bool timed_out = false;  // true: killed after exceeding timeout_seconds
    int exit_code = -1;      // valid only when launched && !timed_out
};

// Runs argv[0] with argv[1..] (resolved via PATH), waits up to timeout_seconds, kills the
// process if it is still running, and reports what happened. stdout/stderr are inherited.
SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds);

}  // namespace pareto_nbd
```
`cpp/src/subprocess.cpp`:
```cpp
#include "pareto_nbd/subprocess.hpp"

#include <chrono>
#include <thread>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <csignal>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace pareto_nbd {

#ifdef _WIN32
namespace {
// Standard CommandLineToArgvW-compatible quoting.
std::string QuoteArg(const std::string& a) {
    std::string out = "\"";
    size_t bs = 0;
    for (char c : a) {
        if (c == '\\') {
            ++bs;
        } else if (c == '"') {
            out.append(bs * 2 + 1, '\\');
            out += '"';
            bs = 0;
        } else {
            out.append(bs, '\\');
            bs = 0;
            out += c;
        }
    }
    out.append(bs * 2, '\\');
    out += '"';
    return out;
}
}  // namespace

SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds) {
    SubprocessResult r;
    if (argv.empty()) return r;
    std::string cmd;
    for (const auto& a : argv) {
        if (!cmd.empty()) cmd += ' ';
        cmd += QuoteArg(a);
    }
    STARTUPINFOA si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    if (!CreateProcessA(nullptr, cmd.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr,
                        nullptr, &si, &pi)) {
        return r;
    }
    r.launched = true;
    DWORD w = WaitForSingleObject(pi.hProcess, static_cast<DWORD>(timeout_seconds) * 1000);
    if (w == WAIT_TIMEOUT) {
        TerminateProcess(pi.hProcess, 1);
        WaitForSingleObject(pi.hProcess, 5000);
        r.timed_out = true;
    } else {
        DWORD code = 0;
        GetExitCodeProcess(pi.hProcess, &code);
        r.exit_code = static_cast<int>(code);
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return r;
}
#else
SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds) {
    SubprocessResult r;
    if (argv.empty()) return r;
    std::vector<char*> args;
    for (const auto& a : argv) args.push_back(const_cast<char*>(a.c_str()));
    args.push_back(nullptr);
    pid_t pid = fork();
    if (pid < 0) return r;
    if (pid == 0) {
        execvp(args[0], args.data());
        _exit(127);
    }
    r.launched = true;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(timeout_seconds);
    int status = 0;
    while (true) {
        pid_t done = waitpid(pid, &status, WNOHANG);
        if (done == pid) {
            r.exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
            return r;
        }
        if (std::chrono::steady_clock::now() >= deadline) {
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            r.timed_out = true;
            return r;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}
#endif

}  // namespace pareto_nbd
```
CMake: add the two files.

- [ ] **Step 4: Run to verify it passes**

Run: `cmake --build cpp/build --target unit_tests && cpp/build/unit_tests "[subprocess]"`
Expected: 4 cases pass (or SKIP if no python on PATH).

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/subprocess.hpp cpp/src/subprocess.cpp cpp/tests/test_subprocess.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): RunWithTimeout -- cross-platform subprocess with kill-on-timeout"
```

---

### Task 4: McmcFit runner + worker integration

**Files:**
- Create: `cpp/include/pareto_nbd/mcmc_fit.hpp`, `cpp/src/mcmc_fit.cpp`, `cpp/tests/fixtures/fake_mcmc_cli.py`
- Modify: `cpp/src/worker.cpp` (`ProcessOneJobUnguarded`), `cpp/CMakeLists.txt` (add `src/mcmc_fit.cpp`; `target_compile_definitions(amortized_inference PRIVATE PROJECT_ROOT_DIR="${CMAKE_SOURCE_DIR}/..")`; add `tests/test_mcmc_fit.cpp`)
- Test: `cpp/tests/test_mcmc_fit.cpp`, extend `cpp/tests/test_worker.cpp`

**Interfaces:**
- Consumes: `RunWithTimeout` (Task 3), `ChooseFitMethod`/`ParseFitMode` (Task 2), `CustomerFeatures` (`ingest.hpp`), `ParetoNbdParams{r, alpha, s, beta}` (`forecast.hpp`), `UploadStorage::Put/GetPath/Exists`.
- Produces:
  ```cpp
  struct McmcFitResult {
      bool ok = false;
      ParetoNbdParams params{};
      std::string draws_key;   // storage key of the .npz, empty if none
      std::string note;        // user-facing reason when !ok
  };
  McmcFitResult RunMcmcFit(const std::string& job_id, const CustomerFeatures& cohort, UploadStorage& storage);
  ```
  Environment overrides: `PARETO_PYTHON` (default `python`), `PARETO_MCMC_CLI` (default `<PROJECT_ROOT_DIR>/src/mcmc_cli.py`), `PARETO_MCMC_TIMEOUT_S` (default `600`).

- [ ] **Step 1: Write the stub CLI and failing tests**

`cpp/tests/fixtures/fake_mcmc_cli.py` (mimics the real CLI contract without sampling):
```python
import argparse, json, sys, time

p = argparse.ArgumentParser()
p.add_argument("--cohort"); p.add_argument("--out"); p.add_argument("--draws")
p.add_argument("--n-draws"); p.add_argument("--burn-in"); p.add_argument("--thin"); p.add_argument("--seed")
a = p.parse_args()
if a.cohort.endswith("FAIL"):
    sys.exit(2)
open(a.draws, "wb").write(b"fake")
open(a.out, "w").write(json.dumps({"r": 0.7, "alpha": 11.0, "s": 0.6, "beta": 13.0,
                                    "n_keep": 1, "n_customers": 1, "elapsed_s": 0.0}))
```
`cpp/tests/test_mcmc_fit.cpp`:
```cpp
#include <catch2/catch_test_macros.hpp>
#include <cstdlib>
#include <string>
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/mcmc_fit.hpp"
#include "pareto_nbd/storage.hpp"

namespace {
void SetEnv(const char* k, const std::string& v) {
#ifdef _WIN32
    _putenv_s(k, v.c_str());
#else
    setenv(k, v.c_str(), 1);
#endif
}
pareto_nbd::CustomerFeatures TinyCohort() {
    pareto_nbd::CustomerFeatures c;
    c.customer_id = {"A", "B"};
    c.x = {3, 0};
    c.t_x = {10.5, 0};
    c.T_cal = {20, 20};
    return c;
}
const std::string kFake = std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/fake_mcmc_cli.py";
}  // namespace

TEST_CASE("RunMcmcFit returns posterior-mean params from the CLI", "[mcmc_fit]") {
    SetEnv("PARETO_MCMC_CLI", kFake);
    pareto_nbd::LocalDiskStorage storage("./data/test_mcmc_uploads");
    auto r = pareto_nbd::RunMcmcFit("job-ok", TinyCohort(), storage);
    if (!r.ok && r.note.find("could not start") != std::string::npos) { SKIP("python not launchable"); }
    REQUIRE(r.ok);
    REQUIRE(r.params.r == 0.7);
    REQUIRE(r.params.beta == 13.0);
    REQUIRE(r.draws_key == "mcmc/job-ok_draws.npz");
    REQUIRE(storage.Exists(r.draws_key));
}

TEST_CASE("RunMcmcFit reports a note instead of throwing when the CLI fails", "[mcmc_fit]") {
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/does_not_exist.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_mcmc_uploads");
    auto r = pareto_nbd::RunMcmcFit("job-bad", TinyCohort(), storage);
    REQUIRE_FALSE(r.ok);
    REQUIRE(r.note.rfind("High-precision refit unavailable", 0) == 0);
    SetEnv("PARETO_MCMC_CLI", kFake);
}

TEST_CASE("RunMcmcFit reports a timeout note", "[mcmc_fit]") {
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/sleepy_mcmc_cli.py");
    SetEnv("PARETO_MCMC_TIMEOUT_S", "1");
    pareto_nbd::LocalDiskStorage storage("./data/test_mcmc_uploads");
    auto r = pareto_nbd::RunMcmcFit("job-slow", TinyCohort(), storage);
    SetEnv("PARETO_MCMC_TIMEOUT_S", "600");
    SetEnv("PARETO_MCMC_CLI", kFake);
    REQUIRE_FALSE(r.ok);
    REQUIRE(r.note.find("timed out") != std::string::npos);
}
```
Also create `cpp/tests/fixtures/sleepy_mcmc_cli.py` containing `import time; time.sleep(60)`.

Append to `cpp/tests/test_worker.cpp` (insert helper `SetEnv` as above in an anonymous namespace at the top of the file, and `#include <cstdlib>`):
```cpp
namespace {
std::string InsertJob(drogon::orm::DbClientPtr db, const std::string& key, const std::string& mode) {
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path, fit_mode) "
        "VALUES ($1::uuid, 'queued', $2, $3) RETURNING id",
        pareto_nbd::kDefaultBusinessId, key, mode);
    return rows[0]["id"].as<std::string>();
}
const char* kSmallCsv = "customer_id,transaction_date,amount\n"
                         "A,2024-01-01,10.0\nA,2024-01-08,5.0\nA,2024-01-22,8.0\n"
                         "B,2024-01-01,3.0\nC,2024-01-15,20.0\nC,2024-01-29,6.0\n";
}  // namespace

TEST_CASE("fit_mode=mcmc uses the CLI's parameters and records fit_method", "[worker][mcmc]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/fake_mcmc_cli.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    storage.Put("uploads/mcmc-ok.csv", kSmallCsv);
    std::string job_id = InsertJob(db, "uploads/mcmc-ok.csv", "mcmc");

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto j = db->execSqlSync("SELECT status, fit_method, fit_note, mcmc_draws_path FROM jobs WHERE id=$1::uuid", job_id);
    REQUIRE(j[0]["status"].as<std::string>() == "done");
    if (j[0]["fit_method"].as<std::string>() != "mcmc") { SKIP("python not launchable"); }
    REQUIRE(j[0]["fit_note"].isNull());
    REQUIRE_FALSE(j[0]["mcmc_draws_path"].isNull());
    auto p = db->execSqlSync("SELECT model_params->>'r' AS r FROM forecast_results WHERE job_id=$1::uuid LIMIT 1", job_id);
    REQUIRE(std::stod(p[0]["r"].as<std::string>()) == 0.7);
}

TEST_CASE("fit_mode=mcmc falls back to the amortized fit with a note when the CLI fails", "[worker][mcmc]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/does_not_exist.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    storage.Put("uploads/mcmc-fail.csv", kSmallCsv);
    std::string job_id = InsertJob(db, "uploads/mcmc-fail.csv", "mcmc");

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto j = db->execSqlSync("SELECT status, fit_method, fit_note FROM jobs WHERE id=$1::uuid", job_id);
    REQUIRE(j[0]["status"].as<std::string>() == "done");
    REQUIRE(j[0]["fit_method"].as<std::string>() == "amortized");
    REQUIRE(j[0]["fit_note"].as<std::string>().rfind("High-precision refit unavailable", 0) == 0);
}

TEST_CASE("auto on a tiny cohort stays on the fast path without spawning Python", "[worker][mcmc]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    // A CLI path that would fail loudly if it were ever invoked.
    SetEnv("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/does_not_exist.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    storage.Put("uploads/auto-tiny.csv", kSmallCsv);
    std::string job_id = InsertJob(db, "uploads/auto-tiny.csv", "auto");

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto j = db->execSqlSync("SELECT fit_method, fit_note FROM jobs WHERE id=$1::uuid", job_id);
    REQUIRE(j[0]["fit_method"].as<std::string>() == "amortized");
    REQUIRE(j[0]["fit_note"].isNull());
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cmake --build cpp/build --target unit_tests`
Expected: FAIL — `mcmc_fit.hpp` not found.

- [ ] **Step 3: Implement**

`cpp/include/pareto_nbd/mcmc_fit.hpp`:
```cpp
#pragma once
#include <string>
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd {

struct McmcFitResult {
    bool ok = false;
    ParetoNbdParams params{};
    std::string draws_key;  // storage key of the saved posterior draws (.npz), empty if none
    std::string note;       // user-facing reason, set when !ok
};

// Fits Pareto/NBD with the Python Gibbs sampler (src/mcmc_cli.py) in a subprocess. Never
// throws for an MCMC-side problem (no Python, timeout, non-zero exit, unparsable or
// non-finite output): returns ok=false with a note so the caller can fall back to the
// amortized fit. Files live under storage keys mcmc/<job_id>_{cohort.csv,fit.json,draws.npz}.
// Env overrides: PARETO_PYTHON, PARETO_MCMC_CLI, PARETO_MCMC_TIMEOUT_S.
McmcFitResult RunMcmcFit(const std::string& job_id, const CustomerFeatures& cohort,
                         UploadStorage& storage);

}  // namespace pareto_nbd
```
`cpp/src/mcmc_fit.cpp`:
```cpp
#include "pareto_nbd/mcmc_fit.hpp"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <sstream>

#include "pareto_nbd/subprocess.hpp"

namespace pareto_nbd {
namespace {

std::string EnvOr(const char* name, const std::string& fallback) {
    const char* v = std::getenv(name);
    return (v && *v) ? std::string(v) : fallback;
}

McmcFitResult Unavailable(const std::string& reason) {
    McmcFitResult r;
    r.note = "High-precision refit unavailable (" + reason + ") - used the fast estimator instead.";
    return r;
}

}  // namespace

McmcFitResult RunMcmcFit(const std::string& job_id, const CustomerFeatures& cohort,
                         UploadStorage& storage) {
    try {
        std::ostringstream csv;
        csv << std::setprecision(17) << "x,t_x,T_cal\n";
        for (size_t i = 0; i < cohort.x.size(); ++i) {
            csv << cohort.x[i] << ',' << cohort.t_x[i] << ',' << cohort.T_cal[i] << '\n';
        }
        const std::string cohort_key = "mcmc/" + job_id + "_cohort.csv";
        const std::string fit_key = "mcmc/" + job_id + "_fit.json";
        const std::string draws_key = "mcmc/" + job_id + "_draws.npz";
        storage.Put(cohort_key, csv.str());

        const std::string py = EnvOr("PARETO_PYTHON", "python");
        const std::string cli =
            EnvOr("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/src/mcmc_cli.py");
        const int timeout = std::atoi(EnvOr("PARETO_MCMC_TIMEOUT_S", "600").c_str());

        auto res = RunWithTimeout({py, cli, "--cohort", storage.GetPath(cohort_key), "--out",
                                   storage.GetPath(fit_key), "--draws", storage.GetPath(draws_key)},
                                  timeout > 0 ? timeout : 600);
        if (!res.launched) return Unavailable("could not start Python");
        if (res.timed_out) return Unavailable("timed out after " + std::to_string(timeout) + " s");
        if (res.exit_code != 0) return Unavailable("sampler exited with code " + std::to_string(res.exit_code));
        if (!storage.Exists(fit_key)) return Unavailable("sampler produced no output");

        std::ifstream in(storage.GetPath(fit_key));
        auto j = nlohmann::json::parse(in);
        McmcFitResult out;
        out.params = ParetoNbdParams{j.at("r").get<double>(), j.at("alpha").get<double>(),
                                     j.at("s").get<double>(), j.at("beta").get<double>()};
        for (double v : {out.params.r, out.params.alpha, out.params.s, out.params.beta}) {
            if (!std::isfinite(v) || v <= 0.0) return Unavailable("sampler returned invalid parameters");
        }
        out.ok = true;
        if (storage.Exists(draws_key)) out.draws_key = draws_key;
        return out;
    } catch (const std::exception& e) {
        return Unavailable(std::string("internal error: ") + e.what());
    }
}

}  // namespace pareto_nbd
```
CMake: add `src/mcmc_fit.cpp`, `tests/test_mcmc_fit.cpp`, and the `PROJECT_ROOT_DIR` definition on `amortized_inference`.

`worker.cpp` — replace the body of `ProcessOneJobUnguarded` from the `SELECT upload_path` through the final `UPDATE`. Add includes `pareto_nbd/fit_policy.hpp`, `pareto_nbd/mcmc_fit.hpp`:
```cpp
    auto job_rows =
        db->execSqlSync("SELECT upload_path, fit_mode FROM jobs WHERE id = $1::uuid", job_id);
    if (job_rows.empty()) { return; }  // job vanished; nothing sensible to do
    std::string csv_path = storage.GetPath(job_rows[0]["upload_path"].as<std::string>());
    const FitMode mode =
        ParseFitMode(job_rows[0]["fit_mode"].as<std::string>()).value_or(FitMode::Auto);

    CustomerFeatures cohort;
    try {
        cohort = ingest_csv(csv_path);
    } catch (const IngestError& e) {
        MarkFailedBestEffort(db, job_id, e.what());
        return;
    }

    FitDecision decision = ChooseFitMethod(mode, cohort.x.size());
    std::string fit_method = "amortized";
    std::string fit_note = decision.note;
    std::string draws_key;
    ParetoNbdParams params{};
    bool have_params = false;

    if (decision.method == FitMethod::Mcmc) {
        McmcFitResult mcmc = RunMcmcFit(job_id, cohort, storage);
        if (mcmc.ok) {
            params = mcmc.params;
            have_params = true;
            fit_method = "mcmc";
            draws_key = mcmc.draws_key;
        } else {
            fit_note = mcmc.note;
        }
    }
    if (!have_params) {
        AmortizedModel model(std::string(PROJECT_MODELS_DIR) + "/amortizer_mlp.onnx",
                              std::string(PROJECT_MODELS_DIR) + "/amortizer_scalers.json");
        auto features = cohort_features(cohort.x, cohort.t_x, cohort.T_cal);
        auto amortized = model.predict(features);
        params = ParetoNbdParams{amortized.r, amortized.alpha, amortized.s, amortized.beta};
    }

    ScoreCohortAndWriteResults(job_id, db, cohort, params);

    db->execSqlSync(
        "UPDATE jobs SET status = 'done', completed_at = now(), fit_method = $2, "
        "fit_note = NULLIF($3, ''), mcmc_draws_path = NULLIF($4, '') WHERE id = $1::uuid",
        job_id, fit_method, fit_note, draws_key);
```
(Keep the existing comment about the models directory above the `AmortizedModel` line.)

- [ ] **Step 4: Run to verify it passes**

Run:
```
cmake --build cpp/build --target unit_tests worker api_server
docker compose up -d
cpp/build/unit_tests "[mcmc_fit],[worker]"
```
Expected: all pass (MCMC cases SKIP cleanly if Python is not on PATH). Then run the full `cpp/build/unit_tests` to confirm no regressions.

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/mcmc_fit.hpp cpp/src/mcmc_fit.cpp cpp/src/worker.cpp cpp/tests cpp/CMakeLists.txt
git commit -m "feat(cpp): worker runs the MCMC subprocess per fit_mode, falling back to the amortized fit"
```

---

### Task 5: API — `fit_mode` on upload, `POST /jobs/{id}/refit`, fit fields on `GET /jobs/{id}`

**Files:**
- Modify: `cpp/src/api_routes.cpp` (`/uploads` handler ~l.160–210, `/jobs/{id}` ~l.215–240; add `/jobs/{id}/refit`)
- Test: extend `cpp/tests/test_uploads_endpoint.cpp`, `cpp/tests/test_jobs_endpoint.cpp`; create `cpp/tests/test_refit_endpoint.cpp` (add to CMake)

**Interfaces:**
- Consumes: `ParseFitMode`, `ToString` (Task 2); existing `EnqueueJob`, `JsonResponse`, `IsValidUuidFormat`.
- Produces: `POST /uploads?fit_mode=auto|fast|mcmc` (default `auto`; invalid → 400 `{"error":"fit_mode must be one of: auto, fast, mcmc"}`). `POST /jobs/{id}/refit` → 200 `{"job_id": <new>}`; 400 bad id; 404 unknown; 409 `{"error":"only a finished job can be refit"}` unless status `done`; 503 like `/uploads` on enqueue failure. `GET /jobs/{id}` adds `fit_mode, fit_method (nullable), fit_note (nullable), source_job_id (nullable)`.

- [ ] **Step 1: Write failing tests**

Add to `cpp/tests/test_jobs_endpoint.cpp` (after the first TEST_CASE):
```cpp
TEST_CASE("GET /jobs/{id} includes the fit fields", "[api][jobs]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path, fit_mode, fit_method, fit_note) "
        "VALUES ($1::uuid, 'done', 'x', 'mcmc', 'amortized', 'fell back') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    auto body = nlohmann::json::parse(GetJob(rows[0]["id"].as<std::string>())->getBody());
    REQUIRE(body["fit_mode"] == "mcmc");
    REQUIRE(body["fit_method"] == "amortized");
    REQUIRE(body["fit_note"] == "fell back");
    REQUIRE(body["source_job_id"].is_null());
}
```
`cpp/tests/test_refit_endpoint.cpp`:
```cpp
#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>
#include <string>
#include "pareto_nbd/db.hpp"
#include "test_server_fixture.hpp"

namespace {
drogon::HttpResponsePtr PostRefit(const std::string& id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/jobs/" + id + "/refit");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}
std::string InsertJob(drogon::orm::DbClientPtr db, const std::string& status) {
    return db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, $2, 'uploads/x.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId, status)[0]["id"].as<std::string>();
}
}  // namespace

TEST_CASE("POST /jobs/{id}/refit queues an mcmc job linked to the source", "[api][refit]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    std::string src = InsertJob(db, "done");

    auto resp = PostRefit(src);
    if (resp->getStatusCode() == drogon::k503ServiceUnavailable) { SKIP("Redis not reachable"); }
    REQUIRE(resp->getStatusCode() == drogon::k200OK);
    std::string new_id = nlohmann::json::parse(resp->getBody())["job_id"];
    REQUIRE(new_id != src);

    auto row = db->execSqlSync(
        "SELECT status, fit_mode, source_job_id::text AS src, upload_path FROM jobs WHERE id=$1::uuid", new_id);
    REQUIRE(row[0]["status"].as<std::string>() == "queued");
    REQUIRE(row[0]["fit_mode"].as<std::string>() == "mcmc");
    REQUIRE(row[0]["src"].as<std::string>() == src);
    REQUIRE(row[0]["upload_path"].as<std::string>() == "uploads/x.csv");
}

TEST_CASE("POST /jobs/{id}/refit rejects bad, unknown and unfinished jobs", "[api][refit]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    REQUIRE(PostRefit("not-a-uuid")->getStatusCode() == drogon::k400BadRequest);
    REQUIRE(PostRefit("00000000-0000-0000-0000-000000000099")->getStatusCode() == drogon::k404NotFound);
    for (const char* st : {"queued", "running", "failed"}) {
        REQUIRE(PostRefit(InsertJob(db, st))->getStatusCode() == drogon::k409Conflict);
    }
}
```
Add to `cpp/tests/test_uploads_endpoint.cpp`, following that file's existing upload helper (read it first; it posts a CSV body via `drogon::HttpClient`): one case posting a valid CSV to `/uploads?fit_mode=fast` and asserting the new job row has `fit_mode='fast'`; one posting to `/uploads?fit_mode=bogus` asserting `400` and error text `fit_mode must be one of: auto, fast, mcmc`; one with no param asserting `fit_mode='auto'`. For the query, call `req->setPath("/uploads")` then `req->setParameter("fit_mode", "fast")` (Drogon appends parameters to the query on POST when a body is set via `setBody`; if the existing helper cannot, use `setPath("/uploads?fit_mode=fast")`).

- [ ] **Step 2: Run to verify it fails**

Run: `cmake --build cpp/build --target unit_tests && cpp/build/unit_tests "[api]"`
Expected: new cases FAIL (404 for `/refit`, missing JSON fields, `fit_mode` column ignored).

- [ ] **Step 3: Implement** in `cpp/src/api_routes.cpp`

(a) `#include "pareto_nbd/fit_policy.hpp"` at the top.

(b) Factor the enqueue-or-mark-failed block out of `/uploads` into a file-local helper (used by both routes), placed in the existing anonymous namespace:
```cpp
// Pushes job_id to the queue. On failure marks the already-inserted row failed (so GET
// /jobs/{id} tells the truth) and returns the 503 response to send, else nullptr.
drogon::HttpResponsePtr EnqueueOrFailResponse(drogon::orm::DbClientPtr db,
                                               drogon::nosql::RedisClientPtr redis,
                                               const std::string& queue_key,
                                               const std::string& job_id) {
    if (pareto_nbd::EnqueueJob(redis, job_id, queue_key)) return nullptr;
    db->execSqlSync(
        "UPDATE jobs SET status = 'failed', error_reason = $2, completed_at = now() "
        "WHERE id = $1::uuid",
        job_id, std::string("could not enqueue job for processing (queue unavailable)"));
    return JsonResponse({{"error", "job queue unavailable, please retry"}, {"job_id", job_id}},
                        drogon::k503ServiceUnavailable);
}
```
(c) In `/uploads`, right after the empty-body check:
```cpp
            std::string mode_str = req->getParameter("fit_mode");
            if (mode_str.empty()) mode_str = "auto";
            auto mode = pareto_nbd::ParseFitMode(mode_str);
            if (!mode) {
                callback(JsonResponse({{"error", "fit_mode must be one of: auto, fast, mcmc"}},
                                       drogon::k400BadRequest));
                return;
            }
```
change the INSERT to
```cpp
                "INSERT INTO jobs (business_id, status, upload_path, fit_mode) "
                "VALUES ($1::uuid, 'queued', $2, $3) RETURNING id",
                pareto_nbd::kDefaultBusinessId, key, pareto_nbd::ToString(*mode));
```
and replace the enqueue block with `if (auto fail = EnqueueOrFailResponse(db, redis, queue_key, job_id)) { callback(fail); return; }`.

(d) `/jobs/{id}`: change the SELECT to `SELECT status, error_reason, fit_mode, fit_method, fit_note, source_job_id::text AS source_job_id FROM jobs WHERE id = $1::uuid` and add after `error_reason`:
```cpp
            auto nullable = [&](const char* col) {
                return rows[0][col].isNull() ? nlohmann::json(nullptr)
                                             : nlohmann::json(rows[0][col].as<std::string>());
            };
            body["fit_mode"] = rows[0]["fit_mode"].as<std::string>();
            body["fit_method"] = nullable("fit_method");
            body["fit_note"] = nullable("fit_note");
            body["source_job_id"] = nullable("source_job_id");
```
(e) New route (register after `/jobs/{id}`):
```cpp
    drogon::app().registerHandler(
        "/jobs/{id}/refit",
        [db, redis, queue_key](const drogon::HttpRequestPtr&,
                               std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                               const std::string& id) {
            if (!IsValidUuidFormat(id)) {
                callback(JsonResponse({{"error", "invalid job id format"}}, drogon::k400BadRequest));
                return;
            }
            auto rows = db->execSqlSync(
                "SELECT status, upload_path FROM jobs WHERE id = $1::uuid", id);
            if (rows.empty()) {
                callback(JsonResponse({{"error", "job not found"}}, drogon::k404NotFound));
                return;
            }
            if (rows[0]["status"].as<std::string>() != "done") {
                callback(JsonResponse({{"error", "only a finished job can be refit"}},
                                       drogon::k409Conflict));
                return;
            }
            auto ins = db->execSqlSync(
                "INSERT INTO jobs (business_id, status, upload_path, fit_mode, source_job_id) "
                "VALUES ($1::uuid, 'queued', $2, 'mcmc', $3::uuid) RETURNING id",
                pareto_nbd::kDefaultBusinessId, rows[0]["upload_path"].as<std::string>(), id);
            std::string new_id = ins[0]["id"].as<std::string>();
            if (auto fail = EnqueueOrFailResponse(db, redis, queue_key, new_id)) {
                callback(fail);
                return;
            }
            callback(JsonResponse({{"job_id", new_id}}, drogon::k200OK));
        },
        {drogon::Post});
```
CMake: add `tests/test_refit_endpoint.cpp`.

- [ ] **Step 4: Run to verify it passes**

Run: `cmake --build cpp/build --target unit_tests worker api_server && cpp/build/unit_tests "[api]"` (Postgres + Redis up)
Expected: all `[api]` cases pass, including pre-existing upload/job/results/summary/export cases.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_routes.cpp cpp/tests cpp/CMakeLists.txt
git commit -m "feat(cpp): fit_mode on upload, POST /jobs/{id}/refit, fit fields on GET /jobs/{id}"
```

---

### Task 6: Frontend — mode selector, fit badge, refit button

**Files:**
- Modify: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/routes/+page.svelte`, `frontend/src/routes/jobs/[id]/+page.svelte`
- Test: `frontend/tests/api.test.ts`, `frontend/tests/upload-page.test.ts`, `frontend/tests/job-page.test.ts`

**Interfaces:**
- Consumes: Task 5 endpoints.
- Produces: `FitMode = 'auto'|'fast'|'mcmc'`, `FitMethod = 'amortized'|'mcmc'`; `JobInfo` gains `fit_mode, fit_method, fit_note, source_job_id`; `api.uploadCsv(file, fitMode = 'auto')`; `api.refitJob(id) -> {job_id}`.

- [ ] **Step 1: Write failing tests**

`frontend/tests/api.test.ts` — add:
```ts
  it('sends the chosen fit mode as a query parameter', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'job-1' }));
    await createApi(fetchFn).uploadCsv(new File(['x'], 'a.csv'), 'mcmc');
    expect((fetchFn.mock.calls[0] as unknown as [string])[0]).toBe('/api/uploads?fit_mode=mcmc');
  });

  it('refitJob POSTs to the refit endpoint', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'job-2' }));
    const out = await createApi(fetchFn).refitJob('job-1');
    expect(out).toEqual({ job_id: 'job-2' });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/jobs/job-1/refit');
    expect(init.method).toBe('POST');
  });
```
(The existing first test expects `'/api/uploads'`: update it to `'/api/uploads?fit_mode=auto'`.)

`frontend/tests/upload-page.test.ts` — add:
```ts
  it('defaults to auto and passes a changed precision mode to the upload', async () => {
    uploadCsv.mockResolvedValue({ job_id: 'job-7' });
    render(Page);
    await pick(new File(['customer_id,transaction_date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    const select = (await screen.findByLabelText(/precision/i)) as HTMLSelectElement;
    expect(select.value).toBe('auto');
    await fireEvent.change(select, { target: { value: 'mcmc' } });
    await fireEvent.click(await screen.findByRole('button', { name: /forecast/i }));
    await waitFor(() => expect(uploadCsv).toHaveBeenCalledWith(expect.any(File), 'mcmc'));
  });
```
Also update the first test's expectations only if it asserts call args (it does not).

`frontend/tests/job-page.test.ts` — add `refitJob` mock alongside `getJob` in the `vi.mock` block (`refitJob: (...a: unknown[]) => refitJob(...a)`, with `const refitJob = vi.fn();` and `refitJob.mockReset()` in `beforeEach`, and mock `$app/navigation` as in the upload test: `const goto = vi.fn(); vi.mock('$app/navigation', () => ({ goto: (...a: unknown[]) => goto(...a) }));`), then:
```ts
  const done = (over = {}) => ({ id: 'job-1', status: 'done', error_reason: null, fit_mode: 'auto',
    fit_method: 'amortized', fit_note: null, source_job_id: null, ...over });

  it('offers a high-precision refit on a fast-fitted job and navigates to the new job', async () => {
    getJob.mockResolvedValue(done());
    refitJob.mockResolvedValue({ job_id: 'job-9' });
    render(Page);
    await fireEvent.click(await screen.findByRole('button', { name: /refit.*mcmc|high-precision/i }));
    await waitFor(() => expect(goto).toHaveBeenCalledWith('/jobs/job-9'));
  });

  it('shows the method used, hides the refit button for an MCMC fit, and surfaces a fallback note', async () => {
    getJob.mockResolvedValue(done({ fit_method: 'mcmc' }));
    render(Page);
    expect(await screen.findByText(/high-precision \(mcmc\)/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /high-precision/i })).toBeNull();
  });

  it('shows the fallback note when the refit could not run', async () => {
    getJob.mockResolvedValue(done({ fit_note: 'High-precision refit unavailable (timed out after 600 s) - used the fast estimator instead.' }));
    render(Page);
    expect(await screen.findByText(/timed out after 600 s/i)).toBeInTheDocument();
  });
```
(import `fireEvent` from `@testing-library/svelte`.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm test -- --maxWorkers=2`
Expected: new/changed tests FAIL.

- [ ] **Step 3: Implement**

`types.ts`:
```ts
export type FitMode = 'auto' | 'fast' | 'mcmc';
export type FitMethod = 'amortized' | 'mcmc';

export interface JobInfo {
  id: string;
  status: JobStatus;
  error_reason: string | null;
  fit_mode: FitMode;
  fit_method: FitMethod | null;
  fit_note: string | null;
  source_job_id: string | null;
}
```
`api.ts` (import `FitMode`):
```ts
    uploadCsv: (file: File, fitMode: FitMode = 'auto') =>
      call<{ job_id: string }>(`/api/uploads?fit_mode=${fitMode}`, {
        method: 'POST',
        headers: { 'content-type': 'text/csv' },
        body: file
      }),
    refitJob: (id: string) =>
      call<{ job_id: string }>(`/api/jobs/${encodeURIComponent(id)}/refit`, { method: 'POST' }),
```
`routes/+page.svelte` — add `import type { FitMode } from '$lib/types';`, `let fitMode = $state<FitMode>('auto');`, call `api.uploadCsv(file, fitMode)`, and inside `{#if file}` before the button:
```svelte
    <label class="precision">
      Precision
      <select bind:value={fitMode} disabled={busy}>
        <option value="auto">Automatic (high-precision for small cohorts)</option>
        <option value="fast">Fast</option>
        <option value="mcmc">High-precision (MCMC, slower)</option>
      </select>
    </label>
```
with a small `.precision { display:block; margin: 0.75rem 0; }` style.

`routes/jobs/[id]/+page.svelte` — add `import { goto } from '$app/navigation';`, state `let refitting = $state(false); let refitError = $state('');`, and:
```ts
  async function refit() {
    refitting = true;
    refitError = '';
    try {
      const { job_id } = await api.refitJob(id);
      await goto(`/jobs/${job_id}`);
    } catch (e) {
      refitError = e instanceof ApiError ? e.message : 'Could not start the refit';
    } finally {
      refitting = false;
    }
  }
```
In the done branch, between `<h1>` and `<Dashboard>`:
```svelte
    <p class="fit" data-testid="fit-info">
      Fitted with: <strong>{job.fit_method === 'mcmc' ? 'High-precision (MCMC)' : 'Fast estimator'}</strong>
      {#if job.fit_method !== 'mcmc'}
        <button onclick={refit} disabled={refitting}>
          {refitting ? 'Starting…' : 'Refit with high-precision MCMC'}
        </button>
      {/if}
    </p>
    {#if job.fit_note}<p class="note">{job.fit_note}</p>{/if}
    {#if refitError}<p role="alert">{refitError}</p>{/if}
```
Reuse the upload page's button/`.note` styles (copy the small rules into this page's `<style>`). Note: a failed MCMC refit shows its `fit_note` and, because `fit_method` is `amortized`, still offers the button, which is the desired retry.

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm test -- --maxWorkers=2 && npm run check`
Expected: all tests pass, 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/tests
git commit -m "feat(frontend): precision selector, fit-method badge and high-precision refit button"
```

---

### Task 7: Live smoke + docs

**Files:**
- Modify: `frontend/scripts/smoke.mjs` (add an MCMC leg), `docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md` (§9 item 6 → built), `CHANGELOG.md` (dated entry), the frontend plan's "Execution notes" if relevant.

- [ ] **Step 1:** Read `frontend/scripts/smoke.mjs` and add a leg: upload the same ~1,500-customer CSV with `?fit_mode=fast`, assert `fit_method === 'amortized'`; POST `/api/jobs/{id}/refit`, poll the new job to `done`, assert `fit_method === 'mcmc'` and `source_job_id` equals the first job. (1,525 customers is above the 50-customer floor, so `auto` would also pick MCMC; assert that on a third upload with no param.)
- [ ] **Step 2:** Run it live: `docker compose up -d`, start `api_server` and `worker` from the same cwd (built via `vcvars64.bat`), then `node frontend/scripts/smoke.mjs`. Expected: all legs pass; record the MCMC wall-clock time in the CHANGELOG (it sets whether `kAutoMcmcMaxCustomers = 2000` is a sensible default; adjust the constant and its test if the measured time is not "quick").
- [ ] **Step 3:** Update the spec (§9.6 and the §4.3 "Explicitly deferred" paragraph: the Python-subprocess path now exists, the native C++ port still deferred) and add a CHANGELOG entry listing the three triggers, the fallback rule, the env vars, and the saved draws.
- [ ] **Step 4: Commit**

```bash
git add frontend/scripts/smoke.mjs docs CHANGELOG.md
git commit -m "docs+smoke: MCMC high-precision path, live-verified"
```

---

## Self-Review

- **Spec coverage:** §9.6 "optional Python-subprocess MCMC" → Tasks 1, 3, 4; "optional" and non-blocking → fallback in Task 4; user's "all three triggers" → per-upload mode (Task 5/6), automatic (Task 2), refit button (Task 5/6); "keep draws" → `.npz` + `mcmc_draws_path` (Tasks 1, 4).
- **Placeholders:** none. The one "read the file first" instruction (Task 5, `test_uploads_endpoint.cpp` helper, and Task 7 `smoke.mjs`) names the exact assertions to add; those two files were not opened while planning.
- **Type consistency:** `FitMode/ParseFitMode/ToString/ChooseFitMethod` (Task 2) are used verbatim in Tasks 4 and 5; `RunWithTimeout`/`SubprocessResult` (Task 3) used verbatim in Task 4; `McmcFitResult` fields match between header, implementation and worker; JSON field names `fit_mode, fit_method, fit_note, source_job_id` match between SQL, API, `types.ts` and tests; `uploadCsv(file, fitMode)` matches page and tests.
- **Known limits (intentionally out of scope):** the draws are saved but nothing consumes them yet (that is the conformal-interval work); convergence diagnostics (split-R̂) are not surfaced; no progress reporting during the sampler run; the `.npz` is not cleaned up.
