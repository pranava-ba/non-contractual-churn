import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const getResults = vi.fn();
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return { ...actual, api: { getResults: (...a: unknown[]) => getResults(...a) } };
});

import CustomerTable from '../src/lib/components/CustomerTable.svelte';
import type { CustomerRow, DataQuality, ResultsPage } from '../src/lib/types';

const row = (o: Partial<CustomerRow> = {}): CustomerRow => ({
  customer_id: 'C1',
  expected_purchases: 2.345,
  p_alive: 0.8,
  clv_point: 120.5,
  clv_lower: 120.5,
  clv_upper: 120.5,
  data_quality: 'ok',
  ...o
});
const page = (customers: CustomerRow[], total = customers.length, p = 1): ResultsPage => ({
  job_id: 'j',
  page: p,
  page_size: 50,
  total,
  customers
});
const props = { jobId: 'j', hasClvInterval: false, qualities: ['ok', 'insufficient_history'] as DataQuality[] };

describe('CustomerTable', () => {
  beforeEach(() => {
    getResults.mockReset();
    getResults.mockResolvedValue(page([row()]));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('loads the first page with default sort and renders rows', async () => {
    render(CustomerTable, { props });
    expect(await screen.findByText('C1')).toBeInTheDocument();
    expect(getResults).toHaveBeenCalledWith('j', {
      page: 1,
      pageSize: 50,
      sort: 'customer_id',
      order: 'asc',
      quality: '',
      q: ''
    });
    expect(screen.getByText('80.0%')).toBeInTheDocument();
    expect(screen.getByText('120.50')).toBeInTheDocument();
  });

  it('clicking a header sorts by it, then toggles direction', async () => {
    render(CustomerTable, { props });
    await screen.findByText('C1');
    const header = screen.getByRole('columnheader', { name: /clv/i });
    await fireEvent.click(within(header).getByRole('button'));
    await waitFor(() =>
      expect(getResults).toHaveBeenLastCalledWith(
        'j',
        expect.objectContaining({ sort: 'clv_point', order: 'asc', page: 1 })
      )
    );
    expect(header).toHaveAttribute('aria-sort', 'ascending');
    await fireEvent.click(within(header).getByRole('button'));
    await waitFor(() =>
      expect(getResults).toHaveBeenLastCalledWith('j', expect.objectContaining({ sort: 'clv_point', order: 'desc' }))
    );
    expect(header).toHaveAttribute('aria-sort', 'descending');
  });

  it('filters by quality and resets to page 1', async () => {
    render(CustomerTable, { props });
    await screen.findByText('C1');
    await fireEvent.change(screen.getByLabelText(/data quality/i), { target: { value: 'insufficient_history' } });
    await waitFor(() =>
      expect(getResults).toHaveBeenLastCalledWith(
        'j',
        expect.objectContaining({ quality: 'insufficient_history', page: 1 })
      )
    );
  });

  it('debounces the customer-id search', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(CustomerTable, { props });
    await screen.findByText('C1');
    getResults.mockClear();
    const box = screen.getByLabelText(/search customer/i);
    await fireEvent.input(box, { target: { value: 'ab' } });
    await fireEvent.input(box, { target: { value: 'abc' } });
    expect(getResults).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(350);
    await waitFor(() => expect(getResults).toHaveBeenCalledTimes(1));
    expect(getResults).toHaveBeenCalledWith('j', expect.objectContaining({ q: 'abc', page: 1 }));
  });

  it('pages forward and back, disabling buttons at the ends', async () => {
    getResults.mockResolvedValue(page([row()], 120, 1));
    render(CustomerTable, { props });
    await screen.findByText('C1');
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
    await fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(getResults).toHaveBeenLastCalledWith('j', expect.objectContaining({ page: 2 })));
  });

  it('shows placeholders as dashes and an interval only when one exists', async () => {
    getResults.mockResolvedValue(
      page([
        row({ customer_id: 'good', clv_lower: 100, clv_upper: 140 }),
        row({
          customer_id: 'bad',
          data_quality: 'forecast_unavailable',
          p_alive: 0,
          expected_purchases: 0,
          clv_point: 0
        })
      ])
    );
    render(CustomerTable, { props: { ...props, hasClvInterval: true } });
    await screen.findByText('good');
    expect(screen.getByText('100.00 – 140.00')).toBeInTheDocument();
    const badRow = screen.getByText('bad').closest('tr')!;
    expect(within(badRow).getAllByText('—').length).toBeGreaterThanOrEqual(4); // purchases, P(alive), CLV, range
    expect(within(badRow).getByText('No forecast')).toBeInTheDocument();
  });

  it('shows a dash for the CLV of a low-history customer whose CLV is a 0.0 placeholder', async () => {
    getResults.mockResolvedValue(
      page([
        row({ customer_id: 'thin-real', data_quality: 'insufficient_history', clv_point: 42 }),
        row({ customer_id: 'thin-none', data_quality: 'insufficient_history', clv_point: 0 })
      ])
    );
    render(CustomerTable, { props });
    await screen.findByText('thin-real');
    expect(within(screen.getByText('thin-real').closest('tr')!).getByText('42.00')).toBeInTheDocument();
    expect(within(screen.getByText('thin-none').closest('tr')!).getByText('—')).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    getResults.mockResolvedValueOnce(page([], 0));
    render(CustomerTable, { props });
    expect(await screen.findByText(/no customers match/i)).toBeInTheDocument();
  });
});
