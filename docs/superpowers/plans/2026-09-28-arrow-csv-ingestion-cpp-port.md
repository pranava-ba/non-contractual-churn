# Arrow CSV Ingestion + RFM Feature Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Given a raw transaction-log CSV (`customer_id, transaction_date,
[amount]`), produce the per-customer BTYD + monetary summary
(`x`, `t_x`, `T_cal`, `m_bar`) that feeds the already-built C++ pipeline
(`cohort_features` → `AmortizedModel` → Gamma-Gamma `CLV`), using Apache
Arrow C++ for the scale-sensitive parse/sort step, validated by golden-file
tests against a new Python reference implementation.

**Architecture:** The research codebase's existing transaction-log summarizers
([src/empirical.py](../../../src/empirical.py)'s `elog_to_summary`,
[src/clv_data.py](../../../src/clv_data.py)'s `clv_summary`) are
backtesting tools: they split a log into a fixed calibration window plus a
forecast holdout to score against a *known* future. Production ingestion has
no known future — it needs the whole log as calibration, "now" being
whatever date the upload was taken as of. That production variant doesn't
exist yet in Python, so this plan first adds it
(`src/ingest.py::elog_to_features`) as the oracle for the C++ port, sharing
the same date-merging/weeks-since-acquisition conventions as the existing
research code (cross-checked against `elog_to_summary` directly, Task 1)
before anything is ported to C++.

The C++ side (`cpp/src/ingest.cpp`) uses Arrow's CSV reader for parsing
(handles quoting, type inference, and scale — hundreds of thousands of
rows) and Arrow's `SortIndices`/`Take` compute functions to group rows by
customer (sort by `customer_id`, then `transaction_date`; same-customer rows
become adjacent). The actual per-customer rolling statistics (first/last
date, repeat count, summed same-day spend) are **not** expressed as an
Arrow group-by/aggregate node: Arrow's `Aggregate` compute API is built for
reductions like sum/count/mean per group, not an ordered multi-field scan
that needs "first date," "last date," and "count after the first," so a
single linear pass over the Arrow-sorted table is simpler and just as fast
as wiring a custom Acero aggregation kernel would be. This mirrors the
tradeoff already made for `fit_gamma_gamma` in Phase 2 (hand-written
Nelder-Mead over pulling in a heavier optimization library) — use Arrow for
what it's uniquely good at (robust, scalable parsing + sorting), write the
small amount of custom logic directly.

**Tech Stack:** Python (pandas, existing repo deps) for the reference
implementation/golden-file generation; C++20, Apache Arrow C++ (CSV +
compute components, via vcpkg), continuing the existing `cpp/` CMake+vcpkg
project (Catch2, nlohmann/json, ONNX Runtime already wired from Phases 1–2).

**Spec:** [docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md](../specs/2026-09-26-clv-forecasting-saas-design.md)
— this plan implements Phase 3 of that spec's §9 phased build order
("Arrow-based CSV ingestion + RFM feature extraction, validated against the
existing Python feature computation"). Phase 4 (Drogon API: upload →
validate → enqueue → worker → Postgres) is a separate plan, written after
this one lands, and is the first phase that actually calls `ingest_csv` from
a live request path — this plan only has to prove the ingestion pipeline is
correct and wired into the existing `cohort_features`/`AmortizedModel`/`CLV`
chain via the `main.cpp` demo.

## Global Constraints

- Continue the conventions already established in `cpp/`: C++20, CMake
  (>=3.25) + vcpkg manifest mode, Release build by default (see the existing
  `CMakeLists.txt` comment on the onnxruntime/onnx Debug-build assertion —
  unrelated to this plan, but don't disturb it), `PROJECT_MODELS_DIR`
  compile definition pointing at `cpp/../models` for both `main` and
  `unit_tests`.
- New vcpkg dependency: `arrow`, with features `["csv", "compute"]` added to
  `cpp/vcpkg.json`'s `dependencies` list (as an object with a `features`
  array, not a bare string, to opt into those two components — Arrow's
  default vcpkg build does not include the CSV reader). This is
  substantially the heaviest dependency in the project so far (bigger than
  onnxruntime); expect the first `cmake --preset default` after adding it to
  take a long time as vcpkg builds it from source. Do this in its own task
  (Task 3) with nothing else changed, so a slow/failed build is easy to
  isolate.
- Arrow's C++ CMake target name depends on the vcpkg triplet (dynamic vs
  static): typically `Arrow::arrow_shared` or `Arrow::arrow_static`. If
  `target_link_libraries` fails to find the target name used below, run
  `cmake --preset default` and check the generated
  `build/vcpkg_installed/<triplet>/share/arrow/ArrowConfig.cmake` (or the
  configure log's exported-targets list) for the actual name and adjust.
- Arrow's CSV/compute C++ API has shifted across versions (e.g.
  `TableReader::Make`'s exact parameter list, `SortKey`'s constructor
  argument order, whether `arrow::Result<T>` needs `.ValueOrDie()` vs
  structured binding via `ARROW_ASSIGN_OR_RAISE`). The code below targets a
  recent (14+) API; check the installed version's headers under
  `build/vcpkg_installed/<triplet>/include/arrow/` if it doesn't compile as
  written and adjust.
- Dates: only calendar-day granularity is supported, matching the Python
  reference's `.values.astype("datetime64[D]")` truncation (any time-of-day
  component in `transaction_date` is dropped, not rounded). Internally, both
  the Python and C++ implementations reduce every date to an integer
  "days since epoch" before doing week arithmetic.
- Customer IDs are treated as opaque strings end-to-end in both the Python
  reference and the C++ port, even when the CSV contains numeric IDs — this
  avoids precision loss on large integer IDs and matches how the eventual
  product keys customers (`customers.external_customer_id TEXT`, per the
  spec's §4.4.1 schema).
- Numeric tolerance: unlike Phase 2's `fit_gamma_gamma` (an MLE fit with a
  necessarily loose tolerance), everything in this plan is exact arithmetic
  (integer day-count subtraction divided by 7). Golden-file comparisons use
  a tight tolerance (relative `1e-9`), the same as Phase 1's
  `moments_to_gamma`/`cohort_features`.
- `m_bar` (average spend per repeat transaction) for a customer with `x=0`
  (no repeat purchases) is defined as `0.0` in both implementations. This
  value is never actually consumed downstream: `fit_gamma_gamma` and the
  rest of the CLV pipeline (see `cpp/include/pareto_nbd/clv.hpp`) already
  filter to `x>0` customers internally, so `0.0` here is just a safe,
  unambiguous placeholder rather than a meaningful estimate.

---

### Task 1: Python reference implementation — `elog_to_features`

**Files:**
- Create: `src/ingest.py`
- Test: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `WEEK` from [src/empirical.py](../../../src/empirical.py)
  (existing); `elog_to_summary` from the same module, used only by this
  task's consistency test, not by `elog_to_features` itself.
- Produces: `elog_to_features(elog: pd.DataFrame, as_of: pd.Timestamp | None
  = None) -> pd.DataFrame`, returning columns `cust, x, t_x, T_cal[, m_bar]`
  — the `m_bar` column is present iff the input `elog` has a `spend` column.
  This is the oracle Task 2's golden-file export script calls, and the
  contract the C++ `ingest_csv` (Tasks 3–7) must reproduce.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ingest.py
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingest import elog_to_features  # noqa: E402
from empirical import elog_to_summary  # noqa: E402


def _toy_elog(with_spend: bool = False) -> pd.DataFrame:
    # cust 1: acquisition + a same-day duplicate on 01-08 + a repeat on 01-22
    #   (gaps are exact multiples of 7 days so weeks are hand-checkable)
    # cust 2: a single transaction (no repeats -> x=0)
    rows = [
        (1, "2024-01-01", 10.0),
        (1, "2024-01-08", 5.0),
        (1, "2024-01-08", 5.0),   # same-day duplicate: merges into the row above
        (1, "2024-01-22", 8.0),
        (2, "2024-01-01", 3.0),
    ]
    df = pd.DataFrame(rows, columns=["cust", "date", "spend"])
    df["date"] = pd.to_datetime(df["date"])
    if not with_spend:
        df = df.drop(columns=["spend"])
    return df


def test_elog_to_features_basic_counts_and_recency():
    out = elog_to_features(_toy_elog()).set_index("cust")
    assert set(out.columns) == {"x", "t_x", "T_cal"}

    # cust 1: 3 unique dates after same-day dedup -> acquisition + 2 repeats
    assert out.loc[1, "x"] == 2
    assert out.loc[1, "t_x"] == 3.0        # (01-22 - 01-01) / 7 weeks
    assert out.loc[1, "T_cal"] == 3.0      # as_of defaults to the log's max date (01-22)

    # cust 2: single transaction -> no repeats
    assert out.loc[2, "x"] == 0
    assert out.loc[2, "t_x"] == 0.0
    assert out.loc[2, "T_cal"] == 3.0      # still measured to the log-wide max date


def test_elog_to_features_monetary_column():
    out = elog_to_features(_toy_elog(with_spend=True)).set_index("cust")
    assert "m_bar" in out.columns
    # cust 1's repeats: day 01-08 (5+5 same-day dedup summed = 10), day 01-22 (8)
    assert out.loc[1, "m_bar"] == 9.0       # mean([10, 8])
    assert out.loc[2, "m_bar"] == 0.0       # x=0 placeholder


def test_elog_to_features_explicit_as_of():
    out = elog_to_features(_toy_elog(), as_of=pd.Timestamp("2024-01-15")).set_index("cust")
    assert out.loc[1, "T_cal"] == 2.0       # (01-15 - 01-01) / 7
    assert out.loc[1, "x"] == 1             # only the 01-08 repeat is <= as_of... 
    # ...wait: elog_to_features does not filter repeats by as_of (see note in
    # Step 3) -- this asserts the documented behavior instead:


def test_elog_to_features_matches_elog_to_summary_calibration_side():
    # elog_to_summary's calibration-window math (x, t_x, T_cal) is already
    # validated research code; when elog_to_features's as_of is set to the
    # exact same cal_end, the two must agree on every shared customer.
    elog = _toy_elog()
    t0 = elog["date"].min()
    cal_weeks = 3
    cal_end = t0 + cal_weeks * np.timedelta64(7, "D")

    a = elog_to_features(elog, as_of=cal_end).set_index("cust")[["x", "t_x", "T_cal"]]
    b = elog_to_summary(elog, cal_weeks=cal_weeks, horizon=1).set_index("cust")[["x", "t_x", "T_cal"]]

    pd.testing.assert_frame_equal(a.sort_index(), b.sort_index())
```

