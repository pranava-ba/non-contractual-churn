# SvelteKit Frontend (Phase 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A SvelteKit app where a business drops a transaction-log CSV, watches the job run, then sees a cohort dashboard (ECharts) plus a sortable/filterable per-customer forecast table and a CSV export — all against the Phase 4 Drogon API.

**Architecture:** A new `frontend/` SvelteKit (Svelte 5, TypeScript, `adapter-node`) app. The browser only ever talks to its own origin under `/api/*`; a `hooks.server.ts` handler forwards those requests to the Drogon API (`API_BASE_URL`), which sidesteps CORS (the API has none) and keeps the API address out of client code. Two small, additive endpoints/params are added to the C++ API first (Tasks 1–2) because the dashboard needs cohort-level aggregates and server-side sort/filter that the Phase 4 API does not expose — computing histograms over hundreds of thousands of customers in the browser would mean downloading every row. All UI logic that can be pure (header validation, API client, polling, chart-option builders, formatting) is a plain TypeScript module with Vitest tests; Svelte components are thin and tested with Testing Library.

**Tech Stack:** SvelteKit 2 + Svelte 5 (runes), TypeScript, Vite 6, `@sveltejs/adapter-node`, ECharts 5 (modular imports, own thin `Chart.svelte` wrapper), Vitest 3 + `@testing-library/svelte` + jsdom. Backend additions: C++20 / Drogon / Catch2 (existing `cpp/` project).

**Spec:** [docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md](../specs/2026-09-26-clv-forecasting-saas-design.md) §4.1 (frontend), §4.2 (API), §6 (partial-data flags), §8 (stack), §9 step 5. Backend contract: [docs/superpowers/plans/2026-09-28-drogon-api-worker.md](2026-09-28-drogon-api-worker.md) and `cpp/src/api_routes.cpp`.

## Global Constraints

- **Stack is locked** (spec §8): SvelteKit frontend, ECharts for charts. No other UI/chart framework (no Tailwind/Bootstrap/Chart.js). Plain scoped CSS in components.
- **Auth, multi-tenancy, billing, customer-facing API access are out of scope** (spec §10). No login UI.
- **Upload contract:** `POST /uploads` takes the **entire request body as the raw CSV** (no multipart). Success: `200 {"job_id": "<uuid>"}`. Failure: `400 {"error": "..."}` (bad CSV), `503 {"error": "...", "job_id": "..."}` (queue down). Body limit is 100 MB.
- **CSV schema** (case-sensitive, matches `cpp/src/ingest.cpp`): required `customer_id`, `transaction_date`; optional `amount`. Extra columns are allowed.
- **Job states:** `queued`, `running`, `done`, `failed`. `GET /jobs/{id}` → `{id, status, error_reason: string|null}`. `/results`, `/summary`, `/export.csv` return **404** until the job is `done`, and **400** for a malformed job id.
- **`data_quality` values** (spec §6): `ok`, `insufficient_history` (x==0, forecast computed but low confidence), `forecast_unavailable` (all numbers are 0.0 placeholders), `clv_unavailable` (CLV columns are 0.0 placeholders). The UI must never present placeholder values as real predictions.
- **No CLV interval yet:** in this phase the worker sets `clv_lower == clv_upper == clv_point` (no conformal interval is fitted — see `cpp/src/worker.cpp`). The UI shows an interval only when the API reports `has_clv_interval: true`.
- **PIT / calibration diagnostic (spec §4.1) is deferred.** A PIT plot needs a held-out future; production uploads have none, so there is nothing to compute it from. The dashboard ships forecast-distribution, P(alive) and CLV histograms instead. Revisit when a holdout/backtest mode exists.
- **Same-origin proxy:** the browser calls `/api/...`; the server forwards to `API_BASE_URL` (default `http://localhost:8080`). Production (`adapter-node`) must run with `BODY_SIZE_LIMIT=100M` — its default of 512 KB would reject real uploads. The upload request uses `Content-Type: text/csv` so SvelteKit's form-CSRF origin check (which only guards form content types) does not apply.
- **Node ≥ 20** (dev machine has Node 24 / npm 11). Frontend lives at `frontend/`; do not touch `cpp/` outside Tasks 1–2.
- **Commits:** frequent, one per task step 5; messages `feat(cpp): ...` / `feat(frontend): ...` in the style of the existing history.

---

## File Structure

```
cpp/src/api_routes.cpp                      (modify: Tasks 1, 2)
cpp/tests/test_summary_endpoint.cpp         (create: Task 1)
cpp/tests/test_results_endpoint.cpp         (modify: Task 2)
cpp/CMakeLists.txt                          (modify: Task 1 — register new test file)
.gitignore                                  (modify: Task 3)
frontend/
  package.json  svelte.config.js  vite.config.ts  tsconfig.json
  src/app.html  src/app.d.ts
  src/hooks.server.ts                       # /api/* proxy handle (thin)
  src/lib/server/proxy.ts                   # pure proxy logic (Task 3)
  src/lib/types.ts                          # API types (Task 4)
  src/lib/api.ts                            # typed fetch client (Task 4)
  src/lib/csvHeader.ts                      # client-side CSV header validation (Task 5)
  src/lib/format.ts                         # number/label formatting (Task 5)
  src/lib/poller.ts                         # job-status polling (Task 7)
  src/lib/chartOptions.ts                   # pure ECharts option builders (Task 8)
  src/lib/components/Dropzone.svelte        # (Task 6)
  src/lib/components/Chart.svelte           # ECharts wrapper (Task 8)
  src/lib/components/SummaryTiles.svelte    # (Task 9)
  src/lib/components/QualityBadge.svelte    # (Task 10)
  src/lib/components/CustomerTable.svelte   # (Task 10)
  src/routes/+layout.svelte                 # shell + global CSS (Task 3)
  src/routes/+page.svelte                   # upload page (Task 6)
  src/routes/jobs/[id]/+page.svelte         # status → dashboard (Tasks 7, 9, 10, 11)
  tests/                                    # *.test.ts mirroring lib/ and components/
  scripts/smoke.mjs                         # live-stack smoke script (Task 12)
  README.md                                 # run instructions (Task 12)
```

---

### Task 1: Backend — `GET /jobs/{id}/summary` (cohort aggregates + histograms)

The dashboard's tiles and three histograms need cohort-level numbers. Computing them in SQL keeps the browser from downloading every customer row.

**Files:**
- Modify: `cpp/src/api_routes.cpp` (anonymous-namespace helper + one new route, placed after `/jobs/{id}/results`)
- Create: `cpp/tests/test_summary_endpoint.cpp`
- Modify: `cpp/CMakeLists.txt` (add `tests/test_summary_endpoint.cpp` to `unit_tests`, after `tests/test_results_endpoint.cpp`)

**Interfaces:**
- Consumes: existing `IsValidUuidFormat`, `JsonResponse`, `db->execSqlSync` (same patterns as the neighbouring handlers); `forecast_results` columns incl. `data_quality`.
- Produces: `GET /jobs/{id}/summary` →
```json
{
  "job_id": "…",
  "n_customers": 4,
  "quality_counts": {"ok": 2, "insufficient_history": 1, "forecast_unavailable": 1},
  "mean_p_alive": 0.6,
  "total_expected_purchases": 4.5,
  "total_clv": 40.0,
  "has_clv_interval": true,
  "histograms": {
    "p_alive":            {"edges": [0, 0.1, …, 1.0],   "counts": [/*10 ints*/]},
    "expected_purchases": {"edges": [0, …, max],        "counts": [/*20 ints*/]},
    "clv_point":          {"edges": [0, …, max],        "counts": [/*20 ints*/]}
  }
}
```
  Semantics: `p_alive`, `expected_purchases`, `mean_p_alive`, `total_expected_purchases` and those two histograms cover only rows with `data_quality IN ('ok','insufficient_history')` (the rest hold 0.0 placeholders). `total_clv` and the `clv_point` histogram cover only `data_quality = 'ok'`. `quality_counts` covers all rows and omits zero-count keys. Bin counts: 10 (`p_alive`, fixed range 0–1), 20 (others, range 0–max, or 0–1 when max ≤ 0). `has_clv_interval` is `true` iff any row has `clv_upper > clv_lower`. Errors: 400 malformed id, 404 unknown/not-done job (same as `/results`).

- [ ] **Step 1: Write the failing test**

```cpp
// cpp/tests/test_summary_endpoint.cpp
#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <drogon/HttpClient.h>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <string>

#include "pareto_nbd/db.hpp"
#include "test_server_fixture.hpp"

// Real HTTP against the shared test server (see test_results_endpoint.cpp for why).

namespace {

drogon::HttpResponsePtr GetSummary(const std::string& job_id) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/summary");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}

std::string MakeDoneJob(const drogon::orm::DbClientPtr& db) {
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    return rows[0]["id"].as<std::string>();
}

void AddRow(const drogon::orm::DbClientPtr& db, const std::string& job_id, int idx,
            double expected, double p_alive, double clv, double lower, double upper,
            const std::string& quality) {
    auto cust = db->execSqlSync(
        "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
        "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
        pareto_nbd::kDefaultBusinessId, "cust-" + job_id + "-" + std::to_string(idx), job_id);
    db->execSqlSync(
        "INSERT INTO forecast_results (job_id, customer_id, expected_purchases, p_alive, "
        "clv_point, clv_lower, clv_upper, model_params, data_quality) "
        "VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, '{}'::jsonb, $8)",
        job_id, cust[0]["id"].as<std::string>(), expected, p_alive, clv, lower, upper, quality);
}

}  // namespace

TEST_CASE("GET /jobs/{id}/summary aggregates a done job, excluding placeholder rows",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = MakeDoneJob(db);
    //             idx  exp   p_alive clv   lo    hi    quality
    AddRow(db, job_id, 0, 1.0, 0.55,  10.0, 8.0,  12.0, "ok");
    AddRow(db, job_id, 1, 3.0, 1.0,   30.0, 30.0, 30.0, "ok");
    AddRow(db, job_id, 2, 0.5, 0.25,  0.0,  0.0,  0.0,  "insufficient_history");
    AddRow(db, job_id, 3, 0.0, 0.0,   0.0,  0.0,  0.0,  "forecast_unavailable");

    auto response = GetSummary(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());

    REQUIRE(body["job_id"] == job_id);
    REQUIRE(body["n_customers"] == 4);
    REQUIRE(body["quality_counts"]["ok"] == 2);
    REQUIRE(body["quality_counts"]["insufficient_history"] == 1);
    REQUIRE(body["quality_counts"]["forecast_unavailable"] == 1);
    REQUIRE_FALSE(body["quality_counts"].contains("clv_unavailable"));

    // Valid-forecast rows are the first three: mean p_alive = (0.55 + 1.0 + 0.25) / 3.
    REQUIRE(body["mean_p_alive"].get<double>() == Catch::Approx(0.6));
    REQUIRE(body["total_expected_purchases"].get<double>() == Catch::Approx(4.5));
    // CLV only counts 'ok' rows.
    REQUIRE(body["total_clv"].get<double>() == Catch::Approx(40.0));
    REQUIRE(body["has_clv_interval"] == true);  // row 0 has lower 8 < upper 12

    // p_alive: 10 bins over [0,1]. 0.25 -> bin 3, 0.55 -> bin 6, 1.0 -> clamped into bin 10.
    const auto& pa = body["histograms"]["p_alive"];
    REQUIRE(pa["edges"].size() == 11);
    REQUIRE(pa["counts"].size() == 10);
    REQUIRE(pa["edges"][0].get<double>() == Catch::Approx(0.0));
    REQUIRE(pa["edges"][10].get<double>() == Catch::Approx(1.0));
    REQUIRE(pa["counts"][2] == 1);
    REQUIRE(pa["counts"][5] == 1);
    REQUIRE(pa["counts"][9] == 1);

    // expected_purchases: valid rows are 1.0, 3.0, 0.5; 20 bins over [0, 3.0] (width 0.15).
    // 0.5 -> bin 4, 1.0 -> bin 7, 3.0 (== max) -> clamped into bin 20.
    const auto& ep = body["histograms"]["expected_purchases"];
    REQUIRE(ep["counts"].size() == 20);
    REQUIRE(ep["edges"][20].get<double>() == Catch::Approx(3.0));
    REQUIRE(ep["counts"][3] == 1);
    REQUIRE(ep["counts"][6] == 1);
    REQUIRE(ep["counts"][19] == 1);

    // clv_point: only the two 'ok' rows (10, 30); 20 bins over [0, 30] (width 1.5).
    const auto& clv = body["histograms"]["clv_point"];
    REQUIRE(clv["counts"][6] == 1);    // 10 / 1.5 = 6.67 -> bin 7
    REQUIRE(clv["counts"][19] == 1);   // 30 == max -> bin 20
}

TEST_CASE("summary reports has_clv_interval=false when every interval is degenerate",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = MakeDoneJob(db);
    AddRow(db, job_id, 0, 1.0, 0.5, 10.0, 10.0, 10.0, "ok");

    auto response = GetSummary(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    REQUIRE(nlohmann::json::parse(response->getBody())["has_clv_interval"] == false);
}

TEST_CASE("summary of a job with no valid-forecast rows has empty-safe histograms",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    std::string job_id = MakeDoneJob(db);
    AddRow(db, job_id, 0, 0.0, 0.0, 0.0, 0.0, 0.0, "forecast_unavailable");

    auto response = GetSummary(job_id);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["n_customers"] == 1);
    REQUIRE(body["mean_p_alive"].get<double>() == Catch::Approx(0.0));
    REQUIRE(body["histograms"]["expected_purchases"]["edges"][20].get<double>() ==
            Catch::Approx(1.0));  // max <= 0 falls back to range [0, 1]
    for (const auto& c : body["histograms"]["p_alive"]["counts"]) REQUIRE(c == 0);
}

TEST_CASE("summary returns 404 for unknown/not-done jobs and 400 for a malformed id",
          "[api][summary]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    REQUIRE(GetSummary("00000000-0000-0000-0000-000000000099")->getStatusCode() ==
            drogon::k404NotFound);

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'running', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    REQUIRE(GetSummary(rows[0]["id"].as<std::string>())->getStatusCode() ==
            drogon::k404NotFound);

    REQUIRE(GetSummary("not-a-valid-uuid")->getStatusCode() == drogon::k400BadRequest);
}
```

- [ ] **Step 2: Register the test and verify it fails**

