# Drogon API + Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the product's HTTP surface end to end: `POST /uploads` accepts a raw
transaction-log CSV, enqueues a job; a separate worker process dequeues it, runs the
already-built pipeline (`ingest_csv` → `AmortizedModel` → Gamma-Gamma CLV) over it, and writes
results to Postgres; `GET /jobs/{id}`, `GET /jobs/{id}/results`, and `GET
/jobs/{id}/export.csv` expose status and output. This is Phase 4 of the spec's §9 phased
build order — the first phase where the `cpp/` library built in Phases 1–3 is called from a
live request path instead of a CLI demo or a test.

**Architecture:** Two new executables alongside the existing `main` (demo) and `unit_tests`:
`api_server` (Drogon HTTP process — accepts uploads, serves job status/results, never touches
the estimation pipeline directly) and `worker` (a polling loop — dequeues job IDs from Redis,
runs the real pipeline, writes to Postgres, updates job status). Both link the same
`amortized_inference` library Phases 1–3 already built, which gains three new modules this
plan adds: `db` (Postgres access via Drogon's async ORM client), `queue` (Redis job
queue/status-cache via Drogon's Redis client), and `storage` (an interface for where uploaded
CSVs and generated exports live, with a local-filesystem implementation now and a documented
seam for swapping in MinIO later — see Global Constraints).

**Tech Stack:** C++20, Drogon (HTTP framework, with its own async Postgres ORM client and
Redis client — no separate database driver needed), PostgreSQL, Redis, continuing the existing
`cpp/` CMake+vcpkg project (Catch2, nlohmann/json, ONNX Runtime, Arrow already wired from
Phases 1–3).

**Spec:** [docs/superpowers/specs/2026-09-26-clv-forecasting-saas-design.md](../specs/2026-09-26-clv-forecasting-saas-design.md)
— this plan implements Phase 4 of that spec's §9 phased build order ("Drogon API: upload →
validate → enqueue → worker picks up → writes results to Postgres"), §4.2 (API endpoints),
§4.3 (worker pipeline), §4.4/§4.4.1 (storage + schema), and §6 (error handling). Phase 5
(SvelteKit frontend) is a separate plan, written after this one lands, and only needs this
plan's four HTTP endpoints to exist — nothing about the frontend is assumed here.

## Global Constraints

- **MinIO is deferred; uploads and exports live on local disk for this phase.** The spec's
  §4.4 names MinIO as the blob store, but wiring in an S3-compatible client (`aws-sdk-cpp`'s
  S3 module is the only vcpkg-available option and is a very heavy dependency — noticeably
  larger than Arrow, which was already the heaviest so far) is a poor trade for an MVP phase
  whose actual goal is proving the upload→job→worker→results loop works. `cpp/include/pareto_nbd/storage.hpp`'s
  `UploadStorage` interface (Task 3) is the seam: everything above it (the API handlers, the
  worker) calls `storage->put(...)`/`storage->get(...)`, never a filesystem or S3 API
  directly, so swapping in a real MinIO-backed implementation later is additive, not a
  rewrite. This mirrors the same kind of pragmatic scope call Phase 3 made choosing a linear
  scan over Arrow's `Aggregate` API — documented here rather than silently deviating from the
  spec.
- **Docker Desktop is a hard prerequisite for Tasks 2 onward** (Postgres + Redis). This
  machine currently has no Docker, no `psql`, no `redis-cli` on `PATH` — confirmed via `Get-Command`
  and `docker --version` before writing this plan. Task 1 is Python/C++-free installation +
  a `docker-compose.yml` and has no such dependency; pause at the end of Task 1 for a human to
  confirm Docker Desktop is installed and `docker compose up -d` has been run before
  proceeding, the same pattern the Phase 1 plan used for the C++ toolchain gap.
- **New vcpkg dependency:** `drogon`, with features `["postgres", "redis"]` added to
  `cpp/vcpkg.json`. Per the installed port's `vcpkg.json`, both features pull in Drogon's
  `orm` feature automatically (`libpq` for postgres, `hiredis` for redis) — no separate
  database client libraries need to be added by hand. The CMake target is a single
  `Drogon::Drogon` (confirmed via the port's `usage` file), unlike Arrow's
  shared-vs-static ambiguity.
- **Drogon API surface risk.** Unlike Arrow (whose exact API this repo has now exercised
  three times), nothing in this codebase has used Drogon yet. The code in this plan reflects
  Drogon's documented, stable async patterns (`drogon::app().registerHandler(...)`,
  `drogon::orm::DbClientPtr` + `execSqlAsync`, `drogon::app().getRedisClient()` +
  `execCommandAsync`) as of this plan's writing, but — same caveat as every Arrow task in the
  Phase 3 plan — check the installed headers under
  `build/vcpkg_installed/<triplet>/include/drogon/` if something doesn't compile as written,
  and note the deviation rather than guessing silently.
- **Test strategy for Postgres/Redis-dependent code:** Catch2 (v3, already in use) supports a
  `SKIP()` macro inside a `TEST_CASE`. Every test that needs a live Postgres or Redis
  connection checks reachability first (a short-timeout connect attempt) and calls `SKIP("...")`
  if unreachable, rather than failing — the same non-blocking-optional-dependency pattern
  already established in this codebase's Python side (`pytest.importorskip` for
  `lightgbm`/`econml`/`torch` in `tests/test_gear2.py`/`tests/test_phase2.py`). CI (which has
  no Postgres/Redis service containers configured) will skip these; a developer with
  `docker compose up -d` running will get full coverage.
- **`businesses` bootstrap:** per spec §4.4.1, multi-tenancy doesn't exist yet — there is
  exactly one row in `businesses`, created once. Task 2's schema migration seeds it (a fixed,
  well-known UUID) so every later task can hardcode that ID rather than building
  business-lookup logic this phase doesn't need.
