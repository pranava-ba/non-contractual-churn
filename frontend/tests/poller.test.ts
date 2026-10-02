import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../src/lib/api';
import { pollJob } from '../src/lib/poller';
import type { JobInfo } from '../src/lib/types';

const job = (status: JobInfo['status'], error_reason: string | null = null): JobInfo => ({
  id: 'j',
  status,
  error_reason
});

describe('pollJob', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('polls until the job is done, reporting each update, with growing delays', async () => {
    const getJob = vi
      .fn()
      .mockResolvedValueOnce(job('queued'))
      .mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(job('done'));
    const seen: string[] = [];
    const p = pollJob('j', { getJob, onUpdate: (j) => seen.push(j.status), initialMs: 100, maxMs: 1000 });

    await vi.advanceTimersByTimeAsync(0); // first poll is immediate
    expect(getJob).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(100); // 100 ms
    expect(getJob).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(150); // 100 * 1.5
    expect(await p).toEqual(job('done'));
    expect(seen).toEqual(['queued', 'running', 'done']);
  });

  it('resolves on failed as a terminal state', async () => {
    const getJob = vi.fn().mockResolvedValue(job('failed', 'degenerate cohort'));
    expect(await pollJob('j', { getJob })).toEqual(job('failed', 'degenerate cohort'));
  });

  it('tolerates transient errors but gives up after maxErrors', async () => {
    const getJob = vi.fn().mockRejectedValue(new ApiError(0, 'Could not reach the server'));
    const p = pollJob('j', { getJob, maxErrors: 3, initialMs: 10 });
    const assertion = expect(p).rejects.toMatchObject({ status: 0 });
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
    expect(getJob).toHaveBeenCalledTimes(3);
  });

  it('recovers when a transient error is followed by success', async () => {
    const getJob = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(502, 'API unreachable'))
      .mockResolvedValueOnce(job('done'));
    const p = pollJob('j', { getJob, initialMs: 10 });
    await vi.advanceTimersByTimeAsync(50);
    expect(await p).toEqual(job('done'));
  });

  it('rejects immediately on a 404', async () => {
    const getJob = vi.fn().mockRejectedValue(new ApiError(404, 'job not found'));
    await expect(pollJob('j', { getJob })).rejects.toMatchObject({ status: 404 });
    expect(getJob).toHaveBeenCalledTimes(1);
  });

  it('stops when aborted', async () => {
    const ctl = new AbortController();
    const getJob = vi.fn().mockResolvedValue(job('running'));
    const p = pollJob('j', { getJob, signal: ctl.signal, initialMs: 100 });
    const assertion = expect(p).rejects.toMatchObject({ name: 'AbortError' });
    await vi.advanceTimersByTimeAsync(0);
    ctl.abort();
    await vi.advanceTimersByTimeAsync(500);
    await assertion;
  });
});
