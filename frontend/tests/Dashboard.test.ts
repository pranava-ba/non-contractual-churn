import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getSummary = vi.fn();
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return {
    ...actual,
    api: {
      getSummary: (...a: unknown[]) => getSummary(...a),
      getResults: () => new Promise(() => {}) // keep the table in its loading state
    }
  };
});
vi.mock('../src/lib/components/Chart.svelte', async () => ({
  default: (await import('./stubs/ChartStub.svelte')).default
}));

import { ApiError } from '../src/lib/api';
import Dashboard from '../src/lib/components/Dashboard.svelte';

const hist = (n: number) => ({ edges: Array.from({ length: n + 1 }, (_, i) => i), counts: Array(n).fill(1) });
const summary = {
  job_id: 'j',
  n_customers: 3,
  quality_counts: { ok: 3 },
  mean_p_alive: 0.5,
  total_expected_purchases: 6,
  total_clv: 100,
  has_clv_interval: false,
  histograms: { p_alive: hist(10), expected_purchases: hist(20), clv_point: hist(20) }
};

describe('Dashboard', () => {
  beforeEach(() => {
    getSummary.mockReset();
  });

  it('loads the summary and renders the three charts', async () => {
    getSummary.mockResolvedValue(summary);
    render(Dashboard, { props: { jobId: 'j' } });
    expect(await screen.findByLabelText('Distribution of P(alive)')).toBeInTheDocument();
    expect(screen.getByLabelText('Distribution of expected purchases')).toBeInTheDocument();
    expect(screen.getByLabelText('Distribution of customer lifetime value')).toBeInTheDocument();
    expect(getSummary).toHaveBeenCalledWith('j');
  });

  it('hides the CLV chart when no customer has a valid CLV', async () => {
    getSummary.mockResolvedValue({ ...summary, quality_counts: { insufficient_history: 3 }, total_clv: 0 });
    render(Dashboard, { props: { jobId: 'j' } });
    await screen.findByLabelText('Distribution of P(alive)');
    expect(screen.queryByLabelText('Distribution of customer lifetime value')).not.toBeInTheDocument();
  });

  it('shows an error when the summary cannot be loaded', async () => {
    getSummary.mockRejectedValue(new ApiError(500, 'Request failed (HTTP 500)'));
    render(Dashboard, { props: { jobId: 'j' } });
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed (HTTP 500)');
  });
});