Before finishing Step 1, resolve the `test_elog_to_features_explicit_as_of`
comment above by deciding (and asserting) the real behavior: `x` counts
**all** repeat purchases in the log regardless of `as_of`, or only those
`<= as_of`? The correct choice is **only those `<= as_of`** — `as_of` means
"pretend today is this date," so a repeat purchase that (in the fixture)
happens to be logged but is in the future relative to `as_of` must not count
as observed history. Rewrite the test body to:

```python
def test_elog_to_features_explicit_as_of():
    out = elog_to_features(_toy_elog(), as_of=pd.Timestamp("2024-01-15")).set_index("cust")
    assert out.loc[1, "T_cal"] == 2.0       # (01-15 - 01-01) / 7
    assert out.loc[1, "x"] == 1             # only the 01-08 repeat is <= as_of
    assert out.loc[1, "t_x"] == 1.0         # (01-08 - 01-01) / 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingest'`

- [ ] **Step 3: Write the implementation**

```python
# src/ingest.py
"""Production analog of empirical.elog_to_summary / clv_data.clv_summary for
the live app: given a raw transaction log, compute per-customer BTYD +
monetary features as of "now" (or an explicit as_of date), with no
forecast-horizon holdout split -- production has no known future to hold
out. This is the Python oracle that src/export_ingest_golden.py snapshots
and cpp/src/ingest.cpp is cross-checked against."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import WEEK  # noqa: E402


def elog_to_features(elog: pd.DataFrame, as_of: "pd.Timestamp | None" = None) -> pd.DataFrame:
    """elog has columns cust, date[, spend]. Same-day purchases per customer
    are merged (date-only dedup; spend summed if present -- matches
    empirical.elog_to_summary / clv_data._to_txn's same-day-merge
    convention). as_of defaults to the log's own max date ("now" = the
    last-seen transaction); only transactions with date <= as_of count as
    observed history, so a caller can also use this to reconstruct what the
    features would have looked like at an earlier point in time."""
    elog = elog.copy()
    elog["date"] = elog["date"].values.astype("datetime64[D]")
    has_spend = "spend" in elog.columns
    if has_spend:
        elog = elog.groupby(["cust", "date"], as_index=False)["spend"].sum()
    else:
        elog = elog.drop_duplicates(["cust", "date"])

    cal_end = np.datetime64(as_of) if as_of is not None else elog["date"].max()
    elog = elog[elog["date"] <= cal_end]

    rows = []
    for cust, g in elog.groupby("cust"):
        g = g.sort_values("date")
        dates = g["date"].values
        acq = dates[0]
        rep = dates[1:]
        x = len(rep)
        t_x = float((rep[-1] - acq) / WEEK) if x > 0 else 0.0
        T_cal = float((cal_end - acq) / WEEK)
        row = {"cust": cust, "x": x, "t_x": t_x, "T_cal": T_cal}
        if has_spend:
            rep_spend = g["spend"].values[1:]
            row["m_bar"] = float(rep_spend.mean()) if x > 0 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingest.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ingest.py tests/test_ingest.py
git commit -m "feat: add elog_to_features, the production (no-holdout) BTYD feature summary"
```