- **Numeric/error-handling conventions carried over from Phase 3:** reuse `IngestError` for
  upload validation (§6 "malformed CSV, missing required columns, or empty file is rejected...
  with a specific error before a job is ever enqueued" is exactly what `LoadRawTable` already
  throws) — translate it to an HTTP 400 with its `what()` message, don't re-implement
  validation. Job failures (§6 "worker-side exceptions... mark the job `failed` with a
  user-facing reason string; raw stack traces are not surfaced") follow the same rule: catch
  at the worker's top level, store `e.what()` in `jobs.error_reason`, never a stack trace.

---

### Task 1: vcpkg Drogon dependency + Docker Compose for local Postgres/Redis

**Files:**
- Modify: `cpp/vcpkg.json`
- Modify: `cpp/CMakeLists.txt`
- Create: `docker-compose.yml` (repo root)
- Create: `cpp/include/pareto_nbd/version.hpp` — no change needed, just confirming the
  scaffold pattern; actual new files below
- Create: `cpp/src/api_main.cpp` (minimal — a single "hello" route, smoke test only)
- Create: `cpp/tests/test_api_smoke.cpp`

**Interfaces:**
- Produces: a running `api_server` binary answering `GET /healthz` with `200 OK` — nothing
  else yet. Proves Drogon links and starts before any task depends on it.

- [ ] **Step 1: Add the Drogon dependency and Docker Compose services**

```json
// cpp/vcpkg.json — add to "dependencies"
{
  "name": "drogon",
  "features": ["postgres", "redis"]
}
```

```yaml
# docker-compose.yml (repo root)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: pareto_nbd
      POSTGRES_PASSWORD: pareto_nbd_dev
      POSTGRES_DB: pareto_nbd
    ports:
      - "5432:5432"
    volumes:
      - pareto_nbd_pg_data:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pareto_nbd_pg_data:
```

- [ ] **Step 2: Write a minimal Drogon smoke test**

```cpp
// cpp/tests/test_api_smoke.cpp
#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include <drogon/HttpAppFramework.h>
#include <thread>
#include <chrono>

// Starts the Drogon event loop on a background thread for the duration of this one test
// case, hits it with a real HTTP client, and shuts it down -- proves the Drogon dependency
// actually links and an app can listen and respond, before any later task builds on it.
TEST_CASE("Drogon app starts and answers a request", "[api][smoke]") {
    drogon::app().addListener("127.0.0.1", 18080);
    drogon::app().registerHandler(
        "/healthz",
        [](const drogon::HttpRequestPtr&,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("ok");
            callback(resp);
        },
        {drogon::Get});

    std::thread server_thread([]() { drogon::app().run(); });
    std::this_thread::sleep_for(std::chrono::milliseconds(300));  // let the loop start

    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18080");
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setPath("/healthz");
    auto [result, response] = client->sendRequest(req, 5.0);
    REQUIRE(result == drogon::ReqResult::Ok);
    REQUIRE(response->getBody() == "ok");

    drogon::app().getLoop()->queueInLoop([]() { drogon::app().quit(); });
    server_thread.join();
}
```

Modify `cpp/CMakeLists.txt`:

```cmake
# add near the top, alongside the other find_package calls
find_package(Drogon CONFIG REQUIRED)

# new executable, alongside the existing main/unit_tests
add_executable(api_server src/api_main.cpp)
target_link_libraries(api_server PRIVATE amortized_inference Drogon::Drogon)

# add tests/test_api_smoke.cpp to unit_tests' sources
# add Drogon::Drogon to unit_tests' target_link_libraries
```

```cpp
// cpp/src/api_main.cpp
#include <drogon/drogon.h>

int main() {
    drogon::app().addListener("0.0.0.0", 8080);
    drogon::app().registerHandler(
        "/healthz",
        [](const drogon::HttpRequestPtr&,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("ok");
            callback(resp);
        },
        {drogon::Get});
    drogon::app().run();
    return 0;
}
```

- [ ] **Step 3: Configure, build, run**

Run (PowerShell, MSVC environment imported first — see the toolchain note carried over from
the Phase 3 plan: `cmd /c` importing `vcvars64.bat`'s environment is still required, cl.exe is
not on `PATH` by default):
```powershell
cmake --preset default
cmake --build build
ctest --test-dir build --output-on-failure
```
Expected: vcpkg builds Drogon + its Postgres/Redis client deps from source (another
heavyweight first-build, though smaller than Arrow) — this can take 15–30 minutes the first
time. The new `[api][smoke]` test passes; all prior Phase 1–3 tests still pass.

- [ ] **Step 4: Human checkpoint — Docker Desktop**

**Pause here.** Everything from Task 2 onward needs a reachable Postgres and Redis. Confirm
with a human that:
1. Docker Desktop is installed and running.
2. `docker compose up -d` has been run from the repo root (starts both services from Step 1's
   `docker-compose.yml`).
3. `docker compose ps` shows both `postgres` and `redis` as `running`/`healthy`.

Do not start Task 2 until this is confirmed — Task 2's own tests need a live Postgres to do
anything meaningful.

- [ ] **Step 5: Commit**

```bash
git add cpp/vcpkg.json cpp/CMakeLists.txt cpp/src/api_main.cpp cpp/tests/test_api_smoke.cpp docker-compose.yml
git commit -m "feat(cpp): scaffold Drogon api_server with a health-check smoke test"
```

---

### Task 2: Postgres schema + connection + smoke test

**Files:**
- Create: `db/schema.sql`
- Create: `cpp/include/pareto_nbd/db.hpp`
- Create: `cpp/src/db.cpp`
- Create: `cpp/tests/test_db.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `pareto_nbd::ConnectDb(const std::string& conn_str) -> drogon::orm::DbClientPtr`
  (a thin wrapper documenting the expected connection-string shape) and
  `pareto_nbd::ApplySchema(drogon::orm::DbClientPtr db, const std::string& schema_sql_path)`,
  both consumed by every later Postgres-touching task. `kDefaultBusinessId`, the fixed UUID
  seeded by the schema, consumed by Tasks 5–8.

- [ ] **Step 1: Write the schema exactly per the spec's §4.4.1**

```sql
-- db/schema.sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS businesses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id  UUID NOT NULL REFERENCES businesses(id),
    status       TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
    upload_path  TEXT NOT NULL,
    error_reason TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS customers (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id           UUID NOT NULL REFERENCES businesses(id),
    external_customer_id  TEXT NOT NULL,
    first_seen_job_id     UUID NOT NULL REFERENCES jobs(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (business_id, external_customer_id)
);

CREATE TABLE IF NOT EXISTS forecast_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              UUID NOT NULL REFERENCES jobs(id),
    customer_id         UUID NOT NULL REFERENCES customers(id),
    expected_purchases  DOUBLE PRECISION NOT NULL,
    p_alive             DOUBLE PRECISION NOT NULL,
    clv_point           DOUBLE PRECISION NOT NULL,
    clv_lower           DOUBLE PRECISION NOT NULL,
    clv_upper           DOUBLE PRECISION NOT NULL,
    model_params        JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, customer_id)
);

-- Seed the single-tenant bootstrap row (spec §4.4.1: "populated with a single row until
-- multi-tenancy ships"), with a fixed, well-known id so application code can hardcode it.
INSERT INTO businesses (id, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'default')
ON CONFLICT (id) DO NOTHING;
```

- [ ] **Step 2: Write the failing test**

```cpp
// cpp/tests/test_db.cpp
#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/db.hpp"

TEST_CASE("ConnectDb connects and ApplySchema seeds the default business", "[db]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable at " + pareto_nbd::kTestConnString); }

    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto result = db->execSqlSync(
        "SELECT name FROM businesses WHERE id = $1::uuid", pareto_nbd::kDefaultBusinessId);
    REQUIRE(result.size() == 1);
    REQUIRE(result[0]["name"].as<std::string>() == "default");
}
```

Add `PROJECT_ROOT_DIR` as a compile definition (parallel to the existing
`PROJECT_MODELS_DIR`) pointing at the repo root (`cpp/..`), since `db/schema.sql` lives
outside `cpp/`.

- [ ] **Step 3: Run to verify it fails**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_db`
Expected: FAIL — `pareto_nbd::ConnectDb`/`ApplySchema`/`kDefaultBusinessId`/`kTestConnString`
don't exist yet.

- [ ] **Step 4: Write the implementation**

```cpp
// cpp/include/pareto_nbd/db.hpp
#pragma once
#include <drogon/orm/DbClient.h>
#include <string>

namespace pareto_nbd {

// Local dev connection string, matching docker-compose.yml's postgres service (Task 1).
// Production wiring (env-var override) is a Phase-4-hardening concern, not this plan's.
inline const std::string kTestConnString =
    "host=127.0.0.1 port=5432 dbname=pareto_nbd user=pareto_nbd password=pareto_nbd_dev";

inline const std::string kDefaultBusinessId = "00000000-0000-0000-0000-000000000001";

// Connects synchronously (a short-timeout attempt) so callers can detect "Postgres isn't
// running" up front and SKIP their test, rather than hanging on Drogon's async retry loop.
// Returns nullptr on failure instead of throwing -- this is a reachability probe, not a
// runtime connection (the returned DbClientPtr, once obtained, is used for real async calls).
drogon::orm::DbClientPtr ConnectDb(const std::string& conn_str);

// Splits schema_sql_path's content on ';' and executes each non-empty statement in order.
// A hand-rolled splitter is adequate for this project's own schema.sql (no stored
// procedures, no semicolons inside string literals) -- do not generalize it into a real SQL
// parser.
void ApplySchema(drogon::orm::DbClientPtr db, const std::string& schema_sql_path);

}  // namespace pareto_nbd
```

