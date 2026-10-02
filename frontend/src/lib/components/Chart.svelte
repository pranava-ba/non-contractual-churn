<script lang="ts">
  import { onMount } from 'svelte';
  import * as echarts from 'echarts/core';
  import type { EChartsCoreOption } from 'echarts/core';
  import { BarChart } from 'echarts/charts';
  import { AriaComponent, GridComponent, TooltipComponent } from 'echarts/components';
  import { CanvasRenderer } from 'echarts/renderers';

  echarts.use([BarChart, GridComponent, TooltipComponent, AriaComponent, CanvasRenderer]);

  let { option, label, height = '260px' }: { option: EChartsCoreOption; label: string; height?: string } = $props();

  let el: HTMLDivElement;
  let chart: ReturnType<typeof echarts.init> | undefined;

  onMount(() => {
    chart = echarts.init(el);
    chart.setOption(option, true);
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => chart?.resize()) : undefined;
    ro?.observe(el);
    return () => {
      ro?.disconnect();
      chart?.dispose();
      chart = undefined;
    };
  });

  $effect(() => {
    chart?.setOption(option, true);
  });
</script>

<div bind:this={el} role="img" aria-label={label} style:height></div>
