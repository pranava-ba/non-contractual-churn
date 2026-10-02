import type { EChartsCoreOption } from 'echarts/core';
import type { Histogram } from './types';

export interface HistogramOptions {
  seriesName: string;
  xLabel: string;
  fmt: (n: number) => string;
}

export function histogramOption(h: Histogram, o: HistogramOptions): EChartsCoreOption {
  if (h.edges.length !== h.counts.length + 1) {
    throw new Error('edges must have counts.length + 1 entries');
  }
  const labels = h.counts.map((_, i) => `${o.fmt(h.edges[i])}–${o.fmt(h.edges[i + 1])}`);
  return {
    aria: { enabled: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 56, right: 16, top: 24, bottom: 56 },
    xAxis: {
      type: 'category',
      data: labels,
      name: o.xLabel,
      nameLocation: 'middle',
      nameGap: 38,
      axisLabel: { hideOverlap: true }
    },
    yAxis: { type: 'value', name: 'Customers', minInterval: 1 },
    series: [
      { name: o.seriesName, type: 'bar', data: h.counts, barCategoryGap: '8%', itemStyle: { color: '#2563eb' } }
    ]
  };
}