```cpp
// cpp/src/db.cpp
#include "pareto_nbd/db.hpp"

#include <fstream>
#include <sstream>
#include <thread>
#include <chrono>
#include <future>

namespace pareto_nbd {

drogon::orm::DbClientPtr ConnectDb(const std::string& conn_str) {
    try {
        auto db = drogon::orm::DbClient::newPgClient(conn_str, 1 /* connection pool size */);
        // newPgClient connects asynchronously; force a real round trip with a short
        // deadline so an unreachable Postgres fails fast instead of hanging.
        auto promise = std::make_shared<std::promise<bool>>();
        auto future = promise->get_future();
        db->execSqlAsync(
            "SELECT 1",
            [promise](const drogon::orm::Result&) { promise->set_value(true); },
            [promise](const drogon::orm::DrogonDbException&) { promise->set_value(false); });
        if (future.wait_for(std::chrono::seconds(2)) != std::future_status::ready ||
            !future.get()) {
            return nullptr;
        }
        return db;
    } catch (...) {
        return nullptr;
    }
}

void ApplySchema(drogon::orm::DbClientPtr db, const std::string& schema_sql_path) {
    std::ifstream f(schema_sql_path);
    std::stringstream buf;
    buf << f.rdbuf();
    std::string sql = buf.str();

    size_t start = 0;
    while (start < sql.size()) {
        size_t end = sql.find(';', start);
        if (end == std::string::npos) break;
        std::string stmt = sql.substr(start, end - start);
        // skip whitespace-only/comment-only fragments between real statements
        if (stmt.find_first_not_of(" \t\r\n") != std::string::npos) {
            db->execSqlSync(stmt);
        }
        start = end + 1;
    }
}

}  // namespace pareto_nbd
```

Note the smoke-test-in-`ConnectDb` pattern above depends on Drogon's connection object being
usable even before its async connection callback has necessarily fired — verify this against
actual Drogon behavior when implementing; if `newPgClient` throws or the client isn't usable
until connected, adjust `ConnectDb` accordingly and note the deviation (this is exactly the
kind of Drogon-API-surface risk flagged in Global Constraints).

Add `db/schema.sql` and `PROJECT_ROOT_DIR` wiring to `cpp/CMakeLists.txt`; add `src/db.cpp` to
`amortized_inference`'s sources; add `tests/test_db.cpp` to `unit_tests`' sources.

- [ ] **Step 5: Run to verify it passes**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_db`
Expected: PASS if Docker Compose's Postgres is up (Task 1 Step 4's checkpoint); SKIP with a
clear message otherwise.

- [ ] **Step 6: Commit**

```bash
git add db/schema.sql cpp/include/pareto_nbd/db.hpp cpp/src/db.cpp cpp/tests/test_db.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): Postgres schema + ConnectDb/ApplySchema with a SKIP-if-unreachable smoke test"
```

---

### Task 3: Local-disk upload storage abstraction

**Files:**
- Create: `cpp/include/pareto_nbd/storage.hpp`
- Create: `cpp/src/storage.cpp`
- Create: `cpp/tests/test_storage.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `UploadStorage` (abstract interface: `Put(key, bytes) -> void`,
  `GetPath(key) -> std::string`, `Exists(key) -> bool`) and
  `LocalDiskStorage` (the only implementation this plan builds), consumed by Task 5 (upload
  endpoint writes) and Task 6 (worker reads). This is the seam Global Constraints names for a
  future MinIO swap — no external service, pure filesystem, fully unit-testable without
  Docker.

- [ ] **Step 1: Write the failing tests**

```cpp
// cpp/tests/test_storage.cpp
#include <catch2/catch_test_macros.hpp>
#include <filesystem>
#include "pareto_nbd/storage.hpp"

TEST_CASE("LocalDiskStorage round-trips a put through GetPath", "[storage]") {
    auto tmp_dir = std::filesystem::temp_directory_path() / "pareto_nbd_storage_test";
    std::filesystem::remove_all(tmp_dir);
    pareto_nbd::LocalDiskStorage storage(tmp_dir.string());

    REQUIRE_FALSE(storage.Exists("uploads/abc.csv"));
    storage.Put("uploads/abc.csv", "customer_id,transaction_date\nA,2024-01-01\n");
    REQUIRE(storage.Exists("uploads/abc.csv"));

    std::string path = storage.GetPath("uploads/abc.csv");
    std::ifstream f(path);
    std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    REQUIRE(content == "customer_id,transaction_date\nA,2024-01-01\n");

    std::filesystem::remove_all(tmp_dir);
}

TEST_CASE("LocalDiskStorage creates nested directories as needed", "[storage]") {
    auto tmp_dir = std::filesystem::temp_directory_path() / "pareto_nbd_storage_test2";
    std::filesystem::remove_all(tmp_dir);
    pareto_nbd::LocalDiskStorage storage(tmp_dir.string());

    storage.Put("a/b/c/deep.csv", "x");
    REQUIRE(storage.Exists("a/b/c/deep.csv"));

    std::filesystem::remove_all(tmp_dir);
}
```

- [ ] **Step 2: Run to verify they fail**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_storage`
Expected: FAIL — `pareto_nbd::LocalDiskStorage` doesn't exist yet.

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/include/pareto_nbd/storage.hpp
#pragma once
#include <string>

namespace pareto_nbd {

// Where uploaded CSVs and generated exports live. Every caller (the upload endpoint, the
// worker, the export endpoint) goes through this interface, never a filesystem or S3 API
// directly -- swapping LocalDiskStorage for a MinIO-backed implementation later touches only
// this file's implementation, not any call site. See the plan's Global Constraints for why
// MinIO itself isn't built in this phase.
class UploadStorage {
public:
    virtual ~UploadStorage() = default;
    virtual void Put(const std::string& key, const std::string& bytes) = 0;
    virtual bool Exists(const std::string& key) = 0;
    // Returns a filesystem path ingest_csv (or any other local reader) can open directly.
    // A future remote-storage implementation would instead download to a temp file here and
    // return that path -- callers never need to know the difference.
    virtual std::string GetPath(const std::string& key) = 0;
};

class LocalDiskStorage : public UploadStorage {
public:
    explicit LocalDiskStorage(std::string root_dir);
    void Put(const std::string& key, const std::string& bytes) override;
    bool Exists(const std::string& key) override;
    std::string GetPath(const std::string& key) override;

private:
    std::string root_dir_;
};

}  // namespace pareto_nbd
```

```cpp
// cpp/src/storage.cpp
#include "pareto_nbd/storage.hpp"

#include <filesystem>
#include <fstream>

namespace pareto_nbd {

LocalDiskStorage::LocalDiskStorage(std::string root_dir) : root_dir_(std::move(root_dir)) {
    std::filesystem::create_directories(root_dir_);
}

std::string LocalDiskStorage::GetPath(const std::string& key) {
    return (std::filesystem::path(root_dir_) / key).string();
}

bool LocalDiskStorage::Exists(const std::string& key) {
    return std::filesystem::exists(GetPath(key));
}

void LocalDiskStorage::Put(const std::string& key, const std::string& bytes) {
    auto path = std::filesystem::path(GetPath(key));
    std::filesystem::create_directories(path.parent_path());
    std::ofstream f(path, std::ios::binary);
    f << bytes;
}

}  // namespace pareto_nbd
```

Add `src/storage.cpp` to `amortized_inference`'s sources; add `tests/test_storage.cpp` (plus
`#include <fstream>` if not already pulled in transitively) to `unit_tests`' sources.

- [ ] **Step 4: Run to verify they pass**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_storage`
Expected: PASS (2 new test cases) — no Docker/Postgres/Redis needed for this task at all.

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/storage.hpp cpp/src/storage.cpp cpp/tests/test_storage.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): UploadStorage interface + LocalDiskStorage implementation"
```

---

### Task 4: Redis job queue + status cache

**Files:**
- Create: `cpp/include/pareto_nbd/queue.hpp`
- Create: `cpp/src/queue.cpp`
- Create: `cpp/tests/test_queue.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `ConnectRedis(...) -> drogon::nosql::RedisClientPtr` (SKIP-if-unreachable pattern,
  mirroring `ConnectDb`), `EnqueueJob(redis, job_id)`, `DequeueJob(redis, timeout_seconds) ->
  std::optional<std::string>` (blocking pop with a timeout, so the worker's poll loop in Task
  6 doesn't busy-spin), consumed by Task 5 (enqueue on upload) and Task 6 (the worker's main
  loop).

- [ ] **Step 1: Write the failing tests**

```cpp
// cpp/tests/test_queue.cpp
#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/queue.hpp"