---

### Task 2: Golden-file fixtures — sample CSVs + expected JSON

**Files:**
- Create: `src/export_ingest_golden.py`
- Create (generated, then committed): `models/ingest_sample.csv`,
  `models/ingest_golden.json`, `models/ingest_golden_as_of.json`,
  `models/ingest_sample_no_money.csv`, `models/ingest_golden_no_money.json`

**Interfaces:**
- Consumes: `elog_to_features` (Task 1).
- Produces: the five committed fixtures above, consumed by the C++
  golden-file tests in Tasks 5–7. `ingest_golden.json` and
  `ingest_golden_no_money.json` are `{"as_of": null, "customers": [{"cust":
  str, "x": float, "t_x": float, "T_cal": float, "m_bar": float | null},
  ...]}`; `ingest_golden_as_of.json` has the same shape with a non-null
  `as_of` (ISO date string) the C++ test must pass to `ingest_csv`.

- [ ] **Step 1: Write the export script**

```python
# src/export_ingest_golden.py
"""Generate golden-file CSV + JSON fixtures for cross-checking a C++ Arrow
ingestion port (cpp/src/ingest.cpp) against the real Python elog_to_features."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import elog_to_features  # noqa: E402

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# Deliberately small and hand-checkable: gaps are exact multiples of 7 days.
# cust A: acquisition + a same-day duplicate + two more repeats.
# cust B: a single transaction (x=0, exercises the no-repeat path).
# cust C: acquired partway through, two repeats, tests a second active customer.
_ROWS = [
    ("A", "2024-01-01", 10.0),
    ("A", "2024-01-08", 5.0),
    ("A", "2024-01-08", 5.0),   # same-day duplicate of the row above
    ("A", "2024-01-22", 8.0),
    ("A", "2024-02-05", 12.0),
    ("B", "2024-01-01", 3.0),
    ("C", "2024-01-15", 20.0),
    ("C", "2024-01-29", 6.0),
    ("C", "2024-02-12", 6.0),
]


def _elog(with_spend: bool) -> pd.DataFrame:
    df = pd.DataFrame(_ROWS, columns=["cust", "date", "spend"])
    df["date"] = pd.to_datetime(df["date"])
    if not with_spend:
        df = df.drop(columns=["spend"])
    return df


def _to_json(features: pd.DataFrame, as_of: str | None, has_money: bool) -> dict:
    customers = []
    for row in features.to_dict("records"):
        c = {"cust": str(row["cust"]), "x": row["x"], "t_x": row["t_x"], "T_cal": row["T_cal"]}
        c["m_bar"] = row["m_bar"] if has_money else None
        customers.append(c)
    return {"as_of": as_of, "customers": customers}


if __name__ == "__main__":
    MODELS_DIR.mkdir(exist_ok=True)

    money_elog = _elog(with_spend=True)
    money_elog.assign(
        customer_id=money_elog["cust"], transaction_date=money_elog["date"].dt.strftime("%Y-%m-%d"),
        amount=money_elog["spend"],
    )[["customer_id", "transaction_date", "amount"]].to_csv(
        MODELS_DIR / "ingest_sample.csv", index=False)

    no_money_elog = _elog(with_spend=False)
    no_money_elog.assign(
        customer_id=no_money_elog["cust"], transaction_date=no_money_elog["date"].dt.strftime("%Y-%m-%d"),
    )[["customer_id", "transaction_date"]].to_csv(
        MODELS_DIR / "ingest_sample_no_money.csv", index=False)

    default_features = elog_to_features(money_elog)
    (MODELS_DIR / "ingest_golden.json").write_text(
        json.dumps(_to_json(default_features, as_of=None, has_money=True), indent=2))

    as_of = pd.Timestamp("2024-01-29")
    as_of_features = elog_to_features(money_elog, as_of=as_of)
    (MODELS_DIR / "ingest_golden_as_of.json").write_text(
        json.dumps(_to_json(as_of_features, as_of=as_of.strftime("%Y-%m-%d"), has_money=True), indent=2))

    no_money_features = elog_to_features(no_money_elog)
    (MODELS_DIR / "ingest_golden_no_money.json").write_text(
        json.dumps(_to_json(no_money_features, as_of=None, has_money=False), indent=2))

    print("Wrote ingest_sample.csv, ingest_sample_no_money.csv, and 3 golden JSON files")
```

