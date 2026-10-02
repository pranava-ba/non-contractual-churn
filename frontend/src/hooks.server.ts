import type { Handle } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { proxyRequest } from '$lib/server/proxy';

// The Drogon API has no CORS support, so the browser only ever talks to this server's own
// origin under /api/*, and this hook forwards those requests to the real API.
export const handle: Handle = async ({ event, resolve }) => {
  if (event.url.pathname.startsWith('/api/')) {
    const base = env.API_BASE_URL ?? 'http://localhost:8080';
    return proxyRequest(event.request, event.url.pathname.slice('/api'.length), event.url.search, base);
  }
  return resolve(event);
};
