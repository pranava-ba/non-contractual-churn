import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const goto = vi.fn();
const uploadCsv = vi.fn();
vi.mock('$app/navigation', () => ({ goto: (...a: unknown[]) => goto(...a) }));
vi.mock('$lib/api', async (orig) => {
  const actual = await orig<typeof import('../src/lib/api')>();
  return { ...actual, api: { uploadCsv: (...a: unknown[]) => uploadCsv(...a) } };
});

import { ApiError } from '../src/lib/api';
import Page from '../src/routes/+page.svelte';

const pick = async (file: File) =>
  fireEvent.change(screen.getByLabelText(/choose a csv/i), { target: { files: [file] } });

describe('upload page', () => {
  beforeEach(() => {
    goto.mockReset();
    uploadCsv.mockReset();
  });

  it('uploads a valid file and navigates to the job page', async () => {
    uploadCsv.mockResolvedValue({ job_id: 'job-42' });
    render(Page);
    await pick(
      new File(['customer_id,transaction_date,amount\n1,2024-01-01,5\n'], 'log.csv', { type: 'text/csv' })
    );

    const button = await screen.findByRole('button', { name: /forecast/i });
    await fireEvent.click(button);

    await waitFor(() => expect(goto).toHaveBeenCalledWith('/jobs/job-42'));
  });

  it('defaults to auto and passes a changed precision mode to the upload', async () => {
    uploadCsv.mockResolvedValue({ job_id: 'job-7' });
    render(Page);
    await pick(new File(['customer_id,transaction_date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    const select = (await screen.findByLabelText(/precision/i)) as HTMLSelectElement;
    expect(select.value).toBe('auto');
    await fireEvent.change(select, { target: { value: 'mcmc' } });
    await fireEvent.click(await screen.findByRole('button', { name: /forecast/i }));
    await waitFor(() => expect(uploadCsv).toHaveBeenCalledWith(expect.any(File), 'mcmc'));
  });

  it('shows header problems and does not offer to upload', async () => {
    render(Page);
    await pick(new File(['id,date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    expect(await screen.findByText(/missing required column "customer_id"/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /forecast/i })).not.toBeInTheDocument();
  });

  it('warns when there is no amount column', async () => {
    render(Page);
    await pick(new File(['customer_id,transaction_date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    expect(await screen.findByText(/no lifetime-value \(clv\) figures/i)).toBeInTheDocument();
  });

  it('shows the server error when the upload is rejected', async () => {
    uploadCsv.mockRejectedValue(new ApiError(400, 'transaction log is empty'));
    render(Page);
    await pick(new File(['customer_id,transaction_date\n1,2024-01-01\n'], 'log.csv', { type: 'text/csv' }));
    await fireEvent.click(await screen.findByRole('button', { name: /forecast/i }));
    expect(await screen.findByText('transaction log is empty')).toBeInTheDocument();
    expect(goto).not.toHaveBeenCalled();
  });
});
