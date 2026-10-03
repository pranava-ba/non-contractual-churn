// End-to-end check through the frontend proxy against a LIVE stack (not a unit test: it needs
// docker compose, api_server and worker running). Usage: node scripts/smoke.mjs [baseUrl] [csv]
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const base = process.argv[2] ?? 'http://localhost:5173';
const csvPath = process.argv[3] ?? fileURLToPath(new URL('../../models/ingest_sample.csv', import.meta.url));

// Throw (rather than process.exit) so open fetch connections close cleanly -- a hard exit with
// live undici sockets trips a libuv assertion on Windows.
const fail = (msg) => {
  throw new Error(msg);
};
const ok = (msg) => console.log(`ok   ${msg}`);

async function get(path) {
  const res = await fetch(base + path);
  if (!res.ok) fail(`${path} -> HTTP ${res.status}`);
  return res;
}

async function waitDone(job_id, seconds = 60) {
  let job = { status: 'queued' };
  for (let i = 0; i < seconds && job.status !== 'done' && job.status !== 'failed'; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    job = await (await get(`/api/jobs/${job_id}`)).json();
  }
  if (job.status !== 'done') fail(`job ended as '${job.status}' (is the worker running?)`);
  return job;
}

async function upload(csv, mode) {
  const q = mode ? `?fit_mode=${mode}` : '';
  const up = await fetch(`${base}/api/uploads${q}`, { method: 'POST', headers: { 'content-type': 'text/csv' }, body: csv });
  if (!up.ok) fail(`upload -> HTTP ${up.status} ${await up.text()}`);
  return (await up.json()).job_id;
}

async function main() {
  const csv = await readFile(csvPath);
  const job_id = await upload(csv, 'fast');
  ok(`uploaded (fit_mode=fast), job ${job_id}`);
  const fast = await waitDone(job_id);
  if (fast.fit_method !== 'amortized') fail(`fast job used '${fast.fit_method}', expected amortized`);
  ok('job done, fitted with the amortized estimator');

  // High-precision refit of the same upload (MCMC subprocess); allow a few minutes.
  const t0 = Date.now();
  const refit = await fetch(`${base}/api/jobs/${job_id}/refit`, { method: 'POST' });
  if (!refit.ok) fail(`refit -> HTTP ${refit.status} ${await refit.text()}`);
  const refit_id = (await refit.json()).job_id;
  const mc = await waitDone(refit_id, 600);
  if (mc.source_job_id !== job_id) fail(`refit source_job_id is ${mc.source_job_id}`);
  if (mc.fit_method !== 'mcmc') fail(`refit used '${mc.fit_method}' (${mc.fit_note ?? 'no note'}), expected mcmc`);
  ok(`refit done with MCMC in ${((Date.now() - t0) / 1000).toFixed(1)} s`);

  // fit_mode=auto picks MCMC for a cohort inside the small-cohort window, else the fast path.
  const auto_id = await upload(csv);
  const auto = await waitDone(auto_id, 600);
  ok(`auto upload used '${auto.fit_method}'`);

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

  const badMode = await fetch(`${base}/api/uploads?fit_mode=bogus`, { method: 'POST', headers: { 'content-type': 'text/csv' }, body: csv });
  if (badMode.status !== 400) fail(`bogus fit_mode should be 400, got ${badMode.status}`);
  ok('unknown fit_mode rejected with 400');

  const bad = await fetch(`${base}/api/uploads`, { method: 'POST', headers: { 'content-type': 'text/csv' }, body: 'a,b\n1,2\n' });
  if (bad.status !== 400) fail(`bad upload should be 400, got ${bad.status}`);
  ok('bad CSV rejected with 400');
  console.log('SMOKE PASSED');
}

main().catch((e) => {
  console.error(`FAIL ${e.message}`);
  process.exitCode = 1;
});