In `cpp/CMakeLists.txt`, add `tests/test_summary_endpoint.cpp` to the `unit_tests` sources right after `tests/test_results_endpoint.cpp`. Make sure Postgres and Redis are up (`docker compose up -d` from the repo root), then:

Run: `cmake --build cpp/build --config Release --target unit_tests` then `cpp/build/Release/unit_tests "[summary]"` (adjust to the preset's output dir; see `cpp/CMakePresets.json`)
Expected: build succeeds; the three HTTP test cases FAIL (the route does not exist → 404 where 200 is required).

- [ ] **Step 3: Implement the route**

In `cpp/src/api_routes.cpp`, add `#include <algorithm>`, `#include <cstdint>` and `#include <vector>` to the includes, then add this helper inside the existing anonymous namespace (after `FormatDouble`):

```cpp
// Builds {"edges": [...], "counts": [...]} for one forecast_results column of one job.
// `column` and `quality_clause` are TRUSTED string literals supplied by this file's own call
// sites below -- never request data -- so concatenating them into the SQL is safe; the job id
// and numeric parameters are always bound. Bin edges run from 0 to `hi`; width_bucket returns
// bucket `bins + 1` for a value exactly equal to `hi`, so the result is clamped into
// [1, bins] (otherwise the maximum value would silently fall out of the chart).
// $2::float8 / $3::int casts are required, same wire-format reason as /results's LIMIT/OFFSET.
nlohmann::json BuildHistogram(const drogon::orm::DbClientPtr& db, const std::string& job_id,
                              const std::string& column, const std::string& quality_clause,
                              int bins, const double* fixed_hi) {
    double hi = 1.0;
    if (fixed_hi != nullptr) {
        hi = *fixed_hi;
    } else {
        auto max_rows = db->execSqlSync(
            "SELECT COALESCE(max(fr." + column + "), 0)::float8 AS m FROM forecast_results fr "
            "WHERE fr.job_id = $1::uuid AND " + quality_clause,
            job_id);
        hi = max_rows[0]["m"].as<double>();
        if (!(hi > 0.0)) hi = 1.0;  // empty or all-zero column: any positive range will do
    }

    auto rows = db->execSqlSync(
        "SELECT LEAST(GREATEST(width_bucket(fr." + column +
            ", 0::float8, $2::float8, $3::int), 1), $3::int) AS b, count(*)::bigint AS n "
        "FROM forecast_results fr WHERE fr.job_id = $1::uuid AND " + quality_clause +
            " GROUP BY b ORDER BY b",
        job_id, hi, bins);

    std::vector<int64_t> counts(static_cast<size_t>(bins), 0);
    for (const auto& row : rows) {
        counts[static_cast<size_t>(row["b"].as<int>() - 1)] = row["n"].as<int64_t>();
    }
    std::vector<double> edges;
    for (int i = 0; i <= bins; ++i) edges.push_back(hi * i / bins);
    return {{"edges", edges}, {"counts", counts}};
}

}  // namespace
```

(The `}  // namespace` line above replaces the existing closing brace of the anonymous namespace — keep exactly one.)

Then add the route inside `RegisterApiRoutes`, immediately after the `/jobs/{id}/results` registration:

```cpp
    // GET /jobs/{id}/summary: cohort-level aggregates and histograms for the dashboard (Phase 5
    // frontend). Computed in SQL so the browser never has to download every customer row.
    // Same id validation and 404-until-done gate as /results. Placeholder rows (see
    // data_quality in worker.cpp) are excluded from every statistic they would corrupt:
    // forecast statistics use ok + insufficient_history rows, CLV statistics use ok rows only.
    drogon::app().registerHandler(
        "/jobs/{id}/summary",
        [db](const drogon::HttpRequestPtr&,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback,
             const std::string& id) {
            if (!IsValidUuidFormat(id)) {
                callback(
                    JsonResponse({{"error", "invalid job id format"}}, drogon::k400BadRequest));
                return;
            }
            auto job_rows = db->execSqlSync("SELECT status FROM jobs WHERE id = $1::uuid", id);
            if (job_rows.empty() || job_rows[0]["status"].as<std::string>() != "done") {
                callback(
                    JsonResponse({{"error", "job not found or not done"}}, drogon::k404NotFound));
                return;
            }

            const std::string kValidForecast =
                "fr.data_quality IN ('ok','insufficient_history')";
            const std::string kValidClv = "fr.data_quality = 'ok'";

            auto agg = db->execSqlSync(
                "SELECT count(*)::bigint AS n, "
                "COALESCE(avg(fr.p_alive) FILTER (WHERE " + kValidForecast + "), 0)::float8 AS mean_p, "
                "COALESCE(sum(fr.expected_purchases) FILTER (WHERE " + kValidForecast + "), 0)::float8 AS sum_ep, "
                "COALESCE(sum(fr.clv_point) FILTER (WHERE " + kValidClv + "), 0)::float8 AS sum_clv, "
                "COALESCE(bool_or(fr.clv_upper > fr.clv_lower), false) AS has_interval "
                "FROM forecast_results fr WHERE fr.job_id = $1::uuid",
                id);

            nlohmann::json quality_counts = nlohmann::json::object();
            auto q_rows = db->execSqlSync(
                "SELECT data_quality, count(*)::bigint AS n FROM forecast_results "
                "WHERE job_id = $1::uuid GROUP BY data_quality",
                id);
            for (const auto& row : q_rows) {
                quality_counts[row["data_quality"].as<std::string>()] = row["n"].as<int64_t>();
            }

            const double p_alive_hi = 1.0;
            nlohmann::json body{
                {"job_id", id},
                {"n_customers", agg[0]["n"].as<int64_t>()},
                {"quality_counts", quality_counts},
                {"mean_p_alive", agg[0]["mean_p"].as<double>()},
                {"total_expected_purchases", agg[0]["sum_ep"].as<double>()},
                {"total_clv", agg[0]["sum_clv"].as<double>()},
                {"has_clv_interval", agg[0]["has_interval"].as<bool>()},
                {"histograms",
                 {{"p_alive", BuildHistogram(db, id, "p_alive", kValidForecast, 10, &p_alive_hi)},
                  {"expected_purchases",
                   BuildHistogram(db, id, "expected_purchases", kValidForecast, 20, nullptr)},
                  {"clv_point", BuildHistogram(db, id, "clv_point", kValidClv, 20, nullptr)}}}};
            callback(JsonResponse(body, drogon::k200OK));
        },
        {drogon::Get});
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cmake --build cpp/build --config Release --target unit_tests` then `cpp/build/Release/unit_tests "[summary],[results],[jobs]"`
Expected: PASS (the new tests plus the untouched `/results` and `/jobs` tests). If a `width_bucket` float edge makes a `counts[...]` index assertion off by one, the fixture values above were chosen to sit mid-bucket; do not weaken the assertion — check the bin arithmetic in the comments.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_routes.cpp cpp/tests/test_summary_endpoint.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): GET /jobs/{id}/summary -- cohort aggregates and histograms"
```

---

### Task 2: Backend — server-side sort, quality filter and ID search on `/results`

The spec wants a sortable/filterable per-customer table; sorting only the current page client-side would be misleading, so the API does it.

**Files:**
- Modify: `cpp/src/api_routes.cpp` (the `/jobs/{id}/results` handler only)
- Modify: `cpp/tests/test_results_endpoint.cpp` (append test cases)

**Interfaces:**
- Consumes: the existing `/results` handler and its `page` / `page_size` handling (unchanged).
- Produces: new optional query params on `GET /jobs/{id}/results`:
  - `sort` ∈ `customer_id` (default) | `expected_purchases` | `p_alive` | `clv_point` | `data_quality`
  - `order` ∈ `asc` (default) | `desc`
  - `quality` ∈ `ok` | `insufficient_history` | `forecast_unavailable` | `clv_unavailable` (omitted = all)
  - `q` — case-insensitive substring match on the customer id (omitted/empty = all)
  Invalid `sort` / `order` / `quality` → `400 {"error": "..."}`. `total` in the response reflects the filters. Ties always break on `customer_id` ascending so paging is stable.

- [ ] **Step 1: Write the failing tests**

Append to `cpp/tests/test_results_endpoint.cpp`. First extend the helper at the top (replace `GetResults`) so it can pass arbitrary parameters:

```cpp
drogon::HttpResponsePtr GetResultsWith(const std::string& job_id,
                                        const std::map<std::string, std::string>& params) {
    auto client = drogon::HttpClient::newHttpClient(pareto_nbd::test::TestServerBaseUrl());
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Get);
    req->setPath("/jobs/" + job_id + "/results");
    for (const auto& [k, v] : params) req->setParameter(k, v);
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    return response;
}
```

(add `#include <map>`), then the test cases:

```cpp
TEST_CASE("GET /jobs/{id}/results sorts, filters by quality, and searches by customer id",
          "[api][results]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    // ids sort lexically a < b < c; clv_point ascending is b (5) < c (20) < a (50).
    struct R { const char* suffix; double p; double clv; const char* q; };
    const R rows[] = {{"a", 0.9, 50.0, "ok"},
                      {"b", 0.1, 5.0, "ok"},
                      {"c", 0.5, 20.0, "insufficient_history"}};
    for (const auto& r : rows) {
        auto cust = db->execSqlSync(
            "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
            "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
            pareto_nbd::kDefaultBusinessId, "Cust-" + job_id + "-" + r.suffix, job_id);
        db->execSqlSync(
            "INSERT INTO forecast_results (job_id, customer_id, expected_purchases, p_alive, "
            "clv_point, clv_lower, clv_upper, model_params, data_quality) "
            "VALUES ($1::uuid, $2::uuid, 1.0, $3, $4, $4, $4, '{}'::jsonb, $5)",
            job_id, cust[0]["id"].as<std::string>(), r.p, r.clv, std::string(r.q));
    }
    auto id_of = [&](const char* s) { return "Cust-" + job_id + "-" + s; };

    auto asc = nlohmann::json::parse(
        GetResultsWith(job_id, {{"sort", "clv_point"}, {"order", "asc"}})->getBody());
    REQUIRE(asc["customers"][0]["customer_id"] == id_of("b"));
    REQUIRE(asc["customers"][2]["customer_id"] == id_of("a"));

    auto desc = nlohmann::json::parse(
        GetResultsWith(job_id, {{"sort", "p_alive"}, {"order", "desc"}})->getBody());
    REQUIRE(desc["customers"][0]["customer_id"] == id_of("a"));
    REQUIRE(desc["customers"][2]["customer_id"] == id_of("b"));

    // Default (no sort params) is unchanged: customer_id ascending.
    auto dflt = nlohmann::json::parse(GetResultsWith(job_id, {})->getBody());
    REQUIRE(dflt["customers"][0]["customer_id"] == id_of("a"));

    // quality filter: total reflects the filter, not the whole job.
    auto only_ok = nlohmann::json::parse(GetResultsWith(job_id, {{"quality", "ok"}})->getBody());
    REQUIRE(only_ok["total"] == 2);
    REQUIRE(only_ok["customers"].size() == 2);

    // q: case-insensitive substring on customer id; this job's ids embed the (unique) job id.
    auto found = nlohmann::json::parse(
        GetResultsWith(job_id, {{"q", "cust-" + job_id + "-C"}})->getBody());
    REQUIRE(found["total"] == 1);
    REQUIRE(found["customers"][0]["customer_id"] == id_of("c"));

    // filters compose with paging.
    auto paged = nlohmann::json::parse(
        GetResultsWith(job_id, {{"quality", "ok"}, {"sort", "clv_point"}, {"order", "desc"},
                                {"page", "2"}, {"page_size", "1"}})->getBody());
    REQUIRE(paged["total"] == 2);
    REQUIRE(paged["customers"].size() == 1);
    REQUIRE(paged["customers"][0]["customer_id"] == id_of("b"));
}

TEST_CASE("GET /jobs/{id}/results rejects invalid sort, order and quality values",
          "[api][results]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') "
        "RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    REQUIRE(GetResultsWith(job_id, {{"sort", "p_alive; DROP TABLE jobs"}})->getStatusCode() ==
            drogon::k400BadRequest);
    REQUIRE(GetResultsWith(job_id, {{"order", "sideways"}})->getStatusCode() ==
            drogon::k400BadRequest);
    REQUIRE(GetResultsWith(job_id, {{"quality", "great"}})->getStatusCode() ==
            drogon::k400BadRequest);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cmake --build cpp/build --config Release --target unit_tests` then `cpp/build/Release/unit_tests "[results]"`
Expected: the two new cases FAIL (sort params ignored → wrong order; bad values return 200). Existing `/results` cases still pass.

- [ ] **Step 3: Implement**

In the `/jobs/{id}/results` handler of `cpp/src/api_routes.cpp`, add `#include <map>` and `#include <set>` at the top of the file, then, after the existing `page_size` parsing and before the job-status lookup, insert:

```cpp
            // Sort/filter params. `sort` is mapped through a fixed whitelist -- the ORDER BY
            // clause is the only part of this query built by string concatenation, and only
            // ever from these literals, never from request text.
            static const std::map<std::string, std::string> kSortColumns = {
                {"customer_id", "c.external_customer_id"},
                {"expected_purchases", "fr.expected_purchases"},
                {"p_alive", "fr.p_alive"},
                {"clv_point", "fr.clv_point"},
                {"data_quality", "fr.data_quality"}};
            static const std::set<std::string> kQualities = {
                "ok", "insufficient_history", "forecast_unavailable", "clv_unavailable"};

            std::string sort = req->getParameter("sort");
            if (sort.empty()) sort = "customer_id";
            auto sort_it = kSortColumns.find(sort);
            if (sort_it == kSortColumns.end()) {
                callback(JsonResponse({{"error", "invalid sort column"}}, drogon::k400BadRequest));
                return;
            }
            std::string order = req->getParameter("order");
            if (order.empty()) order = "asc";
            if (order != "asc" && order != "desc") {
                callback(JsonResponse({{"error", "order must be asc or desc"}},
                                       drogon::k400BadRequest));
                return;
            }
            const std::string quality = req->getParameter("quality");
            if (!quality.empty() && kQualities.count(quality) == 0) {
                callback(JsonResponse({{"error", "invalid quality filter"}},
                                       drogon::k400BadRequest));
                return;
            }
            const std::string search = req->getParameter("q");
```