- [ ] **Step 2: Run the export**

Run: `python src/export_ingest_golden.py`
Expected: prints the confirmation line; `models/ingest_sample.csv`,
`models/ingest_sample_no_money.csv`, `models/ingest_golden.json`,
`models/ingest_golden_as_of.json`, `models/ingest_golden_no_money.json` all
exist.

- [ ] **Step 3: Sanity-check the output by hand**

Open `models/ingest_golden.json` and confirm cust `"A"`: `x=3`
(01-08-merged, 01-22, 02-05), `t_x=(02-05 - 01-01)/7=5.0`,
`T_cal=5.0` (as_of defaults to the log max, 02-05), `m_bar=mean([10, 8,
12])=10.0`. Cust `"B"`: `x=0`, `t_x=0.0`, `T_cal=(02-05-01-01)/7≈4.857`,
`m_bar=0.0`. This is the same hand-checkable-gap trick as Task 1's toy
fixture, just larger.

- [ ] **Step 4: Commit**

```bash
git add src/export_ingest_golden.py models/ingest_sample.csv models/ingest_sample_no_money.csv models/ingest_golden.json models/ingest_golden_as_of.json models/ingest_golden_no_money.json
git commit -m "feat: generate golden-file CSV + JSON fixtures for Arrow ingestion cross-check"
```

---

### Task 3: C++ project scaffold — Arrow dependency + smoke test

**Files:**
- Modify: `cpp/vcpkg.json`
- Modify: `cpp/CMakeLists.txt`
- Create: `cpp/include/pareto_nbd/ingest.hpp`
- Create: `cpp/src/ingest.cpp`
- Create: `cpp/tests/test_ingest.cpp`
- Create (fixtures, not generated): `models/ingest_bad_missing_column.csv`,
  `models/ingest_bad_empty.csv`

**Interfaces:**
- Produces: the `CustomerFeatures` struct and `IngestError` exception type
  (public API for the rest of this plan), plus a minimal `ingest_csv` that
  only proves the Arrow dependency links and a file can be opened — no
  feature computation yet (Tasks 4–7 build that incrementally). Isolating
  the new, heavy dependency in its own task keeps a slow/failed vcpkg build
  easy to bisect from the actual logic.

- [ ] **Step 1: Add the Arrow dependency**

```json
// cpp/vcpkg.json — replace "dependencies" with:
"dependencies": [
    "onnxruntime",
    "nlohmann-json",
    "catch2",
    {
      "name": "arrow",
      "features": ["csv", "compute"]
    }
]
```

- [ ] **Step 2: Write the interface and a failing smoke test**

```cpp
// cpp/include/pareto_nbd/ingest.hpp
#pragma once
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace pareto_nbd {

// Thrown for a malformed/empty CSV or a missing required column. Messages
// are written to be user-facing (surfaced by the future upload-validation
// API, per the spec's §6 error handling), not raw parser internals.
class IngestError : public std::runtime_error {
public:
    explicit IngestError(const std::string& msg) : std::runtime_error(msg) {}
};

// Per-customer BTYD + monetary features computed from a raw transaction-log
// CSV. Parallel arrays, one entry per customer, in no particular order.
// m_bar is empty (and has_monetary is false) when the CSV has no "amount"
// column -- the CLV stage (cpp/include/pareto_nbd/clv.hpp) is simply not
// run for a cohort ingested this way.
struct CustomerFeatures {
    std::vector<std::string> customer_id;
    std::vector<double> x;
    std::vector<double> t_x;
    std::vector<double> T_cal;
    std::vector<double> m_bar;
    bool has_monetary = false;
};

// Reads a transaction-log CSV (required columns: "customer_id",
// "transaction_date"; optional: "amount") and computes per-customer
// features as of as_of_iso_date (format "YYYY-MM-DD"), or the log's own max
// transaction date if not given. Mirrors src/ingest.py's
// elog_to_features exactly (see that module's docstring for the semantics).
// Throws IngestError on a missing required column or an empty file.
CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date = std::nullopt);

}  // namespace pareto_nbd
```

```cpp
// cpp/tests/test_ingest.cpp
#include <catch2/catch_test_macros.hpp>
#include <string>
#include "pareto_nbd/ingest.hpp"

TEST_CASE("ingest_csv smoke test: reads the sample fixture without throwing", "[ingest]") {
    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");
    REQUIRE(features.customer_id.size() == 3);   // customers A, B, C
}
```

Modify `cpp/CMakeLists.txt`:

```cmake
# near the top, alongside the other find_package calls
find_package(Arrow CONFIG REQUIRED)

# add src/ingest.cpp to add_library(amortized_inference ...) sources
# add this to amortized_inference's target_link_libraries (PUBLIC section):
#     Arrow::arrow_shared     <- or Arrow::arrow_static; see Global Constraints

# add tests/test_ingest.cpp to add_executable(unit_tests ...) sources
```

- [ ] **Step 3: Write the placeholder implementation**

