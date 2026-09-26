# Design: CLV/Churn Forecasting SaaS App

**Date:** 2026-09-26
**Status:** Draft — pending review

## 1. Purpose

Turn the Pareto/NBD extension research codebase (calibrated BTYD forecasting,
probabilistic CLV, conformal calibration, amortized neural estimation) into a
customer-facing product: a business uploads a raw transaction log and gets
back calibrated, per-customer purchase and CLV forecasts.

This is the MVP slice only. Auth, billing, and multi-tenancy are explicitly
out of scope and will be their own follow-on sub-project once this loop
works end-to-end for a single tenant.

## 2. Users & scope

- **User**: an external business (SaaS customer), not the research team.
- **Input**: a raw transaction log as CSV (`customer_id, transaction_date,
  [amount]` — no pre-aggregation required from the customer).
- **Output**: an interactive dashboard (cohort-level charts + per-customer
  table) and a downloadable CSV/Excel export of per-customer forecasts. No
  API access in this phase.
- **Scale**: customer transaction logs can be large (hundreds of thousands+
  rows); result turnaround needs to be fast, not "come back in an hour."

## 3. Architecture

```
Customer → SvelteKit frontend → Drogon HTTP API → Redis job queue → C++ worker(s)
                                                                        │
                                                          ┌─────────────┼──────────────┐
                                                    Arrow CSV      ONNX Runtime   Postgres +
                                                    ingestion &    (amortized     MinIO (blob
                                                    RFM features   net inference) storage)
```

Four services: SvelteKit frontend, Drogon API/gateway, a pool of C++ workers
that do the actual estimation, and storage (Postgres for job/result
metadata, MinIO for raw CSV uploads and generated exports). Redis holds the
job queue and job-status cache between the API and workers.

## 4. Components

### 4.1 Frontend — SvelteKit
- **Upload page**: drag-drop CSV, client-side header/type validation before
  the file is sent.
- **Job status view**: polls `GET /jobs/{id}` until the job completes.
- **Dashboard**: cohort-level charts (forecast distribution, PIT/calibration
  diagnostic, P(active) histogram) via **ECharts** (through a Svelte
  wrapper), plus a sortable/filterable per-customer table (expected
  purchases, P(alive), CLV point + interval).
- **Export**: button triggers `GET /jobs/{id}/export.csv`.

### 4.2 API — Drogon (C++20)
Endpoints:
- `POST /uploads` — accepts CSV, stores it in MinIO, validates headers,
  enqueues a job in Redis, returns a job id.
- `GET /jobs/{id}` — job status (`queued`, `running`, `done`, `failed`).
- `GET /jobs/{id}/results` — JSON results once done (cohort summary +
  per-customer records, paginated).
- `GET /jobs/{id}/export.csv` — generates/streams the CSV export.

Drogon's built-in async Postgres driver and JSON handling (via
nlohmann/json) are used directly; no separate ORM layer.

### 4.3 Worker — C++
Picks jobs off the Redis queue and runs the estimation pipeline:
1. **Ingestion**: Apache Arrow C++ reads the uploaded CSV and computes
   per-customer RFM features (frequency, recency, T, monetary value) via
   Arrow's group-by/aggregate compute functions. This is the stage that
   has to handle scale, hence Arrow rather than a hand-rolled parser.
2. **Fast-path estimation**: the existing amortized neural Pareto/NBD
   estimator ([src/amortized.py](../../../src/amortized.py)) continues to be
   trained and validated in Python — that is a research artifact and stays
   there. Its trained weights are exported to **ONNX**, and the C++ worker
   runs inference via the ONNX Runtime C++ API.
3. **CLV combination**: Gamma-Gamma spend model logic
   ([src/clv.py](../../../src/clv.py)) is ported to C++ (closed-form
   arithmetic, not iterative).
4. **Interval calibration**: conformal calibration logic
   ([src/conformal.py](../../../src/conformal.py)) is ported to C++
   (order-statistic based, not iterative).
5. Results are written to Postgres; the export CSV is generated on demand
   or cached in MinIO.

