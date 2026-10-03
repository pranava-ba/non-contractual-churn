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
    expect(url).toBe('/api/uploads?fit_mode=auto');
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('content-type')).toBe('text/csv');
    expect(init.body).toBe(file);
  });

  it('sends the chosen fit mode as a query parameter', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'job-1' }));
    await createApi(fetchFn).uploadCsv(new File(['x'], 'a.csv'), 'mcmc');
    expect((fetchFn.mock.calls[0] as unknown as [string])[0]).toBe('/api/uploads?fit_mode=mcmc');
  });

  it('refitJob POSTs to the refit endpoint', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'job-2' }));
    const out = await createApi(fetchFn).refitJob('job-1');
    expect(out).toEqual({ job_id: 'job-2' });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/jobs/job-1/refit');
    expect(init.method).toBe('POST');
  });

  it('surfaces the API error message for a 400 upload', async () => {
    const fetchFn = vi.fn(async () => json({ error: "missing required column 'customer_id'" }, 400));
    await expect(createApi(fetchFn).uploadCsv(new File(['x'], 'a.csv'))).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      message: "missing required column 'customer_id'"
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
    const fetchFn = vi.fn(async () => {
      throw new TypeError('fetch failed');
    });
    await expect(createApi(fetchFn).getJob('abc')).rejects.toMatchObject({
      status: 0,
      message: 'Could not reach the server'
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
    expect(url2.searchParams.get('q')).toBe('a&b'); // properly encoded, not split
  });

  it('gets the summary and builds the export URL', async () => {
    const fetchFn = vi.fn(async () => json({ job_id: 'j', n_customers: 3 }));
    await createApi(fetchFn).getSummary('j');
    expect((fetchFn.mock.calls[0] as unknown as [string])[0]).toBe('/api/jobs/j/summary');
    expect(exportUrl('j')).toBe('/api/jobs/j/export.csv');
  });
});