```cpp
// cpp/src/ingest.cpp
#include "pareto_nbd/ingest.hpp"

namespace pareto_nbd {

CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    (void)as_of_iso_date;
    CustomerFeatures result;
    result.customer_id = {"A", "B", "C"};   // placeholder -- Tasks 4-5 replace this
    return result;
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Configure, build, and run tests**

Run:
```bash
cmake --preset default
cmake --build build
ctest --test-dir build --output-on-failure
```
Expected: configure succeeds (vcpkg builds Arrow from source the first
time — this can take a long time); build succeeds; the new `[ingest]` test
case passes against the placeholder. All prior test cases (version, moments,
cohort_features, amortized_model, nelder_mead, clv, conformal) still pass.

- [ ] **Step 5: Create the two bad-input fixtures used by Task 4**

```
# models/ingest_bad_missing_column.csv
customer_id,amount
A,10.0
B,5.0
```

```
# models/ingest_bad_empty.csv
customer_id,transaction_date,amount
```

(The second is header-only — zero data rows, which is the "empty
transaction log" case per the spec's §6 error handling, not a zero-byte
file: a zero-byte file fails at CSV-header-parsing, a header-only file fails
at the "no rows" check. Task 4 tests both.)

- [ ] **Step 6: Commit**

```bash
git add cpp/vcpkg.json cpp/CMakeLists.txt cpp/include/pareto_nbd/ingest.hpp cpp/src/ingest.cpp cpp/tests/test_ingest.cpp models/ingest_bad_missing_column.csv models/ingest_bad_empty.csv
git commit -m "feat(cpp): scaffold Arrow-based ingest.hpp/cpp with a smoke test"
```

---

### Task 4: CSV load + column validation + error handling

**Files:**
- Modify: `cpp/src/ingest.cpp`
- Modify: `cpp/tests/test_ingest.cpp`

**Interfaces:**
- Produces: an internal `LoadRawTable(path) -> {table, has_monetary}`
  helper (anonymous namespace, not exported) that owns all Arrow CSV-reader
  setup and validation. `ingest_csv` (still returning the Task 3
  placeholder features) now calls it, so the error paths are exercised
  through the public API from here on.

- [ ] **Step 1: Write the failing tests**

```cpp
// append to cpp/tests/test_ingest.cpp
#include <catch2/catch_exception_translator.hpp>

TEST_CASE("ingest_csv rejects a missing required column", "[ingest][errors]") {
    REQUIRE_THROWS_AS(
        pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_bad_missing_column.csv"),
        pareto_nbd::IngestError);
}

TEST_CASE("ingest_csv rejects an empty transaction log", "[ingest][errors]") {
    REQUIRE_THROWS_AS(
        pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_bad_empty.csv"),
        pareto_nbd::IngestError);
}

TEST_CASE("ingest_csv rejects a nonexistent file", "[ingest][errors]") {
    REQUIRE_THROWS_AS(pareto_nbd::ingest_csv("does_not_exist.csv"), pareto_nbd::IngestError);
}

TEST_CASE("ingest_csv detects the optional amount column", "[ingest]") {
    auto with_money = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");
    REQUIRE(with_money.has_monetary);

    auto without_money = pareto_nbd::ingest_csv(
        std::string(PROJECT_MODELS_DIR) + "/ingest_sample_no_money.csv");
    REQUIRE_FALSE(without_money.has_monetary);
}
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: the four new `[errors]`/monetary-detection cases FAIL (the
placeholder implementation never throws and never sets `has_monetary`); all
prior cases still PASS.

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/src/ingest.cpp
#include "pareto_nbd/ingest.hpp"

#include <arrow/api.h>
#include <arrow/csv/api.h>
#include <arrow/io/api.h>

namespace pareto_nbd {
namespace {

struct RawTable {
    std::shared_ptr<arrow::Table> table;
    bool has_monetary = false;
};

RawTable LoadRawTable(const std::string& path) {
    auto file_result = arrow::io::ReadableFile::Open(path);
    if (!file_result.ok()) {
        throw IngestError("could not open transaction log: " + file_result.status().ToString());
    }

    auto read_options = arrow::csv::ReadOptions::Defaults();
    auto parse_options = arrow::csv::ParseOptions::Defaults();
    auto convert_options = arrow::csv::ConvertOptions::Defaults();
    convert_options.column_types["customer_id"] = arrow::utf8();
    convert_options.column_types["transaction_date"] = arrow::timestamp(arrow::TimeUnit::SECOND);
    convert_options.timestamp_parsers = {arrow::TimestampParser::MakeISO8601()};
    // amount's type (if present) is left to Arrow's own inference (float64
    // for numeric columns); we only need to know whether it exists.

    auto reader_result = arrow::csv::TableReader::Make(
        arrow::io::default_io_context(), *file_result, read_options, parse_options, convert_options);
    if (!reader_result.ok()) {
        throw IngestError("could not parse transaction log: " + reader_result.status().ToString());
    }

    auto table_result = (*reader_result)->Read();
    if (!table_result.ok()) {
        throw IngestError("could not parse transaction log: " + table_result.status().ToString());
    }
    auto table = *table_result;

    const auto& schema = table->schema();
    if (schema->GetFieldIndex("customer_id") < 0) {
        throw IngestError("missing required column 'customer_id'");
    }
    if (schema->GetFieldIndex("transaction_date") < 0) {
        throw IngestError("missing required column 'transaction_date'");
    }
    if (table->num_rows() == 0) {
        throw IngestError("transaction log is empty");
    }

    RawTable result;
    result.table = table;
    result.has_monetary = schema->GetFieldIndex("amount") >= 0;
    return result;
}

}  // namespace

CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    (void)as_of_iso_date;
    RawTable raw = LoadRawTable(path);

    CustomerFeatures result;
    result.has_monetary = raw.has_monetary;
    result.customer_id = {"A", "B", "C"};   // placeholder -- Task 5 replaces this
    return result;
}

}  // namespace pareto_nbd
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS — all `[ingest]`/`[errors]` cases, including the placeholder
smoke test (feature values are still fake, but no test yet asserts them).

- [ ] **Step 5: Commit**

```bash
git add cpp/src/ingest.cpp cpp/tests/test_ingest.cpp
git commit -m "feat(cpp): validate required columns and reject empty CSVs before parsing features"
```

---

### Task 5: Core algorithm — sort, group, compute features (default `as_of`)

**Files:**
- Modify: `cpp/src/ingest.cpp`
- Modify: `cpp/tests/test_ingest.cpp`

