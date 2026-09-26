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