**Explicitly deferred**: the Abe (2009) MCMC Gibbs sampler
([src/estimate.py](../../../src/estimate.py)) is *not* ported to C++ for
this phase. It is iterative, stateful, and is the calibration ground truth
behind the paper's own results — the highest-risk place to introduce a
silent numerical bug in a from-scratch port. Any "high-precision refit"
option in the product calls out to the existing Python implementation as a
subprocess/microservice for now; a native C++ MCMC port is a later,
separate sub-project once the fast path has shipped and been validated
against real usage.

### 4.4 Storage
- **PostgreSQL**: job metadata, per-customer forecast results (JSONB for
  flexible per-model fields).
- **MinIO** (S3-compatible): raw uploaded CSVs, generated export files.
- **Redis**: job queue + job-status cache between API and workers.

#### 4.4.1 Database schema (forward-compatible with the prescriptive/uplift module)

Auth and multi-tenancy are out of scope for this phase (§10), but two schema
decisions now avoid a rework when they — and the prescriptive/uplift layer
discussed in §11 — get built:

1. Every table carries a `business_id` FK from day one, even though there is
   only ever one row in `businesses` until multi-tenancy ships. Retrofitting
   a tenant column onto populated tables later is far more disruptive than
   including an unused one now.
2. **Customers are first-class, persistent entities**, not rows scoped to a
   single upload. A business re-uploads its transaction log over time (new
   `jobs`), and each upload should update the *same* customer record rather
   than creating a disconnected copy — that's what lets `forecast_results`
   accumulate into a per-customer history, and it's the exact join key a
   future `campaign_assignments`/`campaign_outcomes` table needs to line up
   "what we predicted for this customer" with "what campaign they got and
   what happened" (the (X, T, Y) shape `estimate_uplift` in
   [src/prescriptive.py](../../../src/prescriptive.py) already expects).

```sql
-- Present now, populated with a single row until multi-tenancy ships.
CREATE TABLE businesses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id  UUID NOT NULL REFERENCES businesses(id),
    status       TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
    upload_path  TEXT NOT NULL,   -- MinIO object key for the raw CSV
    error_reason TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- One row per real-world customer, persistent across re-uploads.
CREATE TABLE customers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id         UUID NOT NULL REFERENCES businesses(id),
    external_customer_id TEXT NOT NULL,  -- the customer_id from the uploaded CSV
    first_seen_job_id   UUID NOT NULL REFERENCES jobs(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (business_id, external_customer_id)
);

-- One row per (customer, job): a time series of forecasts as new uploads arrive.
CREATE TABLE forecast_results (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id         UUID NOT NULL REFERENCES jobs(id),
    customer_id    UUID NOT NULL REFERENCES customers(id),
    expected_purchases DOUBLE PRECISION NOT NULL,
    p_alive        DOUBLE PRECISION NOT NULL,
    clv_point      DOUBLE PRECISION NOT NULL,
    clv_lower      DOUBLE PRECISION NOT NULL,
    clv_upper      DOUBLE PRECISION NOT NULL,
    model_params   JSONB NOT NULL,   -- e.g. {r, alpha, s, beta} for this fit
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, customer_id)
);
```

**Not built in this phase** — shown only to confirm the tables above join to
it without modification, i.e. adding it later is additive, not a migration
of existing tables:

```sql
CREATE TABLE campaigns (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id  UUID NOT NULL REFERENCES businesses(id),
    name         TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL,
    ended_at     TIMESTAMPTZ
);

-- The "T" in (X, T, Y): who got treated.
CREATE TABLE campaign_assignments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id  UUID NOT NULL REFERENCES campaigns(id),
    customer_id  UUID NOT NULL REFERENCES customers(id),
    treated      BOOLEAN NOT NULL,
    assigned_at  TIMESTAMPTZ NOT NULL,
    UNIQUE (campaign_id, customer_id)
);

-- The "Y" in (X, T, Y): what happened to them afterward.
CREATE TABLE campaign_outcomes (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_assignment_id UUID NOT NULL REFERENCES campaign_assignments(id),
    outcome_metric         TEXT NOT NULL,   -- e.g. 'retained', 'clv_90d'
    outcome_value          DOUBLE PRECISION NOT NULL,
    observed_at            TIMESTAMPTZ NOT NULL
);
```

The "X" (features) side of the uplift estimator's (X, T, Y) contract is just
the `forecast_results` row for that customer as of the campaign's
`started_at` — no new feature-storage table needed.

