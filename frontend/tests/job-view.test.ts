import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getJob = vi.fn();
const getSummary = vi.fn((..._args: unknown[]) => new Promise(() => {}));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return {
    ...actual,
    api: {
      getJob: (...a: unknown[]) => getJob(...a),
      refitJob: vi.fn(),
      getSummary: (...a: unknown[]) => getSummary(...a)
    }
  };
});

import JobView from '../src/lib/components/JobView.svelte';

const job = (id: string, over = {}) => ({
  id,
  status: 'done',
  error_reason: null,
  fit_mode: 'auto',
  fit_method: 'amortized',
  fit_note: null,
  source_job_id: null,
  ...over
});

describe('JobView', () => {
  beforeEach(() => {
    getJob.mockReset();
  });

  it('switches to the new job when the id prop changes (refit navigation reuses the component)', async () => {
    getJob.mockImplementation(async (id: string) =>
      id === 'job-1' ? job('job-1') : job('job-2', { fit_method: 'mcmc' })
    );
    const { rerender } = render(JobView, { id: 'job-1' });
    expect(await screen.findByText(/fast estimator/i)).toBeInTheDocument();

    await rerender({ id: 'job-2' });

    await waitFor(() => expect(getJob).toHaveBeenCalledWith('job-2'));
    expect(await screen.findByText(/high-precision \(mcmc\)/i)).toBeInTheDocument();
    expect(screen.queryByText(/fast estimator/i)).toBeNull();
  });

  it('renders the Starting label with a proper ellipsis while a refit is in flight', async () => {
    getJob.mockResolvedValue(job('job-1'));
    render(JobView, { id: 'job-1' });
    expect(await screen.findByRole('button', { name: /refit with high-precision/i })).toBeInTheDocument();
  });
});