**Interfaces:**
- Produces: the real `ingest_csv` — sorts the loaded table by
  `(customer_id, transaction_date)` via Arrow's `SortIndices`/`Take`, then
  does one linear pass to compute `x`, `t_x`, `T_cal`[, `m_bar`] per
  customer, using the table's own max `transaction_date` as `as_of` when
  none is given (Task 6 adds the explicit-`as_of` path).

- [ ] **Step 1: Write the failing golden-file test**

```cpp
// append to cpp/tests/test_ingest.cpp
#include <algorithm>
#include <fstream>
#include <nlohmann/json.hpp>

namespace {

// Finds the CustomerFeatures entry for a given id, or fails the test.
size_t index_of(const pareto_nbd::CustomerFeatures& f, const std::string& cust) {
    auto it = std::find(f.customer_id.begin(), f.customer_id.end(), cust);
    REQUIRE(it != f.customer_id.end());
    return static_cast<size_t>(it - f.customer_id.begin());
}

}  // namespace

TEST_CASE("ingest_csv matches the Python golden file (default as_of)", "[ingest][golden]") {
    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv");

    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/ingest_golden.json");
    nlohmann::json golden;
    f >> golden;

    REQUIRE(features.has_monetary);
    REQUIRE(features.customer_id.size() == golden["customers"].size());

    for (const auto& c : golden["customers"]) {
        size_t i = index_of(features, c["cust"].get<std::string>());
        REQUIRE(features.x[i] == Catch::Approx(c["x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.t_x[i] == Catch::Approx(c["t_x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.T_cal[i] == Catch::Approx(c["T_cal"].get<double>()).epsilon(1e-9));
        REQUIRE(features.m_bar[i] == Catch::Approx(c["m_bar"].get<double>()).epsilon(1e-9));
    }
}
```

Add `#include <catch2/catch_approx.hpp>` to the top of the file if not
already present (it is, via other test cases in this file by the time this
task lands — check before adding a duplicate).

- [ ] **Step 2: Run the test to verify it fails**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: FAIL — the placeholder `x`/`t_x`/`T_cal`/`m_bar` vectors are
empty/default, not the golden values.

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/src/ingest.cpp — add near the top, after the existing includes
#include <arrow/compute/api.h>
#include <cmath>
#include <map>

// ... inside the anonymous namespace, after LoadRawTable ...

constexpr int64_t kSecondsPerDay = 86400;

// Sorts by (customer_id, transaction_date) so every customer's rows are
// contiguous and date-ordered; the linear pass below relies on this.
std::shared_ptr<arrow::Table> SortByCustomerThenDate(const std::shared_ptr<arrow::Table>& table) {
    arrow::compute::SortOptions sort_options({
        arrow::compute::SortKey("customer_id", arrow::compute::SortOrder::Ascending),
        arrow::compute::SortKey("transaction_date", arrow::compute::SortOrder::Ascending),
    });
    auto indices = arrow::compute::SortIndices(table, sort_options).ValueOrDie();
    auto sorted = arrow::compute::Take(table, indices).ValueOrDie();
    return sorted.table();
}

// One row per (customer, calendar day), amounts summed within a day.
// Building this from the sorted table is a single pass since duplicate
// (customer, day) rows are guaranteed adjacent after SortByCustomerThenDate.
struct DedupedRow {
    std::string customer_id;
    int64_t day;             // days since epoch
    double amount = 0.0;
};

std::vector<DedupedRow> DedupSameDay(const std::shared_ptr<arrow::Table>& sorted, bool has_monetary) {
    auto combined = sorted->CombineChunks().ValueOrDie();
    auto cust_col = std::static_pointer_cast<arrow::StringArray>(combined->column(0)->chunk(0));
    auto date_col = std::static_pointer_cast<arrow::TimestampArray>(combined->column(1)->chunk(0));
    std::shared_ptr<arrow::DoubleArray> amount_col;
    if (has_monetary) {
        int amount_idx = combined->schema()->GetFieldIndex("amount");
        amount_col = std::static_pointer_cast<arrow::DoubleArray>(combined->column(amount_idx)->chunk(0));
    }

    std::vector<DedupedRow> out;
    const int64_t n = cust_col->length();
    for (int64_t i = 0; i < n; ++i) {
        std::string cust = cust_col->GetString(i);
        int64_t day = date_col->Value(i) / kSecondsPerDay;
        double amount = has_monetary ? amount_col->Value(i) : 0.0;

        if (!out.empty() && out.back().customer_id == cust && out.back().day == day) {
            out.back().amount += amount;   // same-day duplicate: sum
        } else {
            out.push_back({cust, day, amount});
        }
    }
    return out;
}

}  // namespace
```

```cpp
// replace ingest_csv's body in cpp/src/ingest.cpp
CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    (void)as_of_iso_date;   // Task 6 wires this through

    RawTable raw = LoadRawTable(path);
    auto sorted = SortByCustomerThenDate(raw.table);
    auto rows = DedupSameDay(sorted, raw.has_monetary);

    int64_t as_of_day = rows.back().day;   // rows is date-sorted within the
    for (const auto& r : rows) as_of_day = std::max(as_of_day, r.day);  // last customer's block only, so scan all rows for the true max

    CustomerFeatures result;
    result.has_monetary = raw.has_monetary;

    size_t i = 0;
    while (i < rows.size()) {
        size_t j = i;
        while (j < rows.size() && rows[j].customer_id == rows[i].customer_id) ++j;
        // rows[i..j) is this customer's date-ordered, same-day-deduped history.
        int64_t acq_day = rows[i].day;
        size_t n_repeats = (j - i) - 1;

        result.customer_id.push_back(rows[i].customer_id);
        result.x.push_back(static_cast<double>(n_repeats));
        result.t_x.push_back(n_repeats > 0 ? (rows[j - 1].day - acq_day) / 7.0 : 0.0);
        result.T_cal.push_back((as_of_day - acq_day) / 7.0);
        if (raw.has_monetary) {
            double sum = 0.0;
            for (size_t k = i + 1; k < j; ++k) sum += rows[k].amount;
            result.m_bar.push_back(n_repeats > 0 ? sum / static_cast<double>(n_repeats) : 0.0);
        }
        i = j;
    }
    return result;
}
```

The `as_of_day` computation above is written slightly awkwardly on purpose
— fix it to a clean single-pass max before moving on:

```cpp
    int64_t as_of_day = rows.front().day;
    for (const auto& r : rows) as_of_day = std::max(as_of_day, r.day);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS — the golden-file case and everything else.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/ingest.cpp cpp/tests/test_ingest.cpp
