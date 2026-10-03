import type { FitMode, JobInfo, JobSummary, ResultsPage, ResultsQuery } from './types';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.ok) return (await res.json()) as T;
  let message = `Request failed (HTTP ${res.status})`;
  try {
    const body = await res.json();
    if (body && typeof body.error === 'string') message = body.error;
  } catch {
    /* non-JSON error body: keep the generic message */
  }
  throw new ApiError(res.status, message);
}

export function createApi(fetchFn: typeof fetch = (...a) => fetch(...a)) {
  async function call<T>(url: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetchFn(url, init);
    } catch {
      throw new ApiError(0, 'Could not reach the server');
    }
    return parse<T>(res);
  }

  return {
    uploadCsv: (file: File, fitMode: FitMode = 'auto') =>
      call<{ job_id: string }>(`/api/uploads?fit_mode=${fitMode}`, {
        method: 'POST',
        headers: { 'content-type': 'text/csv' },
        body: file
      }),
    refitJob: (id: string) =>
      call<{ job_id: string }>(`/api/jobs/${encodeURIComponent(id)}/refit`, { method: 'POST' }),
    getJob: (id: string) => call<JobInfo>(`/api/jobs/${encodeURIComponent(id)}`),
    getResults: (id: string, q: ResultsQuery) => {
      const p = new URLSearchParams({
        page: String(q.page),
        page_size: String(q.pageSize),
        sort: q.sort,
        order: q.order
      });
      if (q.quality) p.set('quality', q.quality);
      if (q.q) p.set('q', q.q);
      return call<ResultsPage>(`/api/jobs/${encodeURIComponent(id)}/results?${p}`);
    },
    getSummary: (id: string) => call<JobSummary>(`/api/jobs/${encodeURIComponent(id)}/summary`)
  };
}

export const exportUrl = (id: string) => `/api/jobs/${encodeURIComponent(id)}/export.csv`;

export const api = createApi();