## 5. Correctness strategy

Every computation ported from the validated Python implementation to C++
(RFM feature extraction, Gamma-Gamma CLV, conformal calibration, ONNX
inference vs. the original PyTorch/numpy model) gets a **golden-file test**:
run the existing Python code on the existing benchmark cohorts (CDNow,
Online Retail II, etc. — already used in [src/datasets.py](../../../src/datasets.py)),
snapshot the outputs, and assert the C++ implementation matches within
tolerance. This is non-negotiable — the forecasts *are* the product, and
this repo's whole premise is that calibration claims must be checked, not
assumed.

## 6. Error handling

- **Upload validation**: malformed CSV, missing required columns, or empty
  file is rejected at `POST /uploads` with a specific error before a job is
  ever enqueued.
- **Job failure**: worker-side exceptions (e.g. degenerate cohort, all-zero
  frequencies) mark the job `failed` with a user-facing reason string;
  raw stack traces are not surfaced to the frontend.
- **Partial data**: customers with insufficient history for a given model
  (e.g. single-transaction customers for Pareto/GGG regularity) are flagged
  per-row in the results rather than failing the whole job.

## 7. Testing

- **C++**: Catch2 unit tests for each ported computation, plus the
  golden-file cross-checks against Python described in §5.
- **Python side**: existing `pytest` suite in `tests/` continues to guard
  the research code (amortized net training, MCMC, scoring) unchanged.
- **Integration**: an end-to-end test that uploads a known small cohort
  through the real API → worker → results path and checks the response
  shape and a few known forecast values.

## 8. Stack (locked in)

| Layer | Choice |
|---|---|
| Frontend | SvelteKit |
| Charts | ECharts (via Svelte wrapper) |
| C++ HTTP framework | Drogon (C++20) |
| Job queue | Redis |
| CSV ingestion / features | Apache Arrow C++ |
| Model inference | ONNX Runtime C++ API |
| Database | PostgreSQL |
| Blob storage | MinIO (S3 API) |
| Build / deps | CMake + vcpkg |
| JSON | nlohmann/json |
| C++ testing | Catch2 |
| Deployment (MVP) | Docker Compose |

## 9. Phased build order

1. Export the amortized model to ONNX; stand up a C++ worker that loads it
   and reproduces the Python inference outputs on a test cohort
   (golden-file check).
2. Port Gamma-Gamma CLV + conformal calibration to C++, same golden-file
   validation.
3. Arrow-based CSV ingestion + RFM feature extraction, validated against
   the existing Python feature computation.
4. Drogon API: upload → validate → enqueue → worker picks up → writes
   results to Postgres.
5. SvelteKit frontend: upload flow, dashboard, export — wired to the API.
6. (Stretch, non-blocking) High-precision MCMC path as an optional
   Python-subprocess call.

## 10. Out of scope (this phase)

- Authentication, multi-tenancy, billing.
- API access for customers (JSON endpoints beyond what the frontend uses).
- Native C++ MCMC.
- Data warehouse/DB connectors (Postgres, Snowflake, Shopify, etc.) — CSV
  upload only.
- The prescriptive/uplift layer (§11) — not built, but the schema in §4.4.1
  is deliberately shaped so it can be added without migrating existing
  tables.

## 11. Future extension: prescriptive/uplift layer

A natural second major phase of the *product* (distinct from the phased
build order in §9, which only covers this descriptive MVP): once a business
has forecast data flowing and starts asking "who should I actually spend
retention budget on," the causal uplift research already validated in
[src/prescriptive.py](../../../src/prescriptive.py) and written up in
[docs/uplift.md](../../../docs/uplift.md) (referred to elsewhere as "Gear 2")
answers that — the conditional treatment effect (CATE) of a retention
action per customer, as opposed to their raw churn risk.

This is deliberately not part of the current build for two reasons: it
needs a different input (campaign treatment/outcome history, not just a
transaction log) that a new customer won't have on day one, and the
underlying research is still at Stage A/B validation (simulated + two real
datasets), not yet its own published result. §4.4.1's `campaigns`,
`campaign_assignments`, and `campaign_outcomes` tables exist in this spec
only to confirm that adding this layer later is additive to the schema, not
a rework of it.
