import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Dropzone from '../src/lib/components/Dropzone.svelte';

describe('Dropzone', () => {
  it('calls onselect with the chosen file', async () => {
    const onselect = vi.fn();
    render(Dropzone, { props: { onselect } });
    const file = new File(['x'], 'log.csv', { type: 'text/csv' });
    await fireEvent.change(screen.getByLabelText(/choose a csv/i), { target: { files: [file] } });
    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('calls onselect on drop', async () => {
    const onselect = vi.fn();
    render(Dropzone, { props: { onselect } });
    const file = new File(['x'], 'log.csv', { type: 'text/csv' });
    await fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files: [file] } });
    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('ignores input while disabled', async () => {
    const onselect = vi.fn();
    render(Dropzone, { props: { onselect, disabled: true } });
    await fireEvent.drop(screen.getByTestId('dropzone'), {
      dataTransfer: { files: [new File(['x'], 'a.csv')] }
    });
    expect(onselect).not.toHaveBeenCalled();
  });
});