TEST_CASE("EnqueueJob then DequeueJob round-trips a job id", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    pareto_nbd::EnqueueJob(redis, "job-abc-123");
    auto got = pareto_nbd::DequeueJob(redis, 2);
    REQUIRE(got.has_value());
    REQUIRE(*got == "job-abc-123");
}

TEST_CASE("DequeueJob times out on an empty queue", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    auto got = pareto_nbd::DequeueJob(redis, 1);
    REQUIRE_FALSE(got.has_value());
}
```

- [ ] **Step 2: Run to verify they fail**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_queue`
Expected: FAIL — nothing in `queue.hpp` exists yet.

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/include/pareto_nbd/queue.hpp
#pragma once
#include <drogon/nosql/RedisClient.h>
#include <optional>
#include <string>

namespace pareto_nbd {

inline const std::string kTestRedisUri = "redis://127.0.0.1:6379";
inline const std::string kJobQueueKey = "pareto_nbd:jobs:queue";

drogon::nosql::RedisClientPtr ConnectRedis(const std::string& redis_uri);

void EnqueueJob(drogon::nosql::RedisClientPtr redis, const std::string& job_id);

// Blocking pop (Redis BLPOP) with a timeout in seconds; std::nullopt on timeout, the job id
// string otherwise. A timeout, not an infinite block, is what lets the worker's loop (Task 6)
// periodically check for a shutdown signal between dequeue attempts.
std::optional<std::string> DequeueJob(drogon::nosql::RedisClientPtr redis, int timeout_seconds);

}  // namespace pareto_nbd
```

```cpp
// cpp/src/queue.cpp
#include "pareto_nbd/queue.hpp"

#include <chrono>
#include <future>

namespace pareto_nbd {

drogon::nosql::RedisClientPtr ConnectRedis(const std::string& redis_uri) {
    try {
        auto redis = drogon::nosql::RedisClient::newRedisClient(
            trantor::InetAddress("127.0.0.1", 6379), 1 /* pool size */);
        auto promise = std::make_shared<std::promise<bool>>();
        auto future = promise->get_future();
        redis->execCommandAsync(
            [promise](const drogon::nosql::RedisResult&) { promise->set_value(true); },
            [promise](const drogon::nosql::RedisException&) { promise->set_value(false); },
            "PING");
        if (future.wait_for(std::chrono::seconds(2)) != std::future_status::ready ||
            !future.get()) {
            return nullptr;
        }
        return redis;
    } catch (...) {
        return nullptr;
    }
}

void EnqueueJob(drogon::nosql::RedisClientPtr redis, const std::string& job_id) {
    auto promise = std::make_shared<std::promise<void>>();
    auto future = promise->get_future();
    redis->execCommandAsync(
        [promise](const drogon::nosql::RedisResult&) { promise->set_value(); },
        [promise](const drogon::nosql::RedisException&) { promise->set_value(); },
        "RPUSH %s %s", kJobQueueKey.c_str(), job_id.c_str());
    future.wait();
}

std::optional<std::string> DequeueJob(drogon::nosql::RedisClientPtr redis, int timeout_seconds) {
    auto promise = std::make_shared<std::promise<std::optional<std::string>>>();
    auto future = promise->get_future();
    redis->execCommandAsync(
        [promise](const drogon::nosql::RedisResult& r) {
            // BLPOP replies with a 2-element array [key, value] on success, nil on timeout.
            if (r.type() == drogon::nosql::RedisResultType::kNil) {
                promise->set_value(std::nullopt);
            } else {
                promise->set_value(r.asArray()[1].asString());
            }
        },
        [promise](const drogon::nosql::RedisException&) { promise->set_value(std::nullopt); },
        "BLPOP %s %d", kJobQueueKey.c_str(), timeout_seconds);
    return future.get();
}

}  // namespace pareto_nbd
```

`ConnectRedis`'s exact constructor signature (`RedisClient::newRedisClient`'s parameters,
whether it takes a URI string directly vs. a `trantor::InetAddress`) and `RedisResult`'s exact
type-checking/array-access API are the highest-risk guesses in this task — check
`build/vcpkg_installed/<triplet>/include/drogon/nosql/RedisClient.h` and
`.../drogon/nosql/RedisResult.h` against what's written here and adjust; note any deviation in
the task report.

Add `src/queue.cpp` to `amortized_inference`'s sources; add `tests/test_queue.cpp` to
`unit_tests`' sources.

- [ ] **Step 4: Run to verify they pass**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_queue`
Expected: PASS (2 new cases) if Redis is up; SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/queue.hpp cpp/src/queue.cpp cpp/tests/test_queue.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): Redis job queue (EnqueueJob/DequeueJob) with a SKIP-if-unreachable test"
```

---

### Task 5: `POST /uploads` — validate, store, enqueue

**Files:**
- Modify: `cpp/src/api_main.cpp`
- Create: `cpp/tests/test_uploads_endpoint.cpp`
- Modify: `cpp/CMakeLists.txt` (compile definitions for the storage root / connection strings
  used by tests)

**Interfaces:**
- Produces: the real `POST /uploads` handler — accepts a raw CSV request body (not
  multipart/form-data; the simplest contract for this MVP is "the whole request body is the
  CSV file," documented in the handler's own comment; multipart form parsing is a Phase-5
  frontend-integration concern if the browser's file input needs it, not blocking this
  endpoint's core logic), validates it via `ingest_csv`'s existing `LoadRawTable` path,
  stores it via `UploadStorage`, inserts a `jobs` row, enqueues in Redis, returns
  `{"job_id": "..."}`.

- [ ] **Step 1: Write the failing tests**

```cpp
// cpp/tests/test_uploads_endpoint.cpp
#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"

// These tests assume api_server's handlers are registered by the same process-wide
// drogon::app() singleton Task 1's smoke test used -- see that test's start/stop pattern.
// Reuses the same fixture approach: start on a background thread, hit it, shut it down.

TEST_CASE("POST /uploads rejects a CSV with a missing required column", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }

    // ... start api_server on a background thread (same pattern as Task 1's smoke test) ...
    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18081");
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads");
    req->setBody("customer_id,amount\nA,10.0\n");  // no transaction_date column
    auto [result, response] = client->sendRequest(req, 5.0);

    REQUIRE(result == drogon::ReqResult::Ok);
    REQUIRE(response->getStatusCode() == drogon::k400BadRequest);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["error"].get<std::string>().find("transaction_date") != std::string::npos);
    // ... shut down ...
}

TEST_CASE("POST /uploads accepts a valid CSV and returns a job id", "[api][uploads]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }

    // ... start api_server ...
    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18081");
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads");
    req->setBody("customer_id,transaction_date,amount\nA,2024-01-01,10.0\nA,2024-01-08,5.0\n");
    auto [result, response] = client->sendRequest(req, 5.0);

    REQUIRE(result == drogon::ReqResult::Ok);
    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body.contains("job_id"));

    // the job row exists with status queued, and the id was pushed onto the Redis queue
    auto rows = db->execSqlSync(
        "SELECT status FROM jobs WHERE id = $1::uuid", body["job_id"].get<std::string>());
    REQUIRE(rows.size() == 1);
    REQUIRE(rows[0]["status"].as<std::string>() == "queued");
    auto dequeued = pareto_nbd::DequeueJob(redis, 2);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == body["job_id"].get<std::string>());
    // ... shut down ...
}
```

Write the actual start/stop boilerplate following Task 1's `test_api_smoke.cpp` pattern
exactly (same background-thread-plus-`queueInLoop`-quit approach); it's repeated here only in
outline to keep this brief focused on the assertions.

- [ ] **Step 2: Run to verify they fail**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_uploads`
Expected: FAIL — `/uploads` isn't registered yet (404).

- [ ] **Step 3: Implement the handler**