Replace the existing count query and page query with filtered versions (both use `$2` = quality, `$3` = search; empty string means "no filter"; `position(lower(x) in lower(y))` is a plain substring test with no LIKE-wildcard escaping to get wrong):

```cpp
            const std::string where =
                "fr.job_id = $1::uuid AND ($2::text = '' OR fr.data_quality = $2::text) "
                "AND position(lower($3::text) in lower(c.external_customer_id)) > 0";

            auto count_rows = db->execSqlSync(
                "SELECT count(*) FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
                "WHERE " + where,
                id, quality, search);
            int64_t total = count_rows[0]["count"].as<int64_t>();

            auto rows = db->execSqlSync(
                "SELECT c.external_customer_id, fr.expected_purchases, fr.p_alive, "
                "fr.clv_point, fr.clv_lower, fr.clv_upper, fr.data_quality "
                "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
                "WHERE " + where + " ORDER BY " + sort_it->second + " " + order +
                    ", c.external_customer_id ASC LIMIT $4::int OFFSET $5::int",
                id, quality, search, page_size, (page - 1) * page_size);
```

`order` is safe to concatenate: it was validated to be exactly `asc` or `desc` above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cmake --build cpp/build --config Release --target unit_tests` then `cpp/build/Release/unit_tests "[results],[summary],[export]"`
Expected: PASS, including all pre-existing `/results` and `/export` cases.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_routes.cpp cpp/tests/test_results_endpoint.cpp
git commit -m "feat(cpp): /jobs/{id}/results sort, quality filter and customer-id search"
```

---

### Task 3: Scaffold `frontend/` — SvelteKit, Vitest, and the `/api` proxy

**Files:**
- Create: `frontend/package.json`, `frontend/svelte.config.js`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/app.html`, `frontend/src/app.d.ts`, `frontend/src/hooks.server.ts`, `frontend/src/lib/server/proxy.ts`, `frontend/src/routes/+layout.svelte`, `frontend/src/routes/+page.svelte` (placeholder, replaced in Task 6)
- Test: `frontend/tests/proxy.test.ts`
- Modify: `.gitignore` (append `frontend/node_modules/`, `frontend/.svelte-kit/`, `frontend/build/`)

**Interfaces:**
- Produces: `proxyRequest(request: Request, apiPath: string, search: string, base: string, fetchFn?: typeof fetch): Promise<Response>` in `src/lib/server/proxy.ts` — forwards method, headers (minus hop-by-hop ones) and streaming body to `base + apiPath + search`; returns the upstream response with `content-encoding`/`transfer-encoding`/`content-length` removed. `hooks.server.ts` calls it for any path starting `/api/` with `apiPath = pathname.slice(4)` (so `/api/jobs/x` → `/jobs/x`).

- [ ] **Step 1: Create the project files**

`frontend/package.json`:
```json
{
  "name": "pareto-nbd-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "start": "BODY_SIZE_LIMIT=100M node build",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@sveltejs/adapter-node": "^5.2.0",
    "@sveltejs/kit": "^2.15.0",
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/svelte": "^5.2.0",
    "jsdom": "^25.0.0",
    "svelte": "^5.16.0",
    "svelte-check": "^4.1.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^3.0.0"
  },
  "dependencies": {
    "echarts": "^5.5.0"
  }
}
```

`frontend/svelte.config.js`:
```js
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  kit: { adapter: adapter() }
};
```

`frontend/vite.config.ts`:
```ts
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['tests/setup.ts']
  }
});
```

`frontend/tsconfig.json`:
```json
{
  "extends": "./.svelte-kit/tsconfig.json",
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "strict": true,
    "moduleResolution": "bundler"
  }
}
```

`frontend/src/app.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CLV Forecasts</title>
    %sveltekit.head%
  </head>
  <body data-sveltekit-preload-data="hover">
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
```

`frontend/src/app.d.ts`:
```ts
declare global {
  namespace App {}
}
export {};
```

`frontend/tests/setup.ts`:
```ts
import '@testing-library/jest-dom/vitest';
```

`frontend/src/routes/+layout.svelte`:
```svelte
<script lang="ts">
  let { children } = $props();
</script>

<header class="bar">
  <a href="/" class="brand">CLV Forecasts</a>
</header>
<main>{@render children()}</main>

<style>
  :global(:root) {
    --bg: #f7f8fa; --fg: #14181f; --muted: #5b6573; --card: #ffffff;
    --line: #dde1e7; --accent: #2563eb; --warn: #b45309; --bad: #b91c1c; --good: #15803d;
  }
  :global(body) {
    margin: 0; background: var(--bg); color: var(--fg);
    font: 16px/1.5 system-ui, -apple-system, 'Segoe UI', sans-serif;
  }
  .bar { background: var(--card); border-bottom: 1px solid var(--line); padding: 0.75rem 1.5rem; }
  .brand { font-weight: 600; color: var(--fg); text-decoration: none; }
  main { max-width: 72rem; margin: 0 auto; padding: 1.5rem; }
</style>
```

`frontend/src/routes/+page.svelte` (placeholder):
```svelte
<h1>Upload a transaction log</h1>
```

Append to the repo-root `.gitignore`:
```
# Frontend
frontend/node_modules/
frontend/.svelte-kit/
frontend/build/
# The Python "lib/" rule earlier in this file would otherwise ignore the SvelteKit source tree
!frontend/src/lib/
```

The last line is **required**: the repo's Python `.gitignore` contains `lib/`, which silently ignores `frontend/src/lib/` — `git add` then skips those files without an obvious error. After every commit in this plan, `git show --stat HEAD` should list the `src/lib/...` files you meant to add.

- [ ] **Step 2: Write the failing proxy test**

```ts
// frontend/tests/proxy.test.ts
import { describe, expect, it, vi } from 'vitest';
import { proxyRequest } from '../src/lib/server/proxy';

describe('proxyRequest', () => {
  it('forwards method, path, query and body to the API base', async () => {
    const fetchFn = vi.fn(async () => new Response('{"job_id":"abc"}', { status: 200 }));
    const req = new Request('http://app.test/api/uploads', {
      method: 'POST',
      headers: { 'content-type': 'text/csv', host: 'app.test', connection: 'keep-alive' },
      body: 'customer_id,transaction_date\n1,2024-01-01\n'
    });

    const res = await proxyRequest(req, '/uploads', '?x=1', 'http://api.test:8080', fetchFn);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ job_id: 'abc' });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://api.test:8080/uploads?x=1');
    expect(init.method).toBe('POST');
    const sent = new Headers(init.headers);
    expect(sent.get('content-type')).toBe('text/csv');
    expect(sent.has('host')).toBe(false);        // hop-by-hop / origin-specific headers dropped
    expect(sent.has('connection')).toBe(false);
    expect((init as RequestInit & { duplex?: string }).duplex).toBe('half');
  });

  it('sends no body for GET and strips encoding headers from the response', async () => {
    const fetchFn = vi.fn(
      async () =>
        new Response('a,b\n', {
          status: 200,
          headers: { 'content-type': 'text/csv', 'content-encoding': 'gzip', 'content-length': '4' }
        })
    );
    const req = new Request('http://app.test/api/jobs/1/export.csv');

    const res = await proxyRequest(req, '/jobs/1/export.csv', '', 'http://api.test:8080', fetchFn);

    const init = (fetchFn.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.body).toBeUndefined();
    expect(res.headers.get('content-type')).toBe('text/csv');
    expect(res.headers.has('content-encoding')).toBe(false);
    expect(res.headers.has('content-length')).toBe(false);
  });

  it('returns 502 with a JSON error when the API is unreachable', async () => {
    const fetchFn = vi.fn(async () => {
      throw new TypeError('fetch failed');
    });
    const res = await proxyRequest(
      new Request('http://app.test/api/jobs/1'), '/jobs/1', '', 'http://api.test:8080', fetchFn
    );
    expect(res.status).toBe(502);
    expect((await res.json()).error).toMatch(/unreachable/i);
  });
});
```

- [ ] **Step 3: Install and run the test to verify it fails**

Run (from `frontend/`): `npm install` then `npx svelte-kit sync` then `npx vitest run tests/proxy.test.ts`
Expected: FAIL — cannot resolve `../src/lib/server/proxy`. (If `npm install` reports a peer-dependency conflict between Vite / the Svelte plugin / Vitest, align them on the versions npm suggests; the plan targets Vite 6 + plugin 5 + Vitest 3.)

- [ ] **Step 4: Implement the proxy and the hook**

`frontend/src/lib/server/proxy.ts`:
```ts
// Headers that describe the browser<->frontend hop, not the frontend<->API hop.
const DROP_REQUEST = new Set(['host', 'connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'content-length']);
// fetch() has already decoded the upstream body, so these would now be wrong.
const DROP_RESPONSE = new Set(['content-encoding', 'content-length', 'transfer-encoding', 'connection']);

export async function proxyRequest(
  request: Request,
  apiPath: string,
  search: string,
  base: string,
  fetchFn: typeof fetch = fetch
): Promise<Response> {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!DROP_REQUEST.has(key.toLowerCase())) headers.set(key, value);
  });

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  const init: RequestInit & { duplex?: 'half' } = {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    duplex: 'half' // required by Node's fetch when streaming a request body
  };

  let upstream: Response;
  try {
    upstream = await fetchFn(base + apiPath + search, init);
  } catch {
    return new Response(JSON.stringify({ error: 'API unreachable' }), {
      status: 502,
      headers: { 'content-type': 'application/json' }
    });
  }

  const out = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!DROP_RESPONSE.has(key.toLowerCase())) out.set(key, value);
  });
  return new Response(upstream.body, { status: upstream.status, headers: out });
}
```

`frontend/src/hooks.server.ts`:
```ts
import type { Handle } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { proxyRequest } from '$lib/server/proxy';

// The Drogon API has no CORS support, so the browser only ever talks to this server's own
// origin under /api/*, and this hook forwards those requests to the real API.
export const handle: Handle = async ({ event, resolve }) => {
  if (event.url.pathname.startsWith('/api/')) {
    const base = env.API_BASE_URL ?? 'http://localhost:8080';
    return proxyRequest(event.request, event.url.pathname.slice('/api'.length), event.url.search, base);
  }
  return resolve(event);
};
```

- [ ] **Step 5: Run tests, check the app boots, commit**

Run (from `frontend/`): `npx vitest run` — Expected: PASS (3 tests).
Run: `npm run check` — Expected: 0 errors.
Run: `npm run dev` in the background, `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` → `200`; with the C++ `api_server` running, `curl -s http://localhost:5173/api/healthz` → `ok`. Stop the dev server.

```bash
git add frontend .gitignore
git commit -m "feat(frontend): scaffold SvelteKit app with Vitest and an /api proxy to the Drogon API"
```

(Do not commit `frontend/node_modules` or `package-lock.json` exclusions — **do** commit `frontend/package-lock.json`.)

---

### Task 4: Typed API client

**Files:**
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`
- Test: `frontend/tests/api.test.ts`

**Interfaces:**
- Produces (`types.ts`):
```ts
export type JobStatus = 'queued' | 'running' | 'done' | 'failed';
export type DataQuality = 'ok' | 'insufficient_history' | 'forecast_unavailable' | 'clv_unavailable';
export interface JobInfo { id: string; status: JobStatus; error_reason: string | null }
export interface CustomerRow {
  customer_id: string; expected_purchases: number; p_alive: number;
  clv_point: number; clv_lower: number; clv_upper: number; data_quality: DataQuality;
}
export type SortKey = 'customer_id' | 'expected_purchases' | 'p_alive' | 'clv_point' | 'data_quality';
export interface ResultsQuery {
  page: number; pageSize: number; sort: SortKey; order: 'asc' | 'desc';
  quality: DataQuality | ''; q: string;
}
export interface ResultsPage { job_id: string; page: number; page_size: number; total: number; customers: CustomerRow[] }
export interface Histogram { edges: number[]; counts: number[] }
export interface JobSummary {
  job_id: string; n_customers: number; quality_counts: Partial<Record<DataQuality, number>>;
  mean_p_alive: number; total_expected_purchases: number; total_clv: number; has_clv_interval: boolean;
  histograms: { p_alive: Histogram; expected_purchases: Histogram; clv_point: Histogram };
}
```
- Produces (`api.ts`):
```ts
export class ApiError extends Error { status: number; constructor(status: number, message: string) }
export function createApi(fetchFn?: typeof fetch): {
  uploadCsv(file: File): Promise<{ job_id: string }>;
  getJob(id: string): Promise<JobInfo>;
  getResults(id: string, query: ResultsQuery): Promise<ResultsPage>;
  getSummary(id: string): Promise<JobSummary>;
};
export function exportUrl(id: string): string;   // '/api/jobs/{id}/export.csv'
export const api: ReturnType<typeof createApi>;  // default instance bound to global fetch
```
  Every method throws `ApiError(status, message)`; `message` is the API's `{"error": ...}` text when present, otherwise `"Request failed (HTTP <status>)"`. Network failures throw `ApiError(0, "Could not reach the server")`.

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/api.test.ts
import { describe, expect, it, vi } from 'vitest';
import { ApiError, createApi, exportUrl } from '../src/lib/api';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

describe('api client', () => {
  it('uploads the raw CSV as the request body with text/csv', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'job-1' }));
    const file = new File(['customer_id,transaction_date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' });

    const out = await createApi(fetchFn).uploadCsv(file);

    expect(out).toEqual({ job_id: 'job-1' });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/uploads');
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('content-type')).toBe('text/csv');
    expect(init.body).toBe(file);
  });

  it('surfaces the API error message for a 400 upload', async () => {
    const fetchFn = vi.fn(async () => json({ error: "missing required column 'customer_id'" }, 400));
    await expect(createApi(fetchFn).uploadCsv(new File(['x'], 'a.csv'))).rejects.toMatchObject({
      name: 'ApiError', status: 400, message: "missing required column 'customer_id'"
    });
  });

  it('falls back to a generic message when the error body is not JSON', async () => {
    const fetchFn = vi.fn(async () => new Response('<html>boom</html>', { status: 500 }));
    const err = await createApi(fetchFn).getJob('abc').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(500);
    expect(err.message).toBe('Request failed (HTTP 500)');
  });

  it('maps a network failure to ApiError status 0', async () => {
    const fetchFn = vi.fn(async () => { throw new TypeError('fetch failed'); });
    await expect(createApi(fetchFn).getJob('abc')).rejects.toMatchObject({
      status: 0, message: 'Could not reach the server'
    });
  });

  it('gets a job', async () => {
    const fetchFn = vi.fn(async () => json({ id: 'j', status: 'running', error_reason: null }));
    expect(await createApi(fetchFn).getJob('j')).toEqual({ id: 'j', status: 'running', error_reason: null });
    expect((fetchFn.mock.calls[0] as unknown as [string])[0]).toBe('/api/jobs/j');
  });

  it('builds the results query string, omitting empty filters', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'j', page: 2, page_size: 25, total: 0, customers: [] }));
    await createApi(fetchFn).getResults('j', {
      page: 2, pageSize: 25, sort: 'clv_point', order: 'desc', quality: '', q: ''
    });
    const url = new URL((fetchFn.mock.calls[0] as unknown as [string])[0], 'http://x');
    expect(url.pathname).toBe('/api/jobs/j/results');
    expect(Object.fromEntries(url.searchParams)).toEqual({
      page: '2', page_size: '25', sort: 'clv_point', order: 'desc'
    });

    await createApi(fetchFn).getResults('j', {
      page: 1, pageSize: 50, sort: 'customer_id', order: 'asc', quality: 'ok', q: 'a&b'
    });
    const url2 = new URL((fetchFn.mock.calls[1] as unknown as [string])[0], 'http://x');
    expect(url2.searchParams.get('quality')).toBe('ok');
    expect(url2.searchParams.get('q')).toBe('a&b');   // properly encoded, not split
  });

  it('gets the summary and builds the export URL', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'j', n_customers: 3 }));
    await createApi(fetchFn).getSummary('j');
    expect((fetchFn.mock.calls[0] as unknown as [string])[0]).toBe('/api/jobs/j/summary');
    expect(exportUrl('j')).toBe('/api/jobs/j/export.csv');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/api.test.ts`
