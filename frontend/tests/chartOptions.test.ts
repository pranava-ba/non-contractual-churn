import { describe, expect, it } from 'vitest';
import { histogramOption } from '../src/lib/chartOptions';

const fmt = (n: number) => n.toFixed(1);

describe('histogramOption', () => {
  const h = { edges: [0, 1, 2, 3], counts: [5, 0, 7] };

  it('labels each bin with its range and carries the counts as bar data', () => {
    const o: any = histogramOption(h, { title: 'Distribution of P(alive)', seriesName: 'Customers', xLabel: 'P(alive)', fmt });
    expect(o.xAxis.data).toEqual(['0.0–1.0', '1.0–2.0', '2.0–3.0']);
    expect(o.series[0].type).toBe('bar');
    expect(o.series[0].data).toEqual([5, 0, 7]);
    expect(o.xAxis.name).toBe('P(alive)');
    expect(o.yAxis.name).toBe('Customers');
  });

  it('carries a hidden title so ECharts names the chart in its accessibility description', () => {
    const o: any = histogramOption(h, { title: 'Distribution of P(alive)', seriesName: 'Customers', xLabel: 'x', fmt });
    expect(o.title).toEqual({ text: 'Distribution of P(alive)', show: false });
  });

  it('enables accessibility descriptions and an axis tooltip', () => {
    const o: any = histogramOption(h, { title: 'T', seriesName: 'Customers', xLabel: 'x', fmt });
    expect(o.aria.enabled).toBe(true);
    expect(o.tooltip.trigger).toBe('axis');
  });

  it('rejects mismatched edges/counts', () => {
    expect(() => histogramOption({ edges: [0, 1], counts: [1, 2] }, { title: 't', seriesName: 's', xLabel: 'x', fmt })).toThrow(
      'edges must have counts.length + 1 entries'
    );
  });
});
