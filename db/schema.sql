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