Expected: FAIL — cannot resolve `../src/lib/api`.

- [ ] **Step 3: Implement**

Write `frontend/src/lib/types.ts` exactly as in **Interfaces** above, then:

```ts
// frontend/src/lib/api.ts
import type { JobInfo, JobSummary, ResultsPage, ResultsQuery } from './types';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.ok) return (await res.json()) as T;
  let message = `Request failed (HTTP ${res.status})`;
  try {
    const body = await res.json();
    if (body && typeof body.error === 'string') message = body.error;
  } catch {
    /* non-JSON error body: keep the generic message */
  }
  throw new ApiError(res.status, message);
}

export function createApi(fetchFn: typeof fetch = (...a) => fetch(...a)) {
  async function call<T>(url: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetchFn(url, init);
    } catch {
      throw new ApiError(0, 'Could not reach the server');
    }
    return parse<T>(res);
  }

  return {
    uploadCsv: (file: File) =>
      call<{ job_id: string }>('/api/uploads', {
        method: 'POST',
        headers: { 'content-type': 'text/csv' },
        body: file
      }),
    getJob: (id: string) => call<JobInfo>(`/api/jobs/${encodeURIComponent(id)}`),
    getResults: (id: string, q: ResultsQuery) => {
      const p = new URLSearchParams({
        page: String(q.page), page_size: String(q.pageSize), sort: q.sort, order: q.order
      });
      if (q.quality) p.set('quality', q.quality);
      if (q.q) p.set('q', q.q);
      return call<ResultsPage>(`/api/jobs/${encodeURIComponent(id)}/results?${p}`);
    },
    getSummary: (id: string) => call<JobSummary>(`/api/jobs/${encodeURIComponent(id)}/summary`)
  };
}

export const exportUrl = (id: string) => `/api/jobs/${encodeURIComponent(id)}/export.csv`;

export const api = createApi();
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` — Expected: PASS (proxy + api tests). `npm run check` — 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/tests/api.test.ts
git commit -m "feat(frontend): typed API client with error mapping"
```

---

### Task 5: Client-side CSV header validation and formatting helpers

Spec §4.1: "client-side header/type validation before the file is sent." Only the first 64 KB is read — files can be 100 MB.

**Files:**
- Create: `frontend/src/lib/csvHeader.ts`, `frontend/src/lib/format.ts`
- Test: `frontend/tests/csvHeader.test.ts`, `frontend/tests/format.test.ts`

**Interfaces:**
- Produces (`csvHeader.ts`):
```ts
export interface HeaderCheck { ok: boolean; errors: string[]; hasAmount: boolean; columns: string[] }
export function parseHeaderLine(text: string): string[];       // first line, BOM-stripped, RFC-4180 quotes
export function validateHeader(columns: string[]): HeaderCheck; // required: customer_id, transaction_date
export function validateFile(file: File): Promise<HeaderCheck>; // size/extension checks + reads first 64 KB
```
- Produces (`format.ts`):
```ts
export const formatInt: (n: number) => string;          // 1234567 -> "1,234,567"
export const formatMoney: (n: number) => string;        // 1234.5 -> "1,234.50"
export const formatPct: (p: number) => string;          // 0.6234 -> "62.3%"
export const formatNum: (n: number) => string;          // up to 3 significant digits, "1.23" / "123" / "0.0123"
export const QUALITY_LABEL: Record<DataQuality, string>;
export const QUALITY_HELP: Record<DataQuality, string>;
```

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/csvHeader.test.ts
import { describe, expect, it } from 'vitest';
import { parseHeaderLine, validateFile, validateHeader } from '../src/lib/csvHeader';

describe('parseHeaderLine', () => {
  it('splits the first line only', () => {
    expect(parseHeaderLine('customer_id,transaction_date,amount\n1,2024-01-01,5\n')).toEqual([
      'customer_id', 'transaction_date', 'amount'
    ]);
  });
  it('strips a UTF-8 BOM and handles CRLF', () => {
    expect(parseHeaderLine('﻿customer_id,transaction_date\r\n1,2024-01-01')).toEqual([
      'customer_id', 'transaction_date'
    ]);
  });
  it('handles quoted fields containing commas and escaped quotes', () => {
    expect(parseHeaderLine('"a,b","say ""hi""",c')).toEqual(['a,b', 'say "hi"', 'c']);
  });
  it('returns a single empty column for empty input', () => {
    expect(parseHeaderLine('')).toEqual(['']);
  });
});

describe('validateHeader', () => {
  it('accepts the required columns, with or without amount, in any order', () => {
    expect(validateHeader(['transaction_date', 'customer_id'])).toMatchObject({ ok: true, hasAmount: false });
    expect(validateHeader(['customer_id', 'transaction_date', 'amount', 'extra'])).toMatchObject({
      ok: true, hasAmount: true
    });
  });
  it('reports each missing required column', () => {
    const r = validateHeader(['foo', 'bar']);
    expect(r.ok).toBe(false);
    expect(r.errors).toEqual([
      'Missing required column "customer_id".',
      'Missing required column "transaction_date".'
    ]);
  });
  it('hints when a column differs only by case (the server is case-sensitive)', () => {
    const r = validateHeader(['Customer_ID', 'transaction_date']);
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toBe(
      'Found "Customer_ID" — column names are case-sensitive; rename it to "customer_id".'
    );
  });
});

describe('validateFile', () => {
  const csv = (text: string, name = 'log.csv') => new File([text], name, { type: 'text/csv' });

  it('passes a good file', async () => {
    expect((await validateFile(csv('customer_id,transaction_date\n1,2024-01-01\n'))).ok).toBe(true);
  });
  it('rejects an empty file', async () => {
    const r = await validateFile(csv(''));
    expect(r.ok).toBe(false);
    expect(r.errors).toEqual(['The file is empty.']);
  });
  it('rejects a non-CSV file by extension', async () => {
    const r = await validateFile(new File(['customer_id,transaction_date'], 'log.xlsx'));
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toBe('Please choose a .csv file.');
  });
  it('rejects a file with a bad header', async () => {
    const r = await validateFile(csv('id,date\n1,2024-01-01\n'));
    expect(r.ok).toBe(false);
    expect(r.errors).toHaveLength(2);
  });
});
```

```ts
// frontend/tests/format.test.ts
import { describe, expect, it } from 'vitest';
import { QUALITY_HELP, QUALITY_LABEL, formatInt, formatMoney, formatNum, formatPct } from '../src/lib/format';

describe('format', () => {
  it('formats integers, money and percentages', () => {
    expect(formatInt(1234567)).toBe('1,234,567');
    expect(formatMoney(1234.5)).toBe('1,234.50');
    expect(formatPct(0.6234)).toBe('62.3%');
  });
  it('formats numbers to ~3 significant digits', () => {
    expect(formatNum(1.2345)).toBe('1.23');
    expect(formatNum(123.456)).toBe('123');
    expect(formatNum(0.012345)).toBe('0.0123');
    expect(formatNum(0)).toBe('0');
  });
  it('has a label and help text for every data-quality value', () => {
    for (const q of ['ok', 'insufficient_history', 'forecast_unavailable', 'clv_unavailable'] as const) {
      expect(QUALITY_LABEL[q]).toBeTruthy();
      expect(QUALITY_HELP[q]).toBeTruthy();
    }
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/csvHeader.test.ts tests/format.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/csvHeader.ts
// Mirrors the server's schema check (cpp/src/ingest.cpp): required columns are exact,
// case-sensitive names; `amount` is optional. This only exists to fail fast, before a
// potentially huge upload -- the server stays the source of truth.
const REQUIRED = ['customer_id', 'transaction_date'] as const;
const HEADER_BYTES = 64 * 1024;

export interface HeaderCheck {
  ok: boolean;
  errors: string[];
  hasAmount: boolean;
  columns: string[];
}

export function parseHeaderLine(text: string): string[] {
  const line = text.replace(/^﻿/, '').split(/\r\n|\n|\r/, 1)[0] ?? '';
  const cols: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; } else inQuotes = false;
      } else cur += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ',') { cols.push(cur); cur = ''; }
    else cur += ch;
  }
  cols.push(cur);
  return cols;
}

export function validateHeader(columns: string[]): HeaderCheck {
  const errors: string[] = [];
  for (const name of REQUIRED) {
    if (columns.includes(name)) continue;
    const near = columns.find((c) => c.trim().toLowerCase() === name);
    errors.push(
      near !== undefined
        ? `Found "${near}" — column names are case-sensitive; rename it to "${name}".`
        : `Missing required column "${name}".`
    );
  }
  return { ok: errors.length === 0, errors, hasAmount: columns.includes('amount'), columns };
}

function readSlice(file: File, bytes: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file.slice(0, bytes));
  });
}

export async function validateFile(file: File): Promise<HeaderCheck> {
  const fail = (msg: string): HeaderCheck => ({ ok: false, errors: [msg], hasAmount: false, columns: [] });
  if (file.size === 0) return fail('The file is empty.');
  if (!/\.csv$/i.test(file.name) && file.type !== 'text/csv') return fail('Please choose a .csv file.');
  return validateHeader(parseHeaderLine(await readSlice(file, HEADER_BYTES)));
}
```

```ts
// frontend/src/lib/format.ts
import type { DataQuality } from './types';

const int = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const money = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const sig3 = new Intl.NumberFormat('en-US', { maximumSignificantDigits: 3 });

export const formatInt = (n: number) => int.format(n);
export const formatMoney = (n: number) => money.format(n);
export const formatPct = (p: number) => `${(p * 100).toFixed(1)}%`;
export const formatNum = (n: number) => sig3.format(n);

export const QUALITY_LABEL: Record<DataQuality, string> = {
  ok: 'OK',
  insufficient_history: 'Low history',
  forecast_unavailable: 'No forecast',
  clv_unavailable: 'No CLV'
};

export const QUALITY_HELP: Record<DataQuality, string> = {
  ok: 'Full forecast and CLV.',
  insufficient_history:
    'Only one purchase on record, so the forecast is low-confidence. Any CLV shown rests on the cohort-wide average spend.',
  forecast_unavailable:
    'The forecast could not be computed for this customer. Values are shown as 0 and are not predictions.',
  clv_unavailable:
    'The forecast is fine, but spend per order is too uncertain to estimate CLV. CLV is shown as 0 and is not a prediction.'
};
```

Note on `formatNum(0.012345)`: `maximumSignificantDigits: 3` yields `0.0123`, and `0` yields `0`.

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` — Expected: PASS. (Verified against `cpp/src/worker.cpp` ~L137–157: an `insufficient_history` row keeps a real `nu * expected` CLV when the Gamma-Gamma posterior mean exists, and a 0.0 placeholder when it is NaN — that case is *not* re-flagged `clv_unavailable`. Hence the help text above and the CLV-cell rule in Task 10.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/csvHeader.ts frontend/src/lib/format.ts frontend/tests/csvHeader.test.ts frontend/tests/format.test.ts
git commit -m "feat(frontend): CSV header validation and number/label formatting"
```

---

### Task 6: Upload page (drop zone → validate → upload → redirect)

**Files:**
- Create: `frontend/src/lib/components/Dropzone.svelte`
- Modify: `frontend/src/routes/+page.svelte` (replace the placeholder)
- Test: `frontend/tests/Dropzone.test.ts`, `frontend/tests/upload-page.test.ts`

**Interfaces:**
- Consumes: `validateFile` (Task 5), `api.uploadCsv` / `ApiError` (Task 4), `goto` from `$app/navigation`.
- Produces: `Dropzone.svelte` props `{ onselect: (file: File) => void; disabled?: boolean }` — a labelled `<input type="file" accept=".csv,text/csv">` plus drag-and-drop; both paths call `onselect` with the first file. The upload page navigates to `/jobs/{job_id}` on success.

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/Dropzone.test.ts
import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Dropzone from '../src/lib/components/Dropzone.svelte';

describe('Dropzone', () => {
  it('calls onselect with the chosen file', async () => {
    const onselect = vi.fn();
    render(Dropzone, { props: { onselect } });
    const file = new File(['x'], 'log.csv', { type: 'text/csv' });
    await fireEvent.change(screen.getByLabelText(/choose a csv/i), { target: { files: [file] } });
    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('calls onselect on drop', async () => {
    const onselect = vi.fn();
    render(Dropzone, { props: { onselect } });
    const file = new File(['x'], 'log.csv', { type: 'text/csv' });
    await fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files: [file] } });
    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('ignores input while disabled', async () => {
    const onselect = vi.fn();
    render(Dropzone, { props: { onselect, disabled: true } });
    await fireEvent.drop(screen.getByTestId('dropzone'), {
      dataTransfer: { files: [new File(['x'], 'a.csv')] }
    });
    expect(onselect).not.toHaveBeenCalled();
  });
});
```

```ts
// frontend/tests/upload-page.test.ts
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const goto = vi.fn();
const uploadCsv = vi.fn();
vi.mock('$app/navigation', () => ({ goto: (...a: unknown[]) => goto(...a) }));
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return { ...actual, api: { uploadCsv: (...a: unknown[]) => uploadCsv(...a) } };
});