git commit -m "feat(cpp): compute per-customer x/t_x/T_cal/m_bar via Arrow sort + linear scan"
```

---

### Task 6: Explicit `as_of` override

**Files:**
- Modify: `cpp/src/ingest.cpp`
- Modify: `cpp/tests/test_ingest.cpp`

**Interfaces:**
- Produces: `ingest_csv`'s `as_of_iso_date` parameter, previously ignored,
  now parsed (`"YYYY-MM-DD"`) and used in place of the table's own max date
  — both as the `T_cal` reference point and as an upper bound filtering out
  any transaction after it (matching `elog_to_features`'s `as_of` semantics
  from Task 1, confirmed by `test_elog_to_features_explicit_as_of`).

- [ ] **Step 1: Write the failing golden-file test**

```cpp
// append to cpp/tests/test_ingest.cpp
TEST_CASE("ingest_csv matches the Python golden file (explicit as_of)", "[ingest][golden]") {
    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/ingest_golden_as_of.json");
    nlohmann::json golden;
    f >> golden;
    std::string as_of = golden["as_of"].get<std::string>();

    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample.csv", as_of);

    REQUIRE(features.customer_id.size() == golden["customers"].size());
    for (const auto& c : golden["customers"]) {
        size_t i = index_of(features, c["cust"].get<std::string>());
        REQUIRE(features.x[i] == Catch::Approx(c["x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.t_x[i] == Catch::Approx(c["t_x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.T_cal[i] == Catch::Approx(c["T_cal"].get<double>()).epsilon(1e-9));
        REQUIRE(features.m_bar[i] == Catch::Approx(c["m_bar"].get<double>()).epsilon(1e-9));
    }
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: FAIL — `as_of_iso_date` is still ignored, so `T_cal`/`x` are
computed against the file's own max date instead of the earlier override.

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/src/ingest.cpp — add to the anonymous namespace
#include <charconv>
#include <sstream>

int64_t ParseIsoDateToDays(const std::string& iso_date) {
    // "YYYY-MM-DD" -> days since 1970-01-01, via the same epoch Arrow's
    // TimestampArray uses (seconds since epoch / kSecondsPerDay upstream).
    std::tm tm{};
    std::istringstream ss(iso_date);
    ss >> std::get_time(&tm, "%Y-%m-%d");
    if (ss.fail()) {
        throw IngestError("invalid as_of date (expected YYYY-MM-DD): " + iso_date);
    }
#ifdef _WIN32
    time_t t = _mkgmtime(&tm);
#else
    time_t t = timegm(&tm);
#endif
    return static_cast<int64_t>(t) / kSecondsPerDay;
}
```

Add `#include <ctime>` near the top of the file. Then update `ingest_csv`:

```cpp
CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    RawTable raw = LoadRawTable(path);
    auto sorted = SortByCustomerThenDate(raw.table);
    auto rows = DedupSameDay(sorted, raw.has_monetary);

    int64_t as_of_day;
    if (as_of_iso_date.has_value()) {
        as_of_day = ParseIsoDateToDays(*as_of_iso_date);
        rows.erase(std::remove_if(rows.begin(), rows.end(),
                                   [as_of_day](const DedupedRow& r) { return r.day > as_of_day; }),
                   rows.end());
        if (rows.empty()) {
            throw IngestError("no transactions on or before as_of date " + *as_of_iso_date);
        }
    } else {
        as_of_day = rows.front().day;
        for (const auto& r : rows) as_of_day = std::max(as_of_day, r.day);
    }

    // ... the rest (grouping + per-customer computation) is unchanged from Task 5 ...
```

Add `#include <algorithm>` if not already present (it is, from Task 5's
`std::max`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS — both golden-file cases (default and explicit `as_of`), and
everything else.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/ingest.cpp cpp/tests/test_ingest.cpp
git commit -m "feat(cpp): support an explicit as_of override in ingest_csv"
```

---

### Task 7: No-monetary CSV path

**Files:**
- Modify: `cpp/tests/test_ingest.cpp`

**Interfaces:**
- Consumes: `ingest_csv` (Tasks 5–6), already branching correctly on
  `has_monetary` — this task is pure verification, not new production code
  (Task 4 already asserted `has_monetary` flips correctly; this closes the
  loop by checking the numeric `x`/`t_x`/`T_cal` values too, and that
  `m_bar` is left empty rather than filled with placeholder zeros).

- [ ] **Step 1: Write the failing test**

```cpp
// append to cpp/tests/test_ingest.cpp
TEST_CASE("ingest_csv matches the Python golden file (no amount column)", "[ingest][golden]") {
    auto features = pareto_nbd::ingest_csv(std::string(PROJECT_MODELS_DIR) + "/ingest_sample_no_money.csv");

    std::ifstream f(std::string(PROJECT_MODELS_DIR) + "/ingest_golden_no_money.json");
    nlohmann::json golden;
    f >> golden;

    REQUIRE_FALSE(features.has_monetary);
    REQUIRE(features.m_bar.empty());
    REQUIRE(features.customer_id.size() == golden["customers"].size());

    for (const auto& c : golden["customers"]) {
        size_t i = index_of(features, c["cust"].get<std::string>());
        REQUIRE(features.x[i] == Catch::Approx(c["x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.t_x[i] == Catch::Approx(c["t_x"].get<double>()).epsilon(1e-9));
        REQUIRE(features.T_cal[i] == Catch::Approx(c["T_cal"].get<double>()).epsilon(1e-9));
    }
}
```

This should already pass given Tasks 4–6's implementation — the point of
this task is confirming that, not writing new code. If it fails, the most
likely gap is `DedupSameDay`/the grouping loop assuming `has_monetary` is
always true somewhere; fix forward rather than special-casing this test.

- [ ] **Step 2: Run the test**

Run: `cmake --build build && ctest --test-dir build --output-on-failure`
Expected: PASS immediately. If not, fix `cpp/src/ingest.cpp` (see note
above) rather than the test.

- [ ] **Step 3: Commit**

```bash
git add cpp/tests/test_ingest.cpp
git commit -m "test(cpp): cover the no-monetary-column ingest path against the Python golden file"
```

---

### Task 8: Wire the demo to real CSV ingestion end-to-end

**Files:**
- Modify: `cpp/src/main.cpp`

**Interfaces:**
- Consumes: `ingest_csv` (this plan), `cohort_features` (Phase 1),
  `AmortizedModel` (Phase 1), `fit_gamma_gamma`/`posterior_mean_nu`/
  `predict_clv_distribution` (Phase 2).
- Produces: no new library code — replaces the demo's golden-JSON-loaded
  synthetic cohort with a real CSV read through the whole pipeline, so
  `cpp/build/main` demonstrates the actual product loop end to end (raw CSV
  in, per-customer CLV out) for the first time.

- [ ] **Step 1: Rewrite `main.cpp`**

```cpp
// cpp/src/main.cpp
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/clv.hpp"
#include "pareto_nbd/cohort_features.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/version.hpp"

// Demo entry point: reads a real transaction-log CSV (the same fixture the
// test suite golden-checks against) end to end -- Arrow ingestion ->
// amortized Pareto/NBD parameters -> Gamma-Gamma CLV -- printed in plain
// terms instead of pass/fail assertions. This is the first point in the
// build where all three ported stages (Phase 1, Phase 2, Phase 3) run
// together on the same real input.
int main() {
    std::cout << "pareto-nbd-inference v" << pareto_nbd::version() << "\n\n";

    const std::string models_dir = PROJECT_MODELS_DIR;

    auto cohort = pareto_nbd::ingest_csv(models_dir + "/ingest_sample.csv");
    std::cout << "Ingested " << models_dir << "/ingest_sample.csv: "
              << cohort.customer_id.size() << " customers"
              << (cohort.has_monetary ? " (with spend data)\n" : " (no spend data)\n");

    pareto_nbd::AmortizedModel model(models_dir + "/amortizer_mlp.onnx",
                                      models_dir + "/amortizer_scalers.json");
    auto features = pareto_nbd::cohort_features(cohort.x, cohort.t_x, cohort.T_cal);
    auto params = model.predict(features);

    std::cout << std::fixed << std::setprecision(4);
    std::cout << "\nEstimated Pareto/NBD parameters:\n";
    std::cout << "  r=" << params.r << " alpha=" << params.alpha
              << " s=" << params.s << " beta=" << params.beta << "\n";

    if (cohort.has_monetary) {
        auto gg = pareto_nbd::fit_gamma_gamma(cohort.x, cohort.m_bar);
        auto nu = pareto_nbd::posterior_mean_nu(cohort.x, cohort.m_bar, gg);
        std::cout << "\nGamma-Gamma spend model: p=" << gg.p << " q=" << gg.q << " v=" << gg.v << "\n";
        std::cout << "\nPer-customer posterior mean spend per transaction:\n";
        for (size_t i = 0; i < cohort.customer_id.size(); ++i) {
            std::cout << "  " << cohort.customer_id[i] << ": nu=" << nu[i]
                      << "  (observed x=" << cohort.x[i] << ", m_bar=" << cohort.m_bar[i] << ")\n";
        }
    }

    std::cout << "\nTurning this into a full CLV forecast (expected future purchases x\n"
              << "posterior mean spend, with a conformal-calibrated interval) wires\n"
              << "together predict_clv_distribution + the conformal-calibration stage\n"
              << "already ported in Phase 2 -- left as an exercise for the Drogon API\n"
              << "worker (Phase 4), which is where this pipeline actually gets called\n"
              << "per uploaded job rather than on one hardcoded demo file.\n";

    return 0;
}
```

- [ ] **Step 2: Build and run the demo**

Run:
```bash
cmake --build build
./build/main       # or build/Release/main.exe on the MSVC generator layout
```
Expected: prints the ingested customer count, the estimated Pareto/NBD
parameters, the fitted Gamma-Gamma parameters, and each customer's posterior
mean spend — real numbers derived from `models/ingest_sample.csv`, not a
canned golden-file cohort.

Run: `ctest --test-dir build --output-on-failure`
Expected: all test cases still pass (this task changes `main.cpp` only, not
`unit_tests`).

- [ ] **Step 3: Commit**

```bash
git add cpp/src/main.cpp
git commit -m "demo: wire main.cpp to real Arrow CSV ingestion end to end"
```

---

## Definition of done

Running `ctest --test-dir cpp/build` passes every test case from Phases 1–2
plus this plan's `[ingest]` suite (error handling, monetary-column
detection, and three golden-file checks — default `as_of`, explicit
`as_of`, no-monetary — all cross-checked against `src/ingest.py`'s
`elog_to_features`). `cpp/build/main` demonstrates the full raw-CSV-to-CLV
pipeline on a real file. This closes Phase 3 of the spec. Phase 4 (the
Drogon API: upload → validate → enqueue → worker picks up → writes results
to Postgres) is the next plan; it depends on `ingest_csv`,
`AmortizedModel`, and the Phase 2 CLV/conformal functions all existing as
stable library calls, which they now do — Phase 4 is wiring, not new
numerical logic.
