<script lang="ts">
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api';
  import { histogramOption } from '$lib/chartOptions';
  import { formatMoney, formatNum, formatPct } from '$lib/format';
  import type { DataQuality, JobSummary } from '$lib/types';
  import Chart from './Chart.svelte';
  import CustomerTable from './CustomerTable.svelte';
  import SummaryTiles from './SummaryTiles.svelte';

  let { jobId }: { jobId: string } = $props();
  let summary = $state<JobSummary | null>(null);
  let error = $state('');

  onMount(async () => {
    try {
      summary = await api.getSummary(jobId);
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Could not load the dashboard';
    }
  });

  const hasClv = $derived((summary?.quality_counts.ok ?? 0) > 0);
  const qualities = $derived(Object.keys(summary?.quality_counts ?? {}) as DataQuality[]);
</script>

{#if error}
  <p role="alert" class="err">{error}</p>
{:else if !summary}
  <p>Loading results…</p>
{:else}
  <SummaryTiles {summary} />
  <div class="charts">
    <section>
      <h3>How likely is each customer to still be active?</h3>
      <Chart
        label="Distribution of P(alive)"
        option={histogramOption(summary.histograms.p_alive, {
          seriesName: 'Customers',
          xLabel: 'P(alive)',
          fmt: formatPct
        })}
      />
    </section>
    <section>
      <h3>Expected purchases per customer</h3>
      <Chart
        label="Distribution of expected purchases"
        option={histogramOption(summary.histograms.expected_purchases, {
          seriesName: 'Customers',
          xLabel: 'Expected purchases',
          fmt: formatNum
        })}
      />
    </section>
    {#if hasClv}
      <section>
        <h3>Customer lifetime value</h3>
        <Chart
          label="Distribution of customer lifetime value"
          option={histogramOption(summary.histograms.clv_point, {
            seriesName: 'Customers',
            xLabel: 'CLV',
            fmt: formatMoney
          })}
        />
      </section>
    {/if}
  </div>
  <CustomerTable {jobId} hasClvInterval={summary.has_clv_interval} {qualities} />
  <!-- Task 11 mounts the export button. -->
{/if}

<style>
  .err {
    color: var(--bad);
  }
  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
    gap: 1.25rem;
    margin-top: 1.5rem;
  }
  section {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1rem;
  }
  h3 {
    margin: 0 0 0.5rem;
    font-size: 1rem;
  }
</style>