import { ApiError } from '../src/lib/api';
import Page from '../src/routes/+page.svelte';

const pick = async (file: File) =>
  fireEvent.change(screen.getByLabelText(/choose a csv/i), { target: { files: [file] } });

describe('upload page', () => {
  beforeEach(() => { goto.mockReset(); uploadCsv.mockReset(); });

  it('uploads a valid file and navigates to the job page', async () => {
    uploadCsv.mockResolvedValue({ job_id: 'job-42' });
    render(Page);
    await pick(new File(['customer_id,transaction_date,amount\n1,2024-01-01,5\n'], 'log.csv', { type: 'text/csv' }));

    const button = await screen.findByRole('button', { name: /forecast/i });
    await fireEvent.click(button);

    await waitFor(() => expect(goto).toHaveBeenCalledWith('/jobs/job-42'));
  });

  it('shows header problems and does not offer to upload', async () => {
    render(Page);
    await pick(new File(['id,date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    expect(await screen.findByText(/missing required column "customer_id"/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /forecast/i })).not.toBeInTheDocument();
  });

  it('shows the server error when the upload is rejected', async () => {
    uploadCsv.mockRejectedValue(new ApiError(400, 'transaction log is empty'));
    render(Page);
    await pick(new File(['customer_id,transaction_date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    await fireEvent.click(await screen.findByRole('button', { name: /forecast/i }));
    expect(await screen.findByText('transaction log is empty')).toBeInTheDocument();
    expect(goto).not.toHaveBeenCalled();
  });
});
```

(The `$lib` and `$app` aliases resolve inside Vitest through the SvelteKit Vite plugin; `$app/navigation` is mocked as shown.)

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/Dropzone.test.ts tests/upload-page.test.ts`
Expected: FAIL — `Dropzone.svelte` not found / page lacks the controls.

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/Dropzone.svelte -->
<script lang="ts">
  let { onselect, disabled = false }: { onselect: (file: File) => void; disabled?: boolean } = $props();
  let over = $state(false);

  function pick(files: FileList | File[] | null | undefined) {
    const first = files?.[0];
    if (!disabled && first) onselect(first);
  }
</script>

<div
  class="zone"
  class:over
  data-testid="dropzone"
  role="group"
  aria-label="CSV drop zone"
  ondragover={(e) => { e.preventDefault(); if (!disabled) over = true; }}
  ondragleave={() => (over = false)}
  ondrop={(e) => { e.preventDefault(); over = false; pick(e.dataTransfer?.files); }}
>
  <p>Drag a transaction-log CSV here, or</p>
  <label class="pick">
    Choose a CSV file
    <input
      type="file"
      accept=".csv,text/csv"
      {disabled}
      onchange={(e) => pick(e.currentTarget.files)}
    />
  </label>
</div>

<style>
  .zone { border: 2px dashed var(--line); border-radius: 12px; padding: 2.5rem 1rem; text-align: center; background: var(--card); }
  .zone.over { border-color: var(--accent); background: #eff4ff; }
  .pick { color: var(--accent); font-weight: 600; cursor: pointer; }
  .pick input { position: absolute; width: 1px; height: 1px; opacity: 0; }
  .pick:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
```

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { api, ApiError } from '$lib/api';
  import { validateFile } from '$lib/csvHeader';
  import Dropzone from '$lib/components/Dropzone.svelte';

  let file = $state<File | null>(null);
  let problems = $state<string[]>([]);
  let hasAmount = $state(true);
  let serverError = $state('');
  let busy = $state(false);

  async function onselect(f: File) {
    file = null; serverError = '';
    const check = await validateFile(f);
    problems = check.errors;
    hasAmount = check.hasAmount;
    if (check.ok) file = f;
  }

  async function submit() {
    if (!file) return;
    busy = true; serverError = '';
    try {
      const { job_id } = await api.uploadCsv(file);
      await goto(`/jobs/${job_id}`);
    } catch (e) {
      serverError = e instanceof ApiError ? e.message : 'Upload failed';
    } finally {
      busy = false;
    }
  }
</script>

<h1>Upload a transaction log</h1>
<p class="lede">
  One row per purchase, with columns <code>customer_id</code>, <code>transaction_date</code> and
  (optional) <code>amount</code>. You get per-customer purchase, retention and lifetime-value forecasts back.
</p>

<Dropzone {onselect} disabled={busy} />

{#if problems.length}
  <ul class="errors" role="alert">
    {#each problems as p}<li>{p}</li>{/each}
  </ul>
{/if}

{#if file}
  <div class="ready">
    <p><strong>{file.name}</strong> ({(file.size / 1024).toFixed(0)} KB)</p>
    {#if !hasAmount}
      <p class="note">No <code>amount</code> column — purchase forecasts only, no lifetime-value (CLV) figures.</p>
    {/if}
    <button onclick={submit} disabled={busy}>{busy ? 'Uploading…' : 'Upload and forecast'}</button>
  </div>
{/if}

{#if serverError}<p class="errors" role="alert">{serverError}</p>{/if}

<style>
  .lede { color: var(--muted); max-width: 46rem; }
  .errors { color: var(--bad); }
  .note { color: var(--warn); }
  .ready { margin-top: 1rem; }
  button { background: var(--accent); color: #fff; border: 0; border-radius: 8px; padding: 0.6rem 1.2rem; font-size: 1rem; cursor: pointer; }
  button:disabled { opacity: 0.6; cursor: wait; }
</style>
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` and `npm run check` — Expected: PASS, 0 type errors. Manual spot check: `npm run dev`, open `http://localhost:5173/`, drop `models/ingest_sample.csv` — the "Upload and forecast" button appears (don't submit until the job page exists, Task 7).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/Dropzone.svelte frontend/src/routes/+page.svelte frontend/tests/Dropzone.test.ts frontend/tests/upload-page.test.ts
git commit -m "feat(frontend): upload page with drag-drop, header validation and server error display"
```

---

### Task 7: Job status polling and the job page shell

**Files:**
- Create: `frontend/src/lib/poller.ts`, `frontend/src/routes/jobs/[id]/+page.svelte`
- Test: `frontend/tests/poller.test.ts`, `frontend/tests/job-page.test.ts`

**Interfaces:**
- Consumes: `api.getJob` / `ApiError` / `JobInfo` (Task 4).
- Produces:
```ts
export interface PollOptions {
  getJob: (id: string) => Promise<JobInfo>;
  onUpdate?: (job: JobInfo) => void;
  signal?: AbortSignal;
  initialMs?: number;   // default 1000
  maxMs?: number;       // default 5000
  maxErrors?: number;   // consecutive transient failures tolerated, default 5
}
/** Resolves with the first job in a terminal state ('done' | 'failed'). Rejects with the last error after
 *  maxErrors consecutive failures, or with an AbortError-named Error when signal aborts. The delay grows 1.5x per
 *  poll up to maxMs. A 404/400 ApiError is not transient and rejects immediately. */
export function pollJob(id: string, opts: PollOptions): Promise<JobInfo>;
```
  The job page (`/jobs/[id]`) polls on mount, shows a status line while `queued`/`running`, the `error_reason` when `failed`, a "not found" message for a bad id, and — when `done` — renders a slot where later tasks mount the dashboard.

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/poller.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../src/lib/api';
import { pollJob } from '../src/lib/poller';
import type { JobInfo } from '../src/lib/types';

const job = (status: JobInfo['status'], error_reason: string | null = null): JobInfo => ({ id: 'j', status, error_reason });

describe('pollJob', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('polls until the job is done, reporting each update, with growing delays', async () => {
    const getJob = vi.fn()
      .mockResolvedValueOnce(job('queued'))
      .mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(job('done'));
    const seen: string[] = [];
    const p = pollJob('j', { getJob, onUpdate: (j) => seen.push(j.status), initialMs: 100, maxMs: 1000 });

    await vi.advanceTimersByTimeAsync(0);     // first poll is immediate
    expect(getJob).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(100);   // 100 ms
    expect(getJob).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(150);   // 100 * 1.5
    expect(await p).toEqual(job('done'));
    expect(seen).toEqual(['queued', 'running', 'done']);
  });

  it('resolves on failed as a terminal state', async () => {
    const getJob = vi.fn().mockResolvedValue(job('failed', 'degenerate cohort'));
    expect(await pollJob('j', { getJob })).toEqual(job('failed', 'degenerate cohort'));
  });

  it('tolerates transient errors but gives up after maxErrors', async () => {
    const getJob = vi.fn().mockRejectedValue(new ApiError(0, 'Could not reach the server'));
    const p = pollJob('j', { getJob, maxErrors: 3, initialMs: 10 });
    const assertion = expect(p).rejects.toMatchObject({ status: 0 });
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
    expect(getJob).toHaveBeenCalledTimes(3);
  });

  it('recovers when a transient error is followed by success', async () => {
    const getJob = vi.fn()
      .mockRejectedValueOnce(new ApiError(502, 'API unreachable'))
      .mockResolvedValueOnce(job('done'));
    const p = pollJob('j', { getJob, initialMs: 10 });
    await vi.advanceTimersByTimeAsync(50);
    expect(await p).toEqual(job('done'));
  });

  it('rejects immediately on a 404', async () => {
    const getJob = vi.fn().mockRejectedValue(new ApiError(404, 'job not found'));
    await expect(pollJob('j', { getJob })).rejects.toMatchObject({ status: 404 });
    expect(getJob).toHaveBeenCalledTimes(1);
  });

  it('stops when aborted', async () => {
    const ctl = new AbortController();
    const getJob = vi.fn().mockResolvedValue(job('running'));
    const p = pollJob('j', { getJob, signal: ctl.signal, initialMs: 100 });
    const assertion = expect(p).rejects.toMatchObject({ name: 'AbortError' });
    await vi.advanceTimersByTimeAsync(0);
    ctl.abort();
    await vi.advanceTimersByTimeAsync(500);
    await assertion;
  });
});
```

```ts
// frontend/tests/job-page.test.ts
import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getJob = vi.fn();
vi.mock('$app/state', () => ({ page: { params: { id: 'job-1' } } }));
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return { ...actual, api: { getJob: (...a: unknown[]) => getJob(...a) } };
});

import { ApiError } from '../src/lib/api';
import Page from '../src/routes/jobs/[id]/+page.svelte';

describe('job page', () => {
  beforeEach(() => getJob.mockReset());

  it('shows progress then the done state', async () => {
    getJob.mockResolvedValueOnce({ id: 'job-1', status: 'running', error_reason: null })
          .mockResolvedValue({ id: 'job-1', status: 'done', error_reason: null });
    render(Page);
    expect(await screen.findByText(/running/i)).toBeInTheDocument();
    expect(await screen.findByTestId('job-done', {}, { timeout: 4000 })).toBeInTheDocument();
  });

  it('shows the failure reason', async () => {
    getJob.mockResolvedValue({ id: 'job-1', status: 'failed', error_reason: 'all customers have zero frequency' });
    render(Page);
    expect(await screen.findByText(/all customers have zero frequency/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /upload another/i })).toBeInTheDocument();
  });

  it('shows a not-found message for an unknown job', async () => {
    getJob.mockRejectedValue(new ApiError(404, 'job not found'));
    render(Page);
    await waitFor(() => expect(screen.getByText(/couldn't find that job/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/poller.test.ts tests/job-page.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/poller.ts
import { ApiError } from './api';
import type { JobInfo } from './types';

export interface PollOptions {
  getJob: (id: string) => Promise<JobInfo>;
  onUpdate?: (job: JobInfo) => void;
  signal?: AbortSignal;
  initialMs?: number;
  maxMs?: number;
  maxErrors?: number;
}

const abortError = () => Object.assign(new Error('Polling aborted'), { name: 'AbortError' });

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(abortError());
    const t = setTimeout(() => { signal?.removeEventListener('abort', onAbort); resolve(); }, ms);
    const onAbort = () => { clearTimeout(t); reject(abortError()); };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

export async function pollJob(id: string, opts: PollOptions): Promise<JobInfo> {
  const { getJob, onUpdate, signal, initialMs = 1000, maxMs = 5000, maxErrors = 5 } = opts;
  let delay = initialMs;
  let errors = 0;
  for (;;) {
    if (signal?.aborted) throw abortError();
    try {
      const job = await getJob(id);
      errors = 0;
      onUpdate?.(job);
      if (job.status === 'done' || job.status === 'failed') return job;
    } catch (e) {
      // 400/404 mean the id itself is wrong: retrying cannot help.
      if (e instanceof ApiError && (e.status === 404 || e.status === 400)) throw e;
      if (++errors >= maxErrors) throw e;
    }
    await sleep(delay, signal);
    delay = Math.min(Math.round(delay * 1.5), maxMs);
  }
}
```

```svelte
<!-- frontend/src/routes/jobs/[id]/+page.svelte -->
<script lang="ts">
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api';
  import { pollJob } from '$lib/poller';
  import type { JobInfo } from '$lib/types';

  const id = page.params.id as string;
  let job = $state<JobInfo | null>(null);
  let notFound = $state(false);
  let netError = $state('');

  onMount(() => {
    const ctl = new AbortController();
    pollJob(id, { getJob: api.getJob, onUpdate: (j) => (job = j), signal: ctl.signal }).catch((e) => {
      if (e?.name === 'AbortError') return;
      if (e instanceof ApiError && (e.status === 404 || e.status === 400)) notFound = true;
      else netError = e instanceof ApiError ? e.message : 'Lost contact with the server';
    });
    return () => ctl.abort();
  });
</script>

{#if notFound}
  <h1>Job not found</h1>
  <p>We couldn't find that job. <a href="/">Upload a file</a> to start a new one.</p>
{:else if netError}
  <h1>Connection problem</h1>
  <p role="alert">{netError}. <a href={`/jobs/${id}`}>Retry</a></p>
{:else if !job || job.status === 'queued' || job.status === 'running'}
  <h1>Working on your forecast…</h1>
  <p aria-live="polite">Status: <strong>{job?.status ?? 'queued'}</strong>. This page updates automatically.</p>
{:else if job.status === 'failed'}
  <h1>Forecast failed</h1>
  <p role="alert">{job.error_reason ?? 'The job failed for an unknown reason.'}</p>
  <p><a href="/">Upload another file</a></p>
{:else}
  <div data-testid="job-done">
    <h1>Forecast ready</h1>
    <!-- Tasks 9–11 mount the dashboard, table and export button here. -->
  </div>
{/if}
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` and `npm run check` — Expected: PASS, 0 type errors. (`api.getJob` is passed unbound — it is an arrow function from `createApi`, so no `this` issue.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/poller.ts frontend/src/routes/jobs frontend/tests/poller.test.ts frontend/tests/job-page.test.ts
git commit -m "feat(frontend): job status polling and job page states"
```

---

### Task 8: Chart wrapper and pure histogram option builder

**Files:**
- Create: `frontend/src/lib/chartOptions.ts`, `frontend/src/lib/components/Chart.svelte`
- Test: `frontend/tests/chartOptions.test.ts`, `frontend/tests/Chart.test.ts`

**Interfaces:**
- Consumes: `Histogram` (Task 4), `formatNum`/`formatPct`/`formatMoney` (Task 5).
- Produces:
```ts
export interface HistogramOptions { seriesName: string; xLabel: string; fmt: (n: number) => string }
export function histogramOption(h: Histogram, o: HistogramOptions): EChartsCoreOption;
// Chart.svelte props: { option: EChartsCoreOption; height?: string (default '260px'); label: string (aria-label) }
```
  `histogramOption` throws `Error('edges must have counts.length + 1 entries')` on malformed input. `Chart.svelte` initialises ECharts with the **canvas renderer and only the Bar chart, Grid, Tooltip and Aria components** (modular import keeps the bundle small), re-applies the option reactively, resizes with its container, and disposes on destroy.

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/chartOptions.test.ts
import { describe, expect, it } from 'vitest';
import { histogramOption } from '../src/lib/chartOptions';

const fmt = (n: number) => n.toFixed(1);

describe('histogramOption', () => {
  const h = { edges: [0, 1, 2, 3], counts: [5, 0, 7] };

  it('labels each bin with its range and carries the counts as bar data', () => {
    const o: any = histogramOption(h, { seriesName: 'Customers', xLabel: 'P(alive)', fmt });
    expect(o.xAxis.data).toEqual(['0.0–1.0', '1.0–2.0', '2.0–3.0']);
    expect(o.series[0].type).toBe('bar');
    expect(o.series[0].data).toEqual([5, 0, 7]);
    expect(o.xAxis.name).toBe('P(alive)');
    expect(o.yAxis.name).toBe('Customers');
  });

  it('enables accessibility descriptions and an axis tooltip', () => {
    const o: any = histogramOption(h, { seriesName: 'Customers', xLabel: 'x', fmt });
    expect(o.aria.enabled).toBe(true);
    expect(o.tooltip.trigger).toBe('axis');
  });

  it('rejects mismatched edges/counts', () => {
    expect(() => histogramOption({ edges: [0, 1], counts: [1, 2] }, { seriesName: 's', xLabel: 'x', fmt })).toThrow(
      'edges must have counts.length + 1 entries'
    );
  });
});
```

```ts
// frontend/tests/Chart.test.ts
import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

const setOption = vi.fn();
const resize = vi.fn();
const dispose = vi.fn();
vi.mock('echarts/core', () => ({
  init: vi.fn(() => ({ setOption, resize, dispose })),
  use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ BarChart: {} }));
vi.mock('echarts/components', () => ({ GridComponent: {}, TooltipComponent: {}, AriaComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

import Chart from '../src/lib/components/Chart.svelte';

describe('Chart', () => {
  it('initialises ECharts, applies the option, and disposes on unmount', () => {
    const option = { series: [{ type: 'bar', data: [1] }] };
    const { unmount, getByRole } = render(Chart, { props: { option, label: 'P(alive) histogram' } });
    expect(getByRole('img', { name: 'P(alive) histogram' })).toBeInTheDocument();
    expect(setOption).toHaveBeenCalledWith(option, true);
    unmount();
    expect(dispose).toHaveBeenCalled();
  });
});
```

(jsdom has no `ResizeObserver`; the component guards for it, and the test setup need not polyfill it.)

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/chartOptions.test.ts tests/Chart.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/chartOptions.ts
import type { EChartsCoreOption } from 'echarts/core';
import type { Histogram } from './types';

export interface HistogramOptions {
  seriesName: string;
  xLabel: string;
  fmt: (n: number) => string;
}

export function histogramOption(h: Histogram, o: HistogramOptions): EChartsCoreOption {
  if (h.edges.length !== h.counts.length + 1) {
    throw new Error('edges must have counts.length + 1 entries');
  }
  const labels = h.counts.map((_, i) => `${o.fmt(h.edges[i])}–${o.fmt(h.edges[i + 1])}`);
  return {
    aria: { enabled: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 56, right: 16, top: 24, bottom: 56 },
    xAxis: { type: 'category', data: labels, name: o.xLabel, nameLocation: 'middle', nameGap: 38, axisLabel: { hideOverlap: true } },
    yAxis: { type: 'value', name: 'Customers', minInterval: 1 },
    series: [{ name: o.seriesName, type: 'bar', data: h.counts, barCategoryGap: '8%', itemStyle: { color: '#2563eb' } }]
  };
}
```

```svelte
<!-- frontend/src/lib/components/Chart.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import * as echarts from 'echarts/core';
  import type { EChartsCoreOption } from 'echarts/core';
  import { BarChart } from 'echarts/charts';
  import { AriaComponent, GridComponent, TooltipComponent } from 'echarts/components';
  import { CanvasRenderer } from 'echarts/renderers';

  echarts.use([BarChart, GridComponent, TooltipComponent, AriaComponent, CanvasRenderer]);

  let { option, label, height = '260px' }: { option: EChartsCoreOption; label: string; height?: string } = $props();

  let el: HTMLDivElement;
  let chart: ReturnType<typeof echarts.init> | undefined;

  onMount(() => {
    chart = echarts.init(el);
    chart.setOption(option, true);
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => chart?.resize()) : undefined;
    ro?.observe(el);
    return () => { ro?.disconnect(); chart?.dispose(); chart = undefined; };
  });

  $effect(() => { chart?.setOption(option, true); });
</script>

<div bind:this={el} role="img" aria-label={label} style:height></div>
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` and `npm run check` — Expected: PASS. If `Chart.test.ts` fails because the first `$effect` run fires before `onMount` sets `chart`, that is expected and harmless (the effect no-ops); `setOption` is still asserted from `onMount`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/chartOptions.ts frontend/src/lib/components/Chart.svelte frontend/tests/chartOptions.test.ts frontend/tests/Chart.test.ts
git commit -m "feat(frontend): ECharts wrapper component and histogram option builder"
```

---

### Task 9: Dashboard — summary tiles and three cohort charts

**Files:**
- Create: `frontend/src/lib/components/SummaryTiles.svelte`, `frontend/src/lib/components/Dashboard.svelte`
- Modify: `frontend/src/routes/jobs/[id]/+page.svelte` (mount `Dashboard` in the done branch)
- Test: `frontend/tests/SummaryTiles.test.ts`, `frontend/tests/Dashboard.test.ts`

**Interfaces:**
- Consumes: `JobSummary` (Task 4), `api.getSummary`, `histogramOption` + `Chart` (Task 8), formatters (Task 5).
- Produces: `SummaryTiles.svelte` props `{ summary: JobSummary }` — tiles: Customers, Expected purchases (total), Mean P(alive), Total CLV (hidden when `quality_counts.ok` is absent/0), plus a data-quality line when any non-`ok` rows exist. `Dashboard.svelte` props `{ jobId: string }` — loads the summary, shows loading/error states, renders tiles + three `Chart`s (P(alive), expected purchases, CLV), and (Tasks 10–11) the table and export slots.

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/SummaryTiles.test.ts
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import SummaryTiles from '../src/lib/components/SummaryTiles.svelte';
import type { JobSummary } from '../src/lib/types';

const hist = { edges: [0, 1], counts: [0] };
const base: JobSummary = {
  job_id: 'j', n_customers: 1234, quality_counts: { ok: 1200, insufficient_history: 34 },
  mean_p_alive: 0.6234, total_expected_purchases: 4567.8, total_clv: 98765.4321, has_clv_interval: false,
  histograms: { p_alive: hist, expected_purchases: hist, clv_point: hist }
};

describe('SummaryTiles', () => {
  it('shows the headline numbers, formatted', () => {
    render(SummaryTiles, { props: { summary: base } });
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('62.3%')).toBeInTheDocument();
    expect(screen.getByText('98,765.43')).toBeInTheDocument();
  });

  it('summarises non-OK data quality', () => {
    render(SummaryTiles, { props: { summary: base } });
    expect(screen.getByText(/34 customers have limited data/i)).toBeInTheDocument();
  });

  it('omits the CLV tile when no customer has a CLV (no amount column)', () => {
    render(SummaryTiles, { props: { summary: { ...base, quality_counts: { insufficient_history: 1234 }, total_clv: 0 } } });
    expect(screen.queryByText(/total clv/i)).not.toBeInTheDocument();
  });
});
```

```ts
// frontend/tests/Dashboard.test.ts
import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getSummary = vi.fn();
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return { ...actual, api: { getSummary: (...a: unknown[]) => getSummary(...a) } };
});
vi.mock('../src/lib/components/Chart.svelte', async () => ({
  default: (await import('./stubs/ChartStub.svelte')).default
}));

import { ApiError } from '../src/lib/api';
import Dashboard from '../src/lib/components/Dashboard.svelte';

const hist = (n: number) => ({ edges: Array.from({ length: n + 1 }, (_, i) => i), counts: Array(n).fill(1) });
const summary = {
  job_id: 'j', n_customers: 3, quality_counts: { ok: 3 }, mean_p_alive: 0.5,
  total_expected_purchases: 6, total_clv: 100, has_clv_interval: false,
  histograms: { p_alive: hist(10), expected_purchases: hist(20), clv_point: hist(20) }
};

describe('Dashboard', () => {
  beforeEach(() => getSummary.mockReset());

  it('loads the summary and renders the three charts', async () => {
    getSummary.mockResolvedValue(summary);
    render(Dashboard, { props: { jobId: 'j' } });
    expect(await screen.findByLabelText('Distribution of P(alive)')).toBeInTheDocument();
    expect(screen.getByLabelText('Distribution of expected purchases')).toBeInTheDocument();
    expect(screen.getByLabelText('Distribution of customer lifetime value')).toBeInTheDocument();
    expect(getSummary).toHaveBeenCalledWith('j');
  });

  it('hides the CLV chart when no customer has a valid CLV', async () => {
    getSummary.mockResolvedValue({ ...summary, quality_counts: { insufficient_history: 3 }, total_clv: 0 });
    render(Dashboard, { props: { jobId: 'j' } });
    await screen.findByLabelText('Distribution of P(alive)');
    expect(screen.queryByLabelText('Distribution of customer lifetime value')).not.toBeInTheDocument();
  });

  it('shows an error when the summary cannot be loaded', async () => {
    getSummary.mockRejectedValue(new ApiError(500, 'Request failed (HTTP 500)'));
    render(Dashboard, { props: { jobId: 'j' } });
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed (HTTP 500)');
  });
});
```

Create the stub used above (`ChartStub.svelte` renders just the accessible container so tests don't need a canvas):
```svelte
<!-- frontend/tests/stubs/ChartStub.svelte -->
<script lang="ts">
  let { label }: { option: unknown; label: string; height?: string } = $props();
</script>
<div role="img" aria-label={label}></div>
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/SummaryTiles.test.ts tests/Dashboard.test.ts`
Expected: FAIL — components not found.

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/SummaryTiles.svelte -->
<script lang="ts">
  import type { JobSummary } from '$lib/types';
  import { formatInt, formatMoney, formatNum, formatPct } from '$lib/format';

  let { summary }: { summary: JobSummary } = $props();

  const hasClv = $derived((summary.quality_counts.ok ?? 0) > 0);
  const limited = $derived(summary.n_customers - (summary.quality_counts.ok ?? 0));
</script>

<div class="tiles">
  <div class="tile"><span class="k">Customers</span><span class="v">{formatInt(summary.n_customers)}</span></div>
  <div class="tile"><span class="k">Expected purchases (total)</span><span class="v">{formatNum(summary.total_expected_purchases)}</span></div>
  <div class="tile"><span class="k">Mean P(alive)</span><span class="v">{formatPct(summary.mean_p_alive)}</span></div>
  {#if hasClv}
    <div class="tile"><span class="k">Total CLV</span><span class="v">{formatMoney(summary.total_clv)}</span></div>
  {/if}
</div>
{#if limited > 0}
  <p class="note">{formatInt(limited)} customers have limited data and are excluded from the statistics above that they cannot support.</p>
{/if}

<style>
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 1rem; }
  .tile { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 1rem; display: flex; flex-direction: column; }
  .k { color: var(--muted); font-size: 0.85rem; }
  .v { font-size: 1.6rem; font-weight: 600; }
  .note { color: var(--muted); font-size: 0.9rem; }
</style>
```

(The tile test asserts the text `34 customers have limited data`; the sentence above contains it.)

```svelte
<!-- frontend/src/lib/components/Dashboard.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api';
  import { histogramOption } from '$lib/chartOptions';
  import { formatMoney, formatNum, formatPct } from '$lib/format';
  import type { JobSummary } from '$lib/types';
  import Chart from './Chart.svelte';
  import SummaryTiles from './SummaryTiles.svelte';

  let { jobId }: { jobId: string } = $props();
  let summary = $state<JobSummary | null>(null);
  let error = $state('');

  onMount(async () => {
    try {
      summary = await api.getSummary(jobId);
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Could not load the dashboard';
    }
  });

  const hasClv = $derived((summary?.quality_counts.ok ?? 0) > 0);
</script>

{#if error}
  <p role="alert" class="err">{error}</p>
{:else if !summary}
  <p>Loading results…</p>
{:else}
  <SummaryTiles {summary} />
  <div class="charts">
    <section>
      <h3>How likely is each customer to still be active?</h3>
      <Chart label="Distribution of P(alive)"
        option={histogramOption(summary.histograms.p_alive, { seriesName: 'Customers', xLabel: 'P(alive)', fmt: formatPct })} />
    </section>
    <section>
      <h3>Expected purchases per customer</h3>
      <Chart label="Distribution of expected purchases"
        option={histogramOption(summary.histograms.expected_purchases, { seriesName: 'Customers', xLabel: 'Expected purchases', fmt: formatNum })} />
    </section>
    {#if hasClv}
      <section>
        <h3>Customer lifetime value</h3>
        <Chart label="Distribution of customer lifetime value"
          option={histogramOption(summary.histograms.clv_point, { seriesName: 'Customers', xLabel: 'CLV', fmt: formatMoney })} />
      </section>
    {/if}
  </div>
  <!-- Task 10 mounts <CustomerTable />, Task 11 the export button. -->
{/if}

<style>
  .err { color: var(--bad); }
  .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: 1.25rem; margin-top: 1.5rem; }
  section { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 1rem; }
  h3 { margin: 0 0 0.5rem; font-size: 1rem; }
</style>
```

In `frontend/src/routes/jobs/[id]/+page.svelte`, import `Dashboard` and replace the placeholder comment inside the `job-done` block:
```svelte
  import Dashboard from '$lib/components/Dashboard.svelte';
  …
  <div data-testid="job-done">
    <h1>Your forecast</h1>
    <Dashboard jobId={id} />
  </div>
```
The existing `job-page.test.ts` "done" case keeps passing only if `Dashboard`'s `getSummary` is mocked — add `getSummary: vi.fn(() => new Promise(() => {}))` to that test's `api` mock so the dashboard stays in its loading state.

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` and `npm run check` — Expected: PASS, 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/tests
git commit -m "feat(frontend): dashboard with summary tiles and P(alive)/purchases/CLV histograms"
```

---

### Task 10: Per-customer table — server-side sort, filter, search, paging

**Files:**
- Create: `frontend/src/lib/components/QualityBadge.svelte`, `frontend/src/lib/components/CustomerTable.svelte`
- Modify: `frontend/src/lib/components/Dashboard.svelte` (mount the table)
- Test: `frontend/tests/CustomerTable.test.ts`

**Interfaces:**
- Consumes: `api.getResults`, `ResultsQuery`, `CustomerRow`, `SortKey`, `DataQuality` (Task 4); `QUALITY_LABEL`/`QUALITY_HELP`/formatters (Task 5); `JobSummary.has_clv_interval` and `quality_counts` (to hide empty quality filter options).
- Produces: `CustomerTable.svelte` props `{ jobId: string; hasClvInterval: boolean; qualities: DataQuality[] }` — a table with sortable column headers (click toggles asc/desc; `aria-sort` set), a quality `<select>` (populated from `qualities`), a debounced (300 ms) customer-id search box, and prev/next paging with "Page X of Y". Every control change calls `api.getResults(jobId, query)` and resets to page 1 except paging. `QualityBadge.svelte` props `{ quality: DataQuality }` renders the label with a `title` of the help text; non-`ok` rows render CLV/forecast cells as "—" for the values the placeholder rules say are not real (`forecast_unavailable` → all numeric cells "—"; `clv_unavailable` and `insufficient_history` → CLV cells "—"... see implementation note).

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/tests/CustomerTable.test.ts
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const getResults = vi.fn();
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return { ...actual, api: { getResults: (...a: unknown[]) => getResults(...a) } };
});

import CustomerTable from '../src/lib/components/CustomerTable.svelte';
import type { CustomerRow, ResultsPage } from '../src/lib/types';

const row = (o: Partial<CustomerRow> = {}): CustomerRow => ({
  customer_id: 'C1', expected_purchases: 2.345, p_alive: 0.8, clv_point: 120.5, clv_lower: 120.5, clv_upper: 120.5,
  data_quality: 'ok', ...o
});
const page = (customers: CustomerRow[], total = customers.length, p = 1): ResultsPage => ({
  job_id: 'j', page: p, page_size: 50, total, customers
});
const props = { jobId: 'j', hasClvInterval: false, qualities: ['ok', 'insufficient_history'] as const };

describe('CustomerTable', () => {
  beforeEach(() => { getResults.mockReset(); getResults.mockResolvedValue(page([row()])); });
  afterEach(() => vi.useRealTimers());

  it('loads the first page with default sort and renders rows', async () => {
    render(CustomerTable, { props });
    expect(await screen.findByText('C1')).toBeInTheDocument();
    expect(getResults).toHaveBeenCalledWith('j', {
      page: 1, pageSize: 50, sort: 'customer_id', order: 'asc', quality: '', q: ''
    });
    expect(screen.getByText('80.0%')).toBeInTheDocument();
    expect(screen.getByText('120.50')).toBeInTheDocument();
  });

  it('clicking a header sorts by it, then toggles direction', async () => {
    render(CustomerTable, { props });
    await screen.findByText('C1');
    const header = screen.getByRole('columnheader', { name: /clv/i });
    await fireEvent.click(within(header).getByRole('button'));
    await waitFor(() => expect(getResults).toHaveBeenLastCalledWith('j', expect.objectContaining({ sort: 'clv_point', order: 'asc', page: 1 })));
    expect(header).toHaveAttribute('aria-sort', 'ascending');
    await fireEvent.click(within(header).getByRole('button'));
    await waitFor(() => expect(getResults).toHaveBeenLastCalledWith('j', expect.objectContaining({ sort: 'clv_point', order: 'desc' })));
    expect(header).toHaveAttribute('aria-sort', 'descending');
  });

  it('filters by quality and resets to page 1', async () => {
    render(CustomerTable, { props });
    await screen.findByText('C1');
    await fireEvent.change(screen.getByLabelText(/data quality/i), { target: { value: 'insufficient_history' } });
    await waitFor(() => expect(getResults).toHaveBeenLastCalledWith('j', expect.objectContaining({ quality: 'insufficient_history', page: 1 })));
  });

  it('debounces the customer-id search', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(CustomerTable, { props });
    await screen.findByText('C1');
    getResults.mockClear();
    const box = screen.getByLabelText(/search customer/i);
    await fireEvent.input(box, { target: { value: 'ab' } });
    await fireEvent.input(box, { target: { value: 'abc' } });
    expect(getResults).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(350);
    await waitFor(() => expect(getResults).toHaveBeenCalledTimes(1));
    expect(getResults).toHaveBeenCalledWith('j', expect.objectContaining({ q: 'abc', page: 1 }));
  });

  it('pages forward and back, disabling buttons at the ends', async () => {
    getResults.mockResolvedValue(page([row()], 120, 1));
    render(CustomerTable, { props });
    await screen.findByText('C1');
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
    await fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(getResults).toHaveBeenLastCalledWith('j', expect.objectContaining({ page: 2 })));
  });

  it('shows placeholders as dashes and an interval only when one exists', async () => {
    getResults.mockResolvedValue(page([
      row({ customer_id: 'good', clv_lower: 100, clv_upper: 140 }),
      row({ customer_id: 'bad', data_quality: 'forecast_unavailable', p_alive: 0, expected_purchases: 0, clv_point: 0 })
    ]));
    render(CustomerTable, { props: { ...props, hasClvInterval: true } });
    await screen.findByText('good');
    expect(screen.getByText('100.00 – 140.00')).toBeInTheDocument();
    const badRow = screen.getByText('bad').closest('tr')!;
    expect(within(badRow).getAllByText('—').length).toBeGreaterThanOrEqual(4);   // purchases, P(alive), CLV, interval
    expect(within(badRow).getByText('No forecast')).toBeInTheDocument();
  });

  it('shows an empty state and an error state', async () => {
    getResults.mockResolvedValueOnce(page([], 0));
    render(CustomerTable, { props });
    expect(await screen.findByText(/no customers match/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/CustomerTable.test.ts`
Expected: FAIL — components not found.

- [ ] **Step 3: Implement**

Cell rules (spec §6 / Global Constraints — placeholders are never shown as numbers):
- `forecast_unavailable`: expected purchases, P(alive), CLV, interval → "—".
- `clv_unavailable`: CLV and interval → "—"; forecast values shown.
- `insufficient_history`: forecast cells shown; CLV cells shown **only when `clv_point > 0`** (the worker writes a 0.0 placeholder, still flagged `insufficient_history`, when the Gamma-Gamma posterior is undefined for that customer).
- `ok`: all shown.
- Interval cell: shown only when the `hasClvInterval` prop is true **and** the row's CLV is real; format `lower – upper` (en dash, spaces).

```svelte
<!-- frontend/src/lib/components/QualityBadge.svelte -->
<script lang="ts">
  import type { DataQuality } from '$lib/types';
  import { QUALITY_HELP, QUALITY_LABEL } from '$lib/format';
  let { quality }: { quality: DataQuality } = $props();
</script>

<span class="badge {quality}" title={QUALITY_HELP[quality]}>{QUALITY_LABEL[quality]}</span>

<style>
  .badge { font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 999px; border: 1px solid var(--line); background: var(--card); }
  .ok { color: var(--good); }
  .insufficient_history, .clv_unavailable { color: var(--warn); }
  .forecast_unavailable { color: var(--bad); }
</style>
```

```svelte
<!-- frontend/src/lib/components/CustomerTable.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api';
  import { QUALITY_LABEL, formatMoney, formatNum, formatPct } from '$lib/format';
  import type { CustomerRow, DataQuality, ResultsQuery, SortKey } from '$lib/types';
  import QualityBadge from './QualityBadge.svelte';

  let { jobId, hasClvInterval, qualities }: {
    jobId: string; hasClvInterval: boolean; qualities: readonly DataQuality[];
  } = $props();

  const PAGE_SIZE = 50;
  let sort = $state<SortKey>('customer_id');
  let order = $state<'asc' | 'desc'>('asc');
  let quality = $state<DataQuality | ''>('');
  let search = $state('');
  let pageNo = $state(1);

  let rows = $state<CustomerRow[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let error = $state('');
  let seq = 0;   // discards responses that arrive after a newer request was issued

  const pageCount = $derived(Math.max(1, Math.ceil(total / PAGE_SIZE)));

  async function load() {
    const mine = ++seq;
    loading = true; error = '';
    const query: ResultsQuery = { page: pageNo, pageSize: PAGE_SIZE, sort, order, quality, q: search };
    try {
      const res = await api.getResults(jobId, query);
      if (mine !== seq) return;
      rows = res.customers; total = res.total;
    } catch (e) {
      if (mine !== seq) return;
      error = e instanceof ApiError ? e.message : 'Could not load customers';
    } finally {
      if (mine === seq) loading = false;
    }
  }

  onMount(load);

  function sortBy(key: SortKey) {
    if (sort === key) order = order === 'asc' ? 'desc' : 'asc';
    else { sort = key; order = 'asc'; }
    pageNo = 1; load();
  }
  function onQuality(e: Event) {
    quality = (e.currentTarget as HTMLSelectElement).value as DataQuality | '';
    pageNo = 1; load();
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  function onSearch(e: Event) {
    search = (e.currentTarget as HTMLInputElement).value;
    clearTimeout(timer);
    timer = setTimeout(() => { pageNo = 1; load(); }, 300);
  }
  function go(delta: number) { pageNo += delta; load(); }

  const ariaSort = (key: SortKey) => (sort !== key ? 'none' : order === 'asc' ? 'ascending' : 'descending');
  const hasForecast = (r: CustomerRow) => r.data_quality !== 'forecast_unavailable';
  const hasClv = (r: CustomerRow) =>
    hasForecast(r) && r.data_quality !== 'clv_unavailable' && (r.data_quality !== 'insufficient_history' || r.clv_point > 0);

  const COLS: { key: SortKey; label: string }[] = [
    { key: 'customer_id', label: 'Customer' },
    { key: 'expected_purchases', label: 'Expected purchases' },
    { key: 'p_alive', label: 'P(alive)' },
    { key: 'clv_point', label: 'CLV' }
  ];
</script>

<section class="wrap">
  <h2>Customers</h2>
  <div class="controls">
    <label>Search customer ID <input type="search" oninput={onSearch} /></label>
    <label>Data quality
      <select onchange={onQuality}>
        <option value="">All</option>
        {#each qualities as q}<option value={q}>{QUALITY_LABEL[q]}</option>{/each}
      </select>
    </label>
  </div>

  {#if error}
    <p role="alert" class="err">{error}</p>
  {:else if !loading && rows.length === 0}
    <p>No customers match these filters.</p>
  {:else}
    <div class="scroll">
      <table class:loading>
        <thead>
          <tr>
            {#each COLS as c}
              <th scope="col" aria-sort={ariaSort(c.key)}>
                <button onclick={() => sortBy(c.key)}>{c.label}{sort === c.key ? (order === 'asc' ? ' ▲' : ' ▼') : ''}</button>
              </th>
            {/each}
            {#if hasClvInterval}<th scope="col">CLV range</th>{/if}
            <th scope="col"><button onclick={() => sortBy('data_quality')}>Data quality{sort === 'data_quality' ? (order === 'asc' ? ' ▲' : ' ▼') : ''}</button></th>
          </tr>
        </thead>
        <tbody>
          {#each rows as r (r.customer_id)}
            <tr>
              <td>{r.customer_id}</td>
              <td class="num">{hasForecast(r) ? formatNum(r.expected_purchases) : '—'}</td>
              <td class="num">{hasForecast(r) ? formatPct(r.p_alive) : '—'}</td>
              <td class="num">{hasClv(r) ? formatMoney(r.clv_point) : '—'}</td>
              {#if hasClvInterval}
                <td class="num">{hasClv(r) ? `${formatMoney(r.clv_lower)} – ${formatMoney(r.clv_upper)}` : '—'}</td>
              {/if}
              <td><QualityBadge quality={r.data_quality} /></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="pager">
      <button onclick={() => go(-1)} disabled={pageNo <= 1 || loading}>Previous</button>
      <span>Page {pageNo} of {pageCount}</span>
      <button onclick={() => go(1)} disabled={pageNo >= pageCount || loading}>Next</button>
    </div>
  {/if}
</section>

<style>
  .wrap { margin-top: 2rem; }
  .controls { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
  .controls label { display: flex; flex-direction: column; font-size: 0.85rem; color: var(--muted); gap: 0.2rem; }
  .scroll { overflow-x: auto; background: var(--card); border: 1px solid var(--line); border-radius: 12px; }
  table { width: 100%; border-collapse: collapse; }
  table.loading { opacity: 0.6; }
  th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--line); }
  th button { all: unset; cursor: pointer; font-weight: 600; }
  th button:focus-visible { outline: 2px solid var(--accent); }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .pager { display: flex; gap: 1rem; align-items: center; justify-content: flex-end; margin-top: 0.75rem; }
  .err { color: var(--bad); }
</style>
```

Mount the table at the end of `Dashboard.svelte` (replace the Task-10 comment), computing the filter options from the summary:
```svelte
  import CustomerTable from './CustomerTable.svelte';
  import type { DataQuality } from '$lib/types';
  …
  const qualities = $derived(
    (Object.keys(summary?.quality_counts ?? {}) as DataQuality[])
  );
  …
  <CustomerTable {jobId} hasClvInterval={summary.has_clv_interval} {qualities} />
```
Add `getResults: vi.fn(() => new Promise(() => {}))` to the `api` mock in `Dashboard.test.ts` so the table stays in its loading state during those tests.

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` and `npm run check` — Expected: PASS, 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/tests
git commit -m "feat(frontend): server-side sortable, filterable, searchable customer table"
```

---

### Task 11: Export button and data-quality guidance

**Files:**
- Create: `frontend/src/lib/components/ExportBar.svelte`
- Modify: `frontend/src/lib/components/Dashboard.svelte` (mount `ExportBar` above the charts)
- Test: `frontend/tests/ExportBar.test.ts`

**Interfaces:**
- Consumes: `exportUrl` (Task 4), `QUALITY_LABEL`/`QUALITY_HELP`/`formatInt` (Task 5), `DataQuality`.
- Produces: `ExportBar.svelte` props `{ jobId: string; qualityCounts: Partial<Record<DataQuality, number>> }` — a "Download CSV" link (`href=exportUrl(jobId)`, `download="forecasts-<jobId>.csv"`) and, when any non-`ok` rows exist, a collapsed `<details>` "About data-quality flags" listing each present flag with its count and help text.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/tests/ExportBar.test.ts
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ExportBar from '../src/lib/components/ExportBar.svelte';

describe('ExportBar', () => {
  it('links to the CSV export for the job', () => {
    render(ExportBar, { props: { jobId: 'abc', qualityCounts: { ok: 10 } } });
    const link = screen.getByRole('link', { name: /download csv/i });
    expect(link).toHaveAttribute('href', '/api/jobs/abc/export.csv');
    expect(link).toHaveAttribute('download', 'forecasts-abc.csv');
  });

  it('omits the data-quality explainer when every row is OK', () => {
    render(ExportBar, { props: { jobId: 'abc', qualityCounts: { ok: 10 } } });
    expect(screen.queryByText(/about data-quality flags/i)).not.toBeInTheDocument();
  });

  it('explains each non-OK flag present, with counts', () => {
    render(ExportBar, {
      props: { jobId: 'abc', qualityCounts: { ok: 8, insufficient_history: 1200, forecast_unavailable: 2 } }
    });
    expect(screen.getByText(/about data-quality flags/i)).toBeInTheDocument();
    expect(screen.getByText(/Low history — 1,200 customers/)).toBeInTheDocument();
    expect(screen.getByText(/No forecast — 2 customers/)).toBeInTheDocument();
    expect(screen.queryByText(/No CLV —/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run tests/ExportBar.test.ts` — Expected: FAIL (component not found).

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/ExportBar.svelte -->
<script lang="ts">
  import { exportUrl } from '$lib/api';
  import { QUALITY_HELP, QUALITY_LABEL, formatInt } from '$lib/format';
  import type { DataQuality } from '$lib/types';

  let { jobId, qualityCounts }: { jobId: string; qualityCounts: Partial<Record<DataQuality, number>> } = $props();

  const flagged = $derived(
    (Object.entries(qualityCounts) as [DataQuality, number][]).filter(([q, n]) => q !== 'ok' && n > 0)
  );
</script>

<div class="bar">
  <a class="dl" href={exportUrl(jobId)} download={`forecasts-${jobId}.csv`}>Download CSV</a>
  {#if flagged.length}
    <details>
      <summary>About data-quality flags</summary>
      <ul>
        {#each flagged as [q, n]}
          <li>{QUALITY_LABEL[q]} — {formatInt(n)} customers. {QUALITY_HELP[q]}</li>
        {/each}
      </ul>
    </details>
  {/if}
</div>

<style>
  .bar { display: flex; gap: 1.5rem; align-items: flex-start; flex-wrap: wrap; margin: 1rem 0; }
  .dl { background: var(--accent); color: #fff; padding: 0.5rem 1rem; border-radius: 8px; text-decoration: none; font-weight: 600; }
  details { color: var(--muted); max-width: 40rem; }
  summary { cursor: pointer; }
</style>
```

(`{QUALITY_LABEL[q]} — {n} customers.` renders as one text node per `{}` chunk; if the test's `getByText` regex fails to match across Svelte's adjacent text nodes, wrap the label/count in a single template literal: `{`${QUALITY_LABEL[q]} — ${formatInt(n)} customers. ${QUALITY_HELP[q]}`}`.)

In `Dashboard.svelte`, import `ExportBar` and render it between `SummaryTiles` and the charts div:
```svelte
  <ExportBar {jobId} qualityCounts={summary.quality_counts} />
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run` and `npm run check` — Expected: PASS, 0 type errors, whole suite green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/tests
git commit -m "feat(frontend): CSV export button and data-quality flag explainer"
```

---

### Task 12: Live-stack smoke script, run instructions, and production build

**Files:**
- Create: `frontend/scripts/smoke.mjs`, `frontend/README.md`
- Modify: `docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md` (§9 step 5: add a status note; §4.1: note the PIT deferral — see Step 4)

**Interfaces:**
- Consumes: a running stack — `docker compose up -d` (Postgres, Redis), `api_server`, `worker`, and the frontend on `http://localhost:5173` (`npm run dev`) — plus `models/ingest_sample.csv`.
- Produces: `node scripts/smoke.mjs [baseUrl] [csvPath]` — exits 0 only if upload → poll → summary → results → export all succeed through the **frontend's `/api` proxy**; prints a one-line result per stage.

- [ ] **Step 1: Write the smoke script**

```js
// frontend/scripts/smoke.mjs
// End-to-end check through the frontend proxy against a LIVE stack (not a unit test: it needs
// docker compose, api_server and worker running). Usage: node scripts/smoke.mjs [baseUrl] [csv]
import { readFile } from 'node:fs/promises';

const base = process.argv[2] ?? 'http://localhost:5173';
const csvPath = process.argv[3] ?? new URL('../../models/ingest_sample.csv', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

const fail = (msg) => { console.error(`FAIL ${msg}`); process.exit(1); };
const ok = (msg) => console.log(`ok   ${msg}`);

async function get(path) {
  const res = await fetch(base + path);
  if (!res.ok) fail(`${path} -> HTTP ${res.status}`);
  return res;
}

const csv = await readFile(csvPath);
const up = await fetch(`${base}/api/uploads`, { method: 'POST', headers: { 'content-type': 'text/csv' }, body: csv });
if (!up.ok) fail(`upload -> HTTP ${up.status} ${await up.text()}`);
const { job_id } = await up.json();
ok(`uploaded, job ${job_id}`);

let status = 'queued';
for (let i = 0; i < 60 && status !== 'done' && status !== 'failed'; i++) {
  await new Promise((r) => setTimeout(r, 1000));
  status = (await (await get(`/api/jobs/${job_id}`)).json()).status;
}
if (status !== 'done') fail(`job ended as '${status}' (is the worker running?)`);
ok('job done');

const summary = await (await get(`/api/jobs/${job_id}/summary`)).json();
if (!(summary.n_customers > 0)) fail('summary has no customers');
if (summary.histograms.p_alive.counts.length !== 10) fail('p_alive histogram should have 10 bins');
ok(`summary: ${summary.n_customers} customers, mean P(alive) ${summary.mean_p_alive.toFixed(3)}`);

const results = await (await get(`/api/jobs/${job_id}/results?page=1&page_size=5&sort=p_alive&order=desc`)).json();
if (results.customers.length === 0) fail('results page is empty');
ok(`results: ${results.total} rows, top P(alive) ${results.customers[0].p_alive.toFixed(3)}`);

const exp = await (await get(`/api/jobs/${job_id}/export.csv`)).text();
if (!exp.startsWith('customer_id,expected_purchases,p_alive')) fail('export header is wrong');
ok(`export: ${exp.trim().split('\n').length - 1} data rows`);

const bad = await fetch(`${base}/api/uploads`, { method: 'POST', headers: { 'content-type': 'text/csv' }, body: 'a,b\n1,2\n' });
if (bad.status !== 400) fail(`bad upload should be 400, got ${bad.status}`);
ok('bad CSV rejected with 400');
console.log('SMOKE PASSED');
```

- [ ] **Step 2: Write `frontend/README.md`**

```markdown
# CLV Forecasts — frontend

SvelteKit app for the CLV/churn forecasting service: upload a transaction-log CSV, watch the job,
explore the cohort dashboard and per-customer table, export the forecasts.

## Run it (development)

From the repo root, start the backing services and API:

    docker compose up -d                       # Postgres + Redis
    cpp/build/Release/api_server               # Drogon API on :8080
    cpp/build/Release/worker                   # job worker

Then, from `frontend/`:

    npm install
    npm run dev                                # http://localhost:5173

The browser only calls its own origin under `/api/*`; the server forwards to the Drogon API
(`API_BASE_URL`, default `http://localhost:8080`). The API has no CORS support by design.

## Tests

    npm test                                   # unit + component tests (no backend needed)
    npm run check                              # svelte-check / TypeScript
    node scripts/smoke.mjs                     # live end-to-end check (needs the stack above)

## Production build

    npm run build
    API_BASE_URL=http://api:8080 npm start     # sets BODY_SIZE_LIMIT=100M

`BODY_SIZE_LIMIT` matters: adapter-node rejects request bodies over 512 KB by default, which
would reject real uploads (the API accepts up to 100 MB).

## Layout

- `src/lib/api.ts` — typed client for the Drogon endpoints · `src/lib/types.ts` — API types
- `src/lib/csvHeader.ts` — client-side header validation · `src/lib/poller.ts` — job polling
- `src/lib/chartOptions.ts` + `components/Chart.svelte` — ECharts histograms
- `src/lib/server/proxy.ts` + `src/hooks.server.ts` — the `/api` proxy
- `src/routes/+page.svelte` — upload · `src/routes/jobs/[id]/+page.svelte` — status → dashboard

## Known gaps

- No PIT/calibration diagnostic: it needs a held-out future, which production uploads do not have.
- CLV intervals are shown only when the API reports them (`has_clv_interval`); the worker does not
  yet fit a conformal interval, so today the table shows point CLV only.
```

- [ ] **Step 3: Run the full verification**

Run (from `frontend/`): `npm test` — Expected: all suites PASS.
Run: `npm run check` — Expected: 0 errors, 0 warnings that matter.
Run: `npm run build` — Expected: succeeds and writes `frontend/build/`.
With the live stack up (see README): `npm run dev` in one terminal, then `node scripts/smoke.mjs` — Expected: six `ok` lines then `SMOKE PASSED`. Then open `http://localhost:5173/`, drop `models/ingest_sample.csv`, and confirm by eye: status page → dashboard with tiles, three charts, a table that sorts/filters/pages, and a CSV that downloads. Also drop `models/ingest_bad_missing_column.csv` and confirm the inline "Missing required column" error appears without any network upload.

- [ ] **Step 4: Update the spec**

In `docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md`, under §4.1's Dashboard bullet, append: `(The PIT/calibration diagnostic is deferred: it needs a held-out future that production uploads do not have — see the Phase 5 plan.)` and in §9 mark step 5 as `— implemented per docs/superpowers/plans/2026-10-02-sveltekit-frontend.md`.

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts frontend/README.md docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md
git commit -m "feat(frontend): live-stack smoke script, run docs, and spec status for Phase 5"
```

---

## Self-Review

**Spec coverage (§4.1, §4.2, §6, §9.5):**
- Upload page, drag-drop, client-side header/type validation → Tasks 5, 6.
- Job status view polling `GET /jobs/{id}` → Task 7.
- Dashboard: forecast distribution, P(active) histogram (ECharts via a Svelte wrapper) → Tasks 8, 9. **PIT/calibration diagnostic → deliberately deferred** (no holdout in production; recorded in Global Constraints, Task 12 README and spec edit) — needs the author's sign-off.
- Sortable/filterable per-customer table (expected purchases, P(alive), CLV point + interval) → Task 10 (interval shown only when the API has one — worker currently collapses it to the point).
- Export button → `GET /jobs/{id}/export.csv` → Task 11.
- Spec §6 partial data flagged per row → `QualityBadge`, placeholder dashes, explainer (Tasks 10, 11).
- Backend gaps the frontend exposed (no cohort aggregate endpoint; no sort/filter) → Tasks 1–2, additive and tested.
- Not covered by design: auth/billing/API access (spec §10), MCMC path (§9.6).

**Placeholder scan:** no TBD/TODO; every code step has full code. Two items are explicitly conditional rather than vague — Task 5 Step 4 and Task 10 (whether `insufficient_history` rows carry a real CLV) must be checked against `worker.cpp` by the implementer; the plan says exactly where to look.

**Type consistency:** `ResultsQuery` fields (`page,pageSize,sort,order,quality,q`) are defined in Task 4 and used identically in Tasks 4 (client), 10 (table, tests). `JobSummary.histograms.{p_alive,expected_purchases,clv_point}`, `quality_counts`, `has_clv_interval` match the Task 1 JSON exactly. `Histogram {edges,counts}` is consumed by `histogramOption` (Task 8). `api.getJob` is passed unbound in Task 7 — it is an arrow function from `createApi`, so this is safe. `exportUrl` is exported from `api.ts` (Task 4) and imported in Task 11.

**Risks to watch during execution:** (1) Vite/Svelte-plugin/Vitest peer versions in Task 3; (2) `$app/state` (`page.params`) requires SvelteKit ≥ 2.12 — pinned `^2.15`; (3) the first C++ rebuild may be slow; (4) the Svelte 5 + jsdom + Testing Library combination can need `svelteTesting()` plugin ordering tweaks (already included) — if component tests report "mount is not available on the server", confirm `resolve.conditions` includes `browser`, which `svelteTesting()` sets.