```cpp
// cpp/src/api_main.cpp — add near the /healthz handler
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/ingest.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"
#include <nlohmann/json.hpp>

// ... inside main(), before drogon::app().run() ...

static auto storage = std::make_shared<pareto_nbd::LocalDiskStorage>("./data/uploads");
static auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
static auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);

drogon::app().registerHandler(
    "/uploads",
    [](const drogon::HttpRequestPtr& req,
       std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
        std::string body(req->getBody());
        if (body.empty()) {
            auto resp = drogon::HttpResponse::newHttpJsonResponse(
                nlohmann::json{{"error", "empty request body"}}.dump());
            resp->setStatusCode(drogon::k400BadRequest);
            callback(resp);
            return;
        }

        std::string job_id_placeholder = drogon::utils::getUuid();
        std::string key = "uploads/" + job_id_placeholder + ".csv";
        storage->Put(key, body);

        // Validate via the exact same LoadRawTable path ingest_csv itself uses -- reuse the
        // error, don't re-implement CSV validation. ingest_csv itself isn't called here (the
        // worker does the real parse); this call's only job is to fail fast on a bad upload
        // before a job is ever enqueued, per spec §6.
        try {
            pareto_nbd::ingest_csv(storage->GetPath(key));
        } catch (const pareto_nbd::IngestError& e) {
            auto resp = drogon::HttpResponse::newHttpJsonResponse(
                nlohmann::json{{"error", std::string(e.what())}}.dump());
            resp->setStatusCode(drogon::k400BadRequest);
            callback(resp);
            return;
        }

        auto rows = db->execSqlSync(
            "INSERT INTO jobs (business_id, status, upload_path) "
            "VALUES ($1::uuid, 'queued', $2) RETURNING id",
            pareto_nbd::kDefaultBusinessId, key);
        std::string job_id = rows[0]["id"].as<std::string>();

        pareto_nbd::EnqueueJob(redis, job_id);

        auto resp = drogon::HttpResponse::newHttpJsonResponse(
            nlohmann::json{{"job_id", job_id}}.dump());
        callback(resp);
    },
    {drogon::Post});
```

Note: `ingest_csv` is called twice in this phase's full flow — once here (validation only,
result discarded) and once for real in the worker (Task 6). This is deliberate, not
wasteful: parsing a CSV is cheap relative to the AmortizedModel/Gamma-Gamma stages, and
keeping validation synchronous in the request path (so a bad upload never even reaches the
queue) matters more than saving one parse pass. If this becomes a real cost at scale, a
follow-up could pass the parsed result through Redis instead of just the job id — out of
scope for this MVP phase.

Add `#include "pareto_nbd/ingest.hpp"` (Phase 3) to `api_main.cpp`; add `tests/test_uploads_endpoint.cpp`
to `unit_tests`' sources; add whatever compile definitions the test file needs to know the
storage root/connection strings (reuse `PROJECT_MODELS_DIR`-style definitions if simplest, or
just hardcode the same `kTestConnString`/`kTestRedisUri` constants — no new machinery needed).

- [ ] **Step 4: Run to verify they pass**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_uploads`
Expected: PASS (2 cases) if Postgres+Redis are up; SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_main.cpp cpp/tests/test_uploads_endpoint.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): POST /uploads -- validate, store, enqueue"
```

---

### Task 6: Worker — dequeue, run the pipeline, write results

**Files:**
- Create: `cpp/src/worker_main.cpp`
- Create: `cpp/tests/test_worker.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: the `worker` executable's core loop as a testable function,
  `pareto_nbd::ProcessOneJob(job_id, db, storage) -> void` — dequeues nothing itself (the
  caller/`main` does that via Task 4's `DequeueJob`), just does everything from "load the CSV
  at `jobs.upload_path`" through "write `forecast_results` rows and mark the job `done` or
  `failed`". Tested directly (bypassing the queue) so the pipeline logic has fast, isolated
  coverage separate from the dequeue loop's own (thin) wiring.

- [ ] **Step 1: Write the failing test**

```cpp
// cpp/tests/test_worker.cpp
#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/storage.hpp"
#include "pareto_nbd/worker.hpp"

TEST_CASE("ProcessOneJob ingests, forecasts, and writes results for a queued job", "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    std::string key = "uploads/test-job.csv";
    storage.Put(key, "customer_id,transaction_date,amount\n"
                      "A,2024-01-01,10.0\nA,2024-01-08,5.0\nA,2024-01-22,8.0\n"
                      "B,2024-01-01,3.0\n"
                      "C,2024-01-15,20.0\nC,2024-01-29,6.0\n");

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) "
        "VALUES ($1::uuid, 'queued', $2) RETURNING id",
        pareto_nbd::kDefaultBusinessId, key);
    std::string job_id = rows[0]["id"].as<std::string>();

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto job_rows = db->execSqlSync("SELECT status, error_reason FROM jobs WHERE id = $1::uuid", job_id);
    REQUIRE(job_rows[0]["status"].as<std::string>() == "done");
    REQUIRE(job_rows[0]["error_reason"].isNull());

    auto result_rows = db->execSqlSync(
        "SELECT fr.expected_purchases, fr.p_alive, fr.clv_point, c.external_customer_id "
        "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
        "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id", job_id);
    REQUIRE(result_rows.size() == 3);  // A, B, C
    for (const auto& row : result_rows) {
        REQUIRE(row["expected_purchases"].as<double>() >= 0.0);
        double p_alive = row["p_alive"].as<double>();
        REQUIRE(p_alive >= 0.0);
        REQUIRE(p_alive <= 1.0);
    }
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_worker`
Expected: FAIL — `pareto_nbd::ProcessOneJob` doesn't exist yet.

- [ ] **Step 3: Write the implementation**

```cpp
// cpp/include/pareto_nbd/worker.hpp
#pragma once
#include <drogon/orm/DbClient.h>
#include <string>
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd {

// Loads the job's CSV, runs the full estimation pipeline (ingest -> amortized Pareto/NBD ->
// Gamma-Gamma CLV), writes one forecast_results row per customer, and marks the job done or
// failed. Never throws -- all failure modes are caught internally and recorded as the job's
// error_reason (spec §6: worker exceptions mark the job failed with a user-facing reason
// string, never a raw stack trace).
void ProcessOneJob(const std::string& job_id, drogon::orm::DbClientPtr db, UploadStorage& storage);

}  // namespace pareto_nbd
```

```cpp
// cpp/src/worker.cpp
#include "pareto_nbd/worker.hpp"

#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/clv.hpp"
#include "pareto_nbd/cohort_features.hpp"
#include "pareto_nbd/ingest.hpp"

#include <nlohmann/json.hpp>

