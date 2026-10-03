import { ApiError } from './api';
import type { JobInfo } from './types';

export interface PollOptions {
  getJob: (id: string) => Promise<JobInfo>;
  onUpdate?: (job: JobInfo) => void;
  signal?: AbortSignal;
  initialMs?: number;
  maxMs?: number;
  maxErrors?: number;
}

const abortError = () => Object.assign(new Error('Polling aborted'), { name: 'AbortError' });

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(abortError());
    const onAbort = () => {
      clearTimeout(t);
      reject(abortError());
    };
    const t = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/** Resolves with the first job in a terminal state ('done' | 'failed'). Rejects with the last
 *  error after maxErrors consecutive failures, or with an AbortError-named Error on abort. The
 *  delay grows 1.5x per poll up to maxMs. A 400/404 ApiError is not transient and rejects at once. */
export async function pollJob(id: string, opts: PollOptions): Promise<JobInfo> {
  const { getJob, onUpdate, signal, initialMs = 1000, maxMs = 5000, maxErrors = 5 } = opts;
  let delay = initialMs;
  let errors = 0;
  for (;;) {
    if (signal?.aborted) throw abortError();
    try {
      const job = await getJob(id);
      errors = 0;
      onUpdate?.(job);
      if (job.status === 'done' || job.status === 'failed') return job;
    } catch (e) {
      // 400/404 mean the id itself is wrong: retrying cannot help.
      if (e instanceof ApiError && (e.status === 404 || e.status === 400)) throw e;
      if (++errors >= maxErrors) throw e;
    }
    await sleep(delay, signal);
    delay = Math.min(Math.round(delay * 1.5), maxMs);
  }
}
