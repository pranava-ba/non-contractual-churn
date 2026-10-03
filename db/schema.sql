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
    data_quality        TEXT NOT NULL DEFAULT 'ok',
    UNIQUE (job_id, customer_id)
);

-- Idempotent for databases where forecast_results already existed before this column was
-- added (CREATE TABLE IF NOT EXISTS above is a no-op against an existing table, so new
-- columns must also be added here). Values: ok (normal forecast), insufficient_history
-- (x==0 repeat purchases -- forecast computed but low-confidence), forecast_unavailable
-- (closed-form math could not be evaluated for this customer -- see worker.cpp),
-- clv_unavailable (forecast is fine but the Gamma-Gamma CLV is undefined for this customer,
-- posterior shape at or below 1 -- clv columns hold 0.0 placeholders, see worker.cpp).
-- NOTE: avoid the semicolon character anywhere in this comment block, even spelled out or
-- quoted -- ApplySchema's statement splitter (db.cpp) naively splits the whole file on
-- that one character, with no awareness of comments or string literals.
ALTER TABLE forecast_results ADD COLUMN IF NOT EXISTS data_quality TEXT NOT NULL DEFAULT 'ok';

-- Seed the single-tenant bootstrap row (spec §4.4.1: "populated with a single row until
-- multi-tenancy ships"), with a fixed, well-known id so application code can hardcode it.
INSERT INTO businesses (id, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'default')
ON CONFLICT (id) DO NOTHING;

-- Fit selection. fit_mode is what the user asked for (auto, fast or mcmc). fit_method is what
-- the worker actually used (amortized or mcmc, NULL until the job finishes). fit_note explains
-- a fallback (for example the high-precision refit could not run). source_job_id links a refit
-- job to the job it re-fits. mcmc_draws_path is the storage key of the saved posterior draws.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fit_mode TEXT NOT NULL DEFAULT 'auto' CHECK (fit_mode IN ('auto','fast','mcmc'));
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fit_method TEXT CHECK (fit_method IN ('amortized','mcmc'));
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fit_note TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_job_id UUID REFERENCES jobs(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS mcmc_draws_path TEXT;