namespace pareto_nbd {
namespace {

void MarkFailed(drogon::orm::DbClientPtr db, const std::string& job_id, const std::string& reason) {
    db->execSqlSync(
        "UPDATE jobs SET status = 'failed', error_reason = $2, completed_at = now() "
        "WHERE id = $1::uuid",
        job_id, reason);
}

}  // namespace

void ProcessOneJob(const std::string& job_id, drogon::orm::DbClientPtr db, UploadStorage& storage) {
    db->execSqlSync("UPDATE jobs SET status = 'running' WHERE id = $1::uuid", job_id);

    auto job_rows = db->execSqlSync("SELECT upload_path FROM jobs WHERE id = $1::uuid", job_id);
    if (job_rows.empty()) { return; }  // job vanished; nothing sensible to do
    std::string csv_path = storage.GetPath(job_rows[0]["upload_path"].as<std::string>());

    CustomerFeatures cohort;
    try {
        cohort = ingest_csv(csv_path);
    } catch (const IngestError& e) {
        MarkFailed(db, job_id, e.what());
        return;
    }

    // The models directory carries the committed ONNX/scaler artifacts (Phase 1) -- reuse
    // the same PROJECT_MODELS_DIR convention the demo/tests already use.
    AmortizedModel model(std::string(PROJECT_MODELS_DIR) + "/amortizer_mlp.onnx",
                          std::string(PROJECT_MODELS_DIR) + "/amortizer_scalers.json");
    auto features = cohort_features(cohort.x, cohort.t_x, cohort.T_cal);
    auto params = model.predict(features);

    GammaGammaParams gg{};
    std::vector<double> nu;
    bool have_clv = false;
    if (cohort.has_monetary) {
        try {
            gg = fit_gamma_gamma(cohort.x, cohort.m_bar);
            nu = posterior_mean_nu(cohort.x, cohort.m_bar, gg);
            have_clv = true;
        } catch (const std::exception&) {
            // A cohort with no x>0 customers at all can't fit Gamma-Gamma (see clv.hpp) --
            // per spec §6 this is a per-row/per-cohort limitation, not a hard job failure:
            // fall through and write purchase/P(alive) forecasts without a CLV figure.
        }
    }

    for (size_t i = 0; i < cohort.customer_id.size(); ++i) {
        auto cust_rows = db->execSqlSync(
            "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
            "VALUES ($1::uuid, $2, $3::uuid) "
            "ON CONFLICT (business_id, external_customer_id) DO UPDATE SET external_customer_id = EXCLUDED.external_customer_id "
            "RETURNING id",
            kDefaultBusinessId, cohort.customer_id[i], job_id);
        std::string customer_id = cust_rows[0]["id"].as<std::string>();

        // Expected future purchases and P(alive): closed-form Pareto/NBD quantities. This
        // plan does not re-derive them -- src/score.py's spp_predict-equivalent closed forms
        // were never ported to this cpp/ library in Phases 1-3 (only the amortized
        // *parameter* estimation and Gamma-Gamma CLV were). Wiring the actual Pareto/NBD
        // E[x*]/P(alive) closed-form formulas into cpp/ is therefore this task's own
        // remaining gap -- flagging explicitly rather than fabricating a placeholder number:
        // implement pareto_nbd::expected_purchases(r,alpha,s,beta,x,t_x,T_cal,horizon) and
        // pareto_nbd::p_alive(...) (the standard Fader/Hardie/Schmittlein-Morrison-Colombo
        // closed forms, already implemented in Python at src/score.py) as a small new
        // cpp/include/pareto_nbd/forecast.hpp/.cpp pair before this INSERT can use real
        // values -- see this task's Step 3 continuation below.
        double expected_purchases = 0.0;  // placeholder -- see forecast.hpp note above
        double p_alive = 0.0;             // placeholder -- see forecast.hpp note above
        double clv_point = have_clv ? nu[i] * expected_purchases : 0.0;

        nlohmann::json model_params{{"r", params.r}, {"alpha", params.alpha},
                                     {"s", params.s}, {"beta", params.beta}};
        if (have_clv) {
            model_params["gamma_gamma"] = {{"p", gg.p}, {"q", gg.q}, {"v", gg.v}};
        }

        db->execSqlSync(
            "INSERT INTO forecast_results "
            "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, model_params) "
            "VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8::jsonb) "
            "ON CONFLICT (job_id, customer_id) DO NOTHING",
            job_id, customer_id, expected_purchases, p_alive, clv_point, clv_point, clv_point,
            model_params.dump());
    }

    db->execSqlSync(
        "UPDATE jobs SET status = 'done', completed_at = now() WHERE id = $1::uuid", job_id);
}

}  // namespace pareto_nbd
```

**This task surfaces a real, previously-invisible gap:** the closed-form Pareto/NBD
`E[x*]`/`P(alive)` formulas (used everywhere in the Python research code via
`src/score.py`) were never ported to `cpp/` in Phases 1–3, which only needed
*parameter estimation* (`AmortizedModel`) and *CLV* (`fit_gamma_gamma`/`posterior_mean_nu`),
not the forecast formulas themselves. Do not fabricate placeholder numbers in the committed
implementation. Add this as a small preceding step within this same task (not a separate
plan) since it's a tightly-scoped, well-understood port (two closed-form functions, both with
existing Python references and existing golden-file-style validation already in the research
test suite) — read `src/score.py`'s `spp_predict`/the underlying Pareto/NBD E[x*] and P(alive)
formulas, port them to a new `cpp/include/pareto_nbd/forecast.hpp` + `cpp/src/forecast.cpp`
with their own Catch2 unit tests (hand-computable values, same convention as
`moments_to_gamma` in Phase 1), and use the real `expected_purchases`/`p_alive` functions in
place of the two placeholder lines above before this task is considered done.

Add `src/worker.cpp` (and `src/forecast.cpp`) to `amortized_inference`'s sources; add
`tests/test_worker.cpp` (and a `tests/test_forecast.cpp`) to `unit_tests`' sources.

```cpp
// cpp/src/worker_main.cpp
#include <drogon/drogon.h>
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"
#include "pareto_nbd/worker.hpp"

int main() {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    pareto_nbd::LocalDiskStorage storage("./data/uploads");

    if (!db || !redis) {
        std::cerr << "worker: Postgres/Redis unreachable, exiting\n";
        return 1;
    }

    std::cout << "worker: polling for jobs...\n";
    while (true) {
        auto job_id = pareto_nbd::DequeueJob(redis, 5);
        if (!job_id) { continue; }
        std::cout << "worker: processing job " << *job_id << "\n";
        pareto_nbd::ProcessOneJob(*job_id, db, storage);
    }
}
```

Add the `worker` executable to `cpp/CMakeLists.txt`, linking `amortized_inference` +
`Drogon::Drogon` the same way `api_server` does.

- [ ] **Step 4: Run to verify it passes**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R test_worker`
Expected: PASS if Postgres is up (this test bypasses Redis entirely, calling `ProcessOneJob`
directly); SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add cpp/include/pareto_nbd/worker.hpp cpp/src/worker.cpp cpp/src/worker_main.cpp cpp/include/pareto_nbd/forecast.hpp cpp/src/forecast.cpp cpp/tests/test_worker.cpp cpp/tests/test_forecast.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): worker pipeline (ingest -> forecast -> CLV -> Postgres) + closed-form Pareto/NBD forecast.cpp"
```

---

### Task 7: `GET /jobs/{id}` — status

**Files:**
- Modify: `cpp/src/api_main.cpp`
- Modify: `cpp/tests/test_uploads_endpoint.cpp` (or a new `test_jobs_endpoint.cpp` — implementer's call, keep it wherever reads most naturally)

**Interfaces:**
- Produces: `GET /jobs/{id}` returning `{"id":..., "status": "queued"|"running"|"done"|"failed", "error_reason": ...|null}`, 404 for an unknown id.

- [ ] **Step 1: Write the failing test**

```cpp
TEST_CASE("GET /jobs/{id} returns status for a known job, 404 for an unknown one", "[api][jobs]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = rows[0]["id"].as<std::string>();

    // ... start api_server ...
    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18081");

    auto req1 = drogon::HttpRequest::newHttpRequest();
    req1->setPath("/jobs/" + job_id);
    auto [r1, resp1] = client->sendRequest(req1, 5.0);
    REQUIRE(resp1->getStatusCode() == drogon::k200OK);
    auto body1 = nlohmann::json::parse(resp1->getBody());
    REQUIRE(body1["status"] == "done");

    auto req2 = drogon::HttpRequest::newHttpRequest();
    req2->setPath("/jobs/00000000-0000-0000-0000-000000000099");
    auto [r2, resp2] = client->sendRequest(req2, 5.0);
    REQUIRE(resp2->getStatusCode() == drogon::k404NotFound);
    // ... shut down ...
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `ctest --test-dir build --output-on-failure -R test_jobs`
Expected: FAIL — 404 on both paths (route not registered).

- [ ] **Step 3: Implement**

```cpp
// cpp/src/api_main.cpp — add alongside /uploads
drogon::app().registerHandler(
    "/jobs/{id}",
    [](const drogon::HttpRequestPtr&,
       std::function<void(const drogon::HttpResponsePtr&)>&& callback,
       const std::string& id) {
        auto rows = db->execSqlSync(
            "SELECT status, error_reason FROM jobs WHERE id = $1::uuid", id);
        if (rows.empty()) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setStatusCode(drogon::k404NotFound);
            callback(resp);
            return;
        }
        nlohmann::json body{{"id", id}, {"status", rows[0]["status"].as<std::string>()}};
        body["error_reason"] = rows[0]["error_reason"].isNull()
            ? nlohmann::json(nullptr) : nlohmann::json(rows[0]["error_reason"].as<std::string>());
        callback(drogon::HttpResponse::newHttpJsonResponse(body.dump()));
    },
    {drogon::Get});
```

Path-parameter binding (`{id}` → the handler's trailing `const std::string&` parameter) is
Drogon's documented pattern for `registerHandler`; verify the exact placeholder syntax against
the installed headers if it doesn't route as written (this is the same category of risk as
every other Drogon call in this plan).

- [ ] **Step 4: Run to verify it passes**

Run: `ctest --test-dir build --output-on-failure -R test_jobs`
Expected: PASS if Postgres is up; SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_main.cpp cpp/tests/test_uploads_endpoint.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): GET /jobs/{id} status endpoint"
```

---

### Task 8: `GET /jobs/{id}/results` — paginated JSON

**Files:**
- Modify: `cpp/src/api_main.cpp`
- Create: `cpp/tests/test_results_endpoint.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `GET /jobs/{id}/results?page=1&page_size=50` returning
  `{"job_id":..., "page":1, "page_size":50, "total":N, "customers": [{...}]}`; 404 for an
  unknown/not-yet-done job (spec: "JSON results once done" — a `queued`/`running` job has no
  results yet, so this returns 404 too, distinguishable from a truly-unknown id only via
  `GET /jobs/{id}` first, which is the documented client flow per spec §4.2's polling
  description).

