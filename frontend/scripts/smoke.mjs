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

async function main() {
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
}

main().catch((e) => {
  console.error(`FAIL ${e.message}`);
  process.exitCode = 1;
});
