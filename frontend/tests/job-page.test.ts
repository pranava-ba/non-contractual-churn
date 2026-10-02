import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getJob = vi.fn();
const refitJob = vi.fn();
const goto = vi.fn();
vi.mock('$app/navigation', () => ({ goto: (...a: unknown[]) => goto(...a) }));
const getSummary = vi.fn((..._args: unknown[]) => new Promise(() => {})); // keep the dashboard in its loading state
vi.mock('$app/state', () => ({ page: { params: { id: 'job-1' } } }));
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return {
    ...actual,
    api: {
      getJob: (...a: unknown[]) => getJob(...a),
      refitJob: (...a: unknown[]) => refitJob(...a),
      getSummary: (...a: unknown[]) => getSummary(...a)
    }
  };
});

import { ApiError } from '../src/lib/api';
import Page from '../src/routes/jobs/[id]/+page.svelte';

describe('job page', () => {
  beforeEach(() => {
    getJob.mockReset(); // braces matter: a returned function would be run by Vitest as a teardown hook
    refitJob.mockReset();
    goto.mockReset();
  });

  it('shows progress then the done state', async () => {
    getJob
      .mockResolvedValueOnce({ id: 'job-1', status: 'running', error_reason: null })
      .mockResolvedValue({ id: 'job-1', status: 'done', error_reason: null });
    render(Page);
    expect(await screen.findByText(/running/i)).toBeInTheDocument();
    expect(await screen.findByTestId('job-done', {}, { timeout: 4000 })).toBeInTheDocument();
    // the dashboard is mounted for a done job (its summary request is the proof)
    expect(getSummary).toHaveBeenCalledWith('job-1');
  });

  it('shows the failure reason', async () => {
    getJob.mockResolvedValue({ id: 'job-1', status: 'failed', error_reason: 'all customers have zero frequency' });
    render(Page);
    expect(await screen.findByText(/all customers have zero frequency/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /upload another/i })).toBeInTheDocument();
  });

  it('shows a not-found message for an unknown job', async () => {
    getJob.mockRejectedValue(new ApiError(404, 'job not found'));
    render(Page);
    await waitFor(() => expect(screen.getByText(/couldn't find that job/i)).toBeInTheDocument());
  });
  const done = (over = {}) => ({
    id: 'job-1',
    status: 'done',
    error_reason: null,
    fit_mode: 'auto',
    fit_method: 'amortized',
    fit_note: null,
    source_job_id: null,
    ...over
  });

  it('offers a high-precision refit on a fast-fitted job and navigates to the new job', async () => {
    getJob.mockResolvedValue(done());
    refitJob.mockResolvedValue({ job_id: 'job-9' });
    render(Page);
    await fireEvent.click(await screen.findByRole('button', { name: /high-precision/i }));
    expect(refitJob).toHaveBeenCalledWith('job-1');
    await waitFor(() => expect(goto).toHaveBeenCalledWith('/jobs/job-9'));
  });

  it('shows the method used and hides the refit button for an MCMC fit', async () => {
    getJob.mockResolvedValue(done({ fit_method: 'mcmc' }));
    render(Page);
    expect(await screen.findByText(/high-precision \(mcmc\)/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /high-precision/i })).toBeNull();
  });

  it('shows the fallback note when the refit could not run', async () => {
    getJob.mockResolvedValue(
      done({ fit_note: 'High-precision refit unavailable (timed out after 600 s) - used the fast estimator instead.' })
    );
    render(Page);
    expect(await screen.findByText(/timed out after 600 s/i)).toBeInTheDocument();
  });
});
