import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ExportBar from '../src/lib/components/ExportBar.svelte';

describe('ExportBar', () => {
  it('links to the CSV export for the job', () => {
    render(ExportBar, { props: { jobId: 'abc', qualityCounts: { ok: 10 } } });
    const link = screen.getByRole('link', { name: /download csv/i });
    expect(link).toHaveAttribute('href', '/api/jobs/abc/export.csv');
    expect(link).toHaveAttribute('download', 'forecasts-abc.csv');
  });

  it('omits the data-quality explainer when every row is OK', () => {
    render(ExportBar, { props: { jobId: 'abc', qualityCounts: { ok: 10 } } });
    expect(screen.queryByText(/about data-quality flags/i)).not.toBeInTheDocument();
  });

  it('explains each non-OK flag present, with counts', () => {
    render(ExportBar, {
      props: { jobId: 'abc', qualityCounts: { ok: 8, insufficient_history: 1200, forecast_unavailable: 2 } }
    });
    expect(screen.getByText(/about data-quality flags/i)).toBeInTheDocument();
    expect(screen.getByText(/Low history — 1,200 customers/)).toBeInTheDocument();
    expect(screen.getByText(/No forecast — 2 customers/)).toBeInTheDocument();
    expect(screen.queryByText(/No CLV —/)).not.toBeInTheDocument();
  });
});
