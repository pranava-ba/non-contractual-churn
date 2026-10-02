// Headers that describe the browser<->frontend hop, not the frontend<->API hop.
const DROP_REQUEST = new Set(['host', 'connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'content-length']);
// fetch() has already decoded the upstream body, so these would now be wrong.
const DROP_RESPONSE = new Set(['content-encoding', 'content-length', 'transfer-encoding', 'connection']);

export async function proxyRequest(
  request: Request,
  apiPath: string,
  search: string,
  base: string,
  fetchFn: typeof fetch = fetch
): Promise<Response> {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!DROP_REQUEST.has(key.toLowerCase())) headers.set(key, value);
  });

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  const init: RequestInit & { duplex?: 'half' } = {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    duplex: 'half' // required by Node's fetch when streaming a request body
  };

  let upstream: Response;
  try {
    upstream = await fetchFn(base + apiPath + search, init);
  } catch {
    return new Response(JSON.stringify({ error: 'API unreachable' }), {
      status: 502,
      headers: { 'content-type': 'application/json' }
    });
  }

  const out = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!DROP_RESPONSE.has(key.toLowerCase())) out.set(key, value);
  });
  return new Response(upstream.body, { status: upstream.status, headers: out });
}
