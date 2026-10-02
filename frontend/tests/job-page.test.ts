import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getJob = vi.fn();
vi.mock('$app/state', () => ({ page: { params: { id: 'job-1' } } }));
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return {
    ...actual,
    api: {
      getJob: (...a: unknown[]) => getJob(...a),
      getSummary: () => new Promise(() => {}) // keep the dashboard in its loading state
    }
  };
});

import { ApiError } from '../src/lib/api';
import Page from '../src/routes/jobs/[id]/+page.svelte';

describe('job page', () => {
  beforeEach(() => {
    getJob.mockReset(); // braces matter: a returned function would be run by Vitest as a teardown hook
  });

  it('shows progress then the done state', async () => {
    getJob
      .mockResolvedValueOnce({ id: 'job-1', status: 'running', error_reason: null })
      .mockResolvedValue({ id: 'job-1', status: 'done', error_reason: null });
    render(Page);
    expect(await screen.findByText(/running/i)).toBeInTheDocument();
    expect(await screen.findByTestId('job-done', {}, { timeout: 4000 })).toBeInTheDocument();
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
});
