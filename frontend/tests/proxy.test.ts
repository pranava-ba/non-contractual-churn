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
    expect(sent.has('host')).toBe(false); // hop-by-hop / origin-specific headers dropped
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
      new Request('http://app.test/api/jobs/1'),
      '/jobs/1',
      '',
      'http://api.test:8080',
      fetchFn
    );
    expect(res.status).toBe(502);
    expect((await res.json()).error).toMatch(/unreachable/i);
  });
});