- [ ] **Step 1: Write the failing test**

```cpp
// cpp/tests/test_results_endpoint.cpp
#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>
#include "pareto_nbd/db.hpp"

TEST_CASE("GET /jobs/{id}/results paginates forecast_results for a done job", "[api][results]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    for (int i = 0; i < 3; ++i) {
        auto cust_rows = db->execSqlSync(
            "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
            "VALUES ($1::uuid, $2, $3::uuid) RETURNING id",
            pareto_nbd::kDefaultBusinessId, "cust-" + std::to_string(i), job_id);
        db->execSqlSync(
            "INSERT INTO forecast_results "
            "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, model_params) "
            "VALUES ($1::uuid, $2::uuid, 1.0, 0.5, 10.0, 8.0, 12.0, '{}'::jsonb)",
            job_id, cust_rows[0]["id"].as<std::string>());
    }

    // ... start api_server, GET /jobs/{job_id}/results?page=1&page_size=2 ...
    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18081");
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setPath("/jobs/" + job_id + "/results");
    req->setParameter("page", "1");
    req->setParameter("page_size", "2");
    auto [result, response] = client->sendRequest(req, 5.0);

    REQUIRE(response->getStatusCode() == drogon::k200OK);
    auto body = nlohmann::json::parse(response->getBody());
    REQUIRE(body["total"] == 3);
    REQUIRE(body["customers"].size() == 2);
    // ... shut down ...
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `ctest --test-dir build --output-on-failure -R test_results`
Expected: FAIL — route not registered.

- [ ] **Step 3: Implement**

```cpp
// cpp/src/api_main.cpp
drogon::app().registerHandler(
    "/jobs/{id}/results",
    [](const drogon::HttpRequestPtr& req,
       std::function<void(const drogon::HttpResponsePtr&)>&& callback,
       const std::string& id) {
        int page = 1, page_size = 50;
        if (auto p = req->getParameter("page"); !p.empty()) page = std::stoi(p);
        if (auto ps = req->getParameter("page_size"); !ps.empty()) page_size = std::stoi(ps);

        auto count_rows = db->execSqlSync(
            "SELECT count(*) FROM forecast_results WHERE job_id = $1::uuid", id);
        int64_t total = count_rows[0]["count"].as<int64_t>();

        auto rows = db->execSqlSync(
            "SELECT c.external_customer_id, fr.expected_purchases, fr.p_alive, "
            "fr.clv_point, fr.clv_lower, fr.clv_upper "
            "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
            "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id "
            "LIMIT $2 OFFSET $3",
            id, page_size, (page - 1) * page_size);

        nlohmann::json customers = nlohmann::json::array();
        for (const auto& row : rows) {
            customers.push_back({
                {"customer_id", row["external_customer_id"].as<std::string>()},
                {"expected_purchases", row["expected_purchases"].as<double>()},
                {"p_alive", row["p_alive"].as<double>()},
                {"clv_point", row["clv_point"].as<double>()},
                {"clv_lower", row["clv_lower"].as<double>()},
                {"clv_upper", row["clv_upper"].as<double>()},
            });
        }
        nlohmann::json body{{"job_id", id}, {"page", page}, {"page_size", page_size},
                             {"total", total}, {"customers", customers}};
        callback(drogon::HttpResponse::newHttpJsonResponse(body.dump()));
    },
    {drogon::Get});
```

- [ ] **Step 4: Run to verify it passes**

Run: `ctest --test-dir build --output-on-failure -R test_results`
Expected: PASS if Postgres is up; SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_main.cpp cpp/tests/test_results_endpoint.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): GET /jobs/{id}/results -- paginated per-customer forecasts"
```

---

### Task 9: `GET /jobs/{id}/export.csv`

**Files:**
- Modify: `cpp/src/api_main.cpp`
- Create: `cpp/tests/test_export_endpoint.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `GET /jobs/{id}/export.csv` streaming all (unpaginated) `forecast_results` for a
  job as CSV, `Content-Type: text/csv`.

- [ ] **Step 1: Write the failing test**

```cpp
// cpp/tests/test_export_endpoint.cpp
#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include "pareto_nbd/db.hpp"

TEST_CASE("GET /jobs/{id}/export.csv streams a CSV of all results", "[api][export]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'done', 'x') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();
    auto cust_rows = db->execSqlSync(
        "INSERT INTO customers (business_id, external_customer_id, first_seen_job_id) "
        "VALUES ($1::uuid, 'cust-1', $2::uuid) RETURNING id",
        pareto_nbd::kDefaultBusinessId, job_id);
    db->execSqlSync(
        "INSERT INTO forecast_results "
        "(job_id, customer_id, expected_purchases, p_alive, clv_point, clv_lower, clv_upper, model_params) "
        "VALUES ($1::uuid, $2::uuid, 1.5, 0.75, 20.0, 15.0, 25.0, '{}'::jsonb)",
        job_id, cust_rows[0]["id"].as<std::string>());

    // ... start api_server ...
    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18081");
    auto req = drogon::HttpRequest::newHttpRequest();
    req->setPath("/jobs/" + job_id + "/export.csv");
    auto [result, response] = client->sendRequest(req, 5.0);

    REQUIRE(response->getStatusCode() == drogon::k200OK);
    std::string body = std::string(response->getBody());
    REQUIRE(body.find("customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper") == 0);
    REQUIRE(body.find("cust-1,1.5,0.75,20,15,25") != std::string::npos);
    // ... shut down ...
}
```

Adjust the exact numeric-formatting assertion (`"20,15,25"` vs `"20.0,15.0,25.0"`) once you
see how the implementation actually formats doubles — don't over-fit the test to a guess; the
point is CSV structure + presence of the row, not exact float-to-string formatting.

- [ ] **Step 2: Run to verify it fails**

Run: `ctest --test-dir build --output-on-failure -R test_export`
Expected: FAIL — route not registered.

- [ ] **Step 3: Implement**

```cpp
// cpp/src/api_main.cpp
drogon::app().registerHandler(
    "/jobs/{id}/export.csv",
    [](const drogon::HttpRequestPtr&,
       std::function<void(const drogon::HttpResponsePtr&)>&& callback,
       const std::string& id) {
        auto rows = db->execSqlSync(
            "SELECT c.external_customer_id, fr.expected_purchases, fr.p_alive, "
            "fr.clv_point, fr.clv_lower, fr.clv_upper "
            "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
            "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id", id);

        std::ostringstream csv;
        csv << "customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper\n";
        for (const auto& row : rows) {
            csv << row["external_customer_id"].as<std::string>() << ","
                << row["expected_purchases"].as<double>() << ","
                << row["p_alive"].as<double>() << ","
                << row["clv_point"].as<double>() << ","
                << row["clv_lower"].as<double>() << ","
                << row["clv_upper"].as<double>() << "\n";
        }

        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setContentTypeCode(drogon::CT_TEXT_PLAIN);  // Drogon may not have a built-in
                                                            // CT_TEXT_CSV; set the header
                                                            // directly if so -- verify against
                                                            // drogon::ContentType's enum.
        resp->addHeader("Content-Type", "text/csv");
        resp->setBody(csv.str());
        callback(resp);
    },
    {drogon::Get});
