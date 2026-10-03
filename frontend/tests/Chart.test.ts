import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

const setOption = vi.fn();
const resize = vi.fn();
const dispose = vi.fn();
vi.mock('echarts/core', () => ({
  init: vi.fn(() => ({ setOption, resize, dispose })),
  use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ BarChart: {} }));
vi.mock('echarts/components', () => ({ GridComponent: {}, TitleComponent: {}, TooltipComponent: {}, AriaComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

import Chart from '../src/lib/components/Chart.svelte';

describe('Chart', () => {
  it('initialises ECharts, applies the option, and disposes on unmount', () => {
    const option = { series: [{ type: 'bar', data: [1] }] };
    const { unmount, getByRole } = render(Chart, { props: { option, label: 'P(alive) histogram' } });
    expect(getByRole('img', { name: 'P(alive) histogram' })).toBeInTheDocument();
    expect(setOption).toHaveBeenCalledWith(option, true);
    unmount();
    expect(dispose).toHaveBeenCalled();
  });
});
