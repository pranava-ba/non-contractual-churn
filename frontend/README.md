# CLV Forecasts — frontend

SvelteKit app for the CLV/churn forecasting service: upload a transaction-log CSV, watch the job,
explore the cohort dashboard and per-customer table, export the forecasts.

## Run it (development)

From the repo root, start the backing services and API:

    docker compose up -d                       # Postgres + Redis
    cpp/build/api_server                       # Drogon API on :8080
    cpp/build/worker                           # job worker (run from the same directory as api_server —
                                               #  both read uploads from ./data/uploads)

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
would reject real uploads (the API accepts up to 100 MB). Note that `npm start` uses POSIX
`VAR=value` syntax; on Windows set `BODY_SIZE_LIMIT=100M` in the environment and run `node build`.

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
