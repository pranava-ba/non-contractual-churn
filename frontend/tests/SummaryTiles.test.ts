import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import SummaryTiles from '../src/lib/components/SummaryTiles.svelte';
import type { JobSummary } from '../src/lib/types';

const hist = { edges: [0, 1], counts: [0] };
const base: JobSummary = {
  job_id: 'j',
  n_customers: 1234,
  quality_counts: { ok: 1200, insufficient_history: 34 },
  mean_p_alive: 0.6234,
  total_expected_purchases: 4567.8,
  total_clv: 98765.4321,
  has_clv_interval: false,
  histograms: { p_alive: hist, expected_purchases: hist, clv_point: hist }
};

describe('SummaryTiles', () => {
  it('shows the headline numbers, formatted', () => {
    render(SummaryTiles, { props: { summary: base } });
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('62.3%')).toBeInTheDocument();
    expect(screen.getByText('98,765.43')).toBeInTheDocument();
  });

  it('summarises non-OK data quality', () => {
    render(SummaryTiles, { props: { summary: base } });
    expect(screen.getByText(/34 customers have limited data/i)).toBeInTheDocument();
  });

  it('omits the CLV tile when no customer has a CLV (no amount column)', () => {
    render(SummaryTiles, {
      props: { summary: { ...base, quality_counts: { insufficient_history: 1234 }, total_clv: 0 } }
    });
    expect(screen.queryByText(/total clv/i)).not.toBeInTheDocument();
  });
});