```

- [ ] **Step 4: Run to verify it passes**

Run: `ctest --test-dir build --output-on-failure -R test_export`
Expected: PASS if Postgres is up; SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add cpp/src/api_main.cpp cpp/tests/test_export_endpoint.cpp cpp/CMakeLists.txt
git commit -m "feat(cpp): GET /jobs/{id}/export.csv"
```

---

### Task 10: Partial-data handling — per-row flags for thin customer history

**Files:**
- Modify: `cpp/src/worker.cpp`
- Modify: `db/schema.sql` (one additive column)
- Modify: `cpp/tests/test_worker.cpp`

**Interfaces:**
- Produces: a `forecast_results.data_quality` text column (`'ok'` or `'insufficient_history'`)
  and worker logic that sets it per customer, per spec §6: "customers with insufficient
  history for a given model (e.g. single-transaction customers for Pareto/GGG regularity) are
  flagged per-row in the results rather than failing the whole job."

- [ ] **Step 1: Write the failing test**

```cpp
// append to cpp/tests/test_worker.cpp
TEST_CASE("ProcessOneJob flags single-transaction customers as insufficient_history", "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads2");
    storage.Put("uploads/thin.csv",
                "customer_id,transaction_date,amount\n"
                "A,2024-01-01,10.0\nA,2024-01-08,5.0\n"  // A has repeats: sufficient
                "B,2024-01-01,3.0\n");                    // B: single transaction, x=0

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'queued', 'uploads/thin.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto rows = db->execSqlSync(
        "SELECT c.external_customer_id, fr.data_quality "
        "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
        "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id", job_id);
    REQUIRE(rows.size() == 2);
    REQUIRE(rows[0]["external_customer_id"].as<std::string>() == "A");
    REQUIRE(rows[0]["data_quality"].as<std::string>() == "ok");
    REQUIRE(rows[1]["external_customer_id"].as<std::string>() == "B");
    REQUIRE(rows[1]["data_quality"].as<std::string>() == "insufficient_history");
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `ctest --test-dir build --output-on-failure -R test_worker`
Expected: FAIL — `data_quality` column doesn't exist / isn't populated.

- [ ] **Step 3: Implement**

```sql
-- append to db/schema.sql
ALTER TABLE forecast_results ADD COLUMN IF NOT EXISTS data_quality TEXT NOT NULL DEFAULT 'ok';
```

```cpp
// cpp/src/worker.cpp -- inside the per-customer loop, before the INSERT
std::string data_quality = (cohort.x[i] > 0) ? "ok" : "insufficient_history";
```

Add `data_quality` to the `forecast_results` INSERT's column list and bind list.

Re-run Task 2's schema test manually if needed to confirm `ApplySchema`'s statement-splitter
handles the `ALTER TABLE` line correctly (it should — same semicolon-delimited pattern as
every other statement).

- [ ] **Step 4: Run to verify it passes**

Run: `ctest --test-dir build --output-on-failure -R test_worker`
Expected: PASS (including the new case) if Postgres is up.

- [ ] **Step 5: Commit**

```bash
git add db/schema.sql cpp/src/worker.cpp cpp/tests/test_worker.cpp
git commit -m "feat(cpp): flag insufficient-history customers per-row instead of failing the job"
```

---

### Task 11: End-to-end integration test

**Files:**
- Create: `cpp/tests/test_integration_upload_to_results.cpp`
- Modify: `cpp/CMakeLists.txt`

**Interfaces:**
- Produces: one test that exercises the real path spec §7 names explicitly: "an end-to-end
  test that uploads a known small cohort through the real API → worker → results path and
  checks the response shape and a few known forecast values." Everything before this task
  tested layers in isolation (worker logic directly, each endpoint alone); this is the only
  test in the whole plan that runs the actual `api_server` HTTP flow followed by actually
  invoking `ProcessOneJob` the way `worker_main`'s loop would (calling it directly after
  dequeuing, rather than spawning a second process — spawning `worker_main` as a real
  subprocess is possible but adds process-lifecycle complexity for marginal extra coverage;
  note this as a documented simplification, not a gap to silently accept).

- [ ] **Step 1: Write the test**

```cpp
// cpp/tests/test_integration_upload_to_results.cpp
#include <catch2/catch_test_macros.hpp>
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"
#include "pareto_nbd/worker.hpp"

TEST_CASE("Full loop: upload -> worker processes -> results are queryable", "[integration]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!db || !redis) { SKIP("Postgres/Redis not reachable"); }

    // ... start api_server on a background thread (Task 1's pattern) ...
    auto client = drogon::HttpClient::newHttpClient("http://127.0.0.1:18081");

    auto req = drogon::HttpRequest::newHttpRequest();
    req->setMethod(drogon::Post);
    req->setPath("/uploads");
    req->setBody("customer_id,transaction_date,amount\n"
                 "A,2024-01-01,10.0\nA,2024-01-08,5.0\nA,2024-01-22,8.0\n"
                 "B,2024-01-01,3.0\n");
    auto [r1, resp1] = client->sendRequest(req, 5.0);
    REQUIRE(resp1->getStatusCode() == drogon::k200OK);
    std::string job_id = nlohmann::json::parse(resp1->getBody())["job_id"].get<std::string>();

    // Simulate the worker: dequeue the job it was pushed onto, process it directly (see this
    // task's Interfaces note on why a real subprocess isn't spawned here).
    pareto_nbd::LocalDiskStorage storage("./data/uploads");
    auto dequeued = pareto_nbd::DequeueJob(redis, 5);
    REQUIRE(dequeued.has_value());
    REQUIRE(*dequeued == job_id);
    pareto_nbd::ProcessOneJob(*dequeued, db, storage);

    auto req2 = drogon::HttpRequest::newHttpRequest();
    req2->setPath("/jobs/" + job_id);
    auto [r2, resp2] = client->sendRequest(req2, 5.0);
    REQUIRE(nlohmann::json::parse(resp2->getBody())["status"] == "done");

    auto req3 = drogon::HttpRequest::newHttpRequest();
    req3->setPath("/jobs/" + job_id + "/results");
    auto [r3, resp3] = client->sendRequest(req3, 5.0);
    auto results = nlohmann::json::parse(resp3->getBody());
    REQUIRE(results["total"] == 2);  // customers A and B

    // ... shut down ...
}
```

- [ ] **Step 2: Run**

Run: `cmake --build build && ctest --test-dir build --output-on-failure -R integration`
Expected: PASS if Postgres+Redis are up; SKIP otherwise. If it fails for a reason unrelated to
Postgres/Redis reachability, that's a real integration bug — do not weaken the test to make it
pass, fix the underlying issue (most likely candidates: a race between the upload response and
the Redis push being visible, or a stale `db`/`redis` global pointer if Task 1–9's globals in
`api_main.cpp` weren't structured for reuse across the test binary vs. the real server binary —
resolve by refactoring shared setup into a small `BuildApp(db, redis, storage)` function both
`api_main.cpp` and the test call, if this bites).

- [ ] **Step 3: Commit**

```bash
git add cpp/tests/test_integration_upload_to_results.cpp cpp/CMakeLists.txt
git commit -m "test(cpp): end-to-end upload -> worker -> results integration test"
```

---

## Definition of done

`ctest --test-dir cpp/build` passes every test from Phases 1–3 plus this plan's new suites,
either genuinely passing (with Docker Compose's Postgres+Redis running) or cleanly SKIPping
(without them) — never erroring. `api_server` and `worker` both build and, run together against
a live `docker compose up -d`, support the full loop: `POST /uploads` a CSV, `GET /jobs/{id}`
shows `queued` → (worker picks it up) → `done`, `GET /jobs/{id}/results` and
`GET /jobs/{id}/export.csv` return real per-customer forecasts. This closes Phase 4 of the
spec. Phase 5 (the SvelteKit frontend) is the next plan; it depends only on these four HTTP
endpoints existing with this JSON/CSV shape, not on anything internal to how they're
implemented.
