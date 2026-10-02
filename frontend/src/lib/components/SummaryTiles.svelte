<script lang="ts">
  import type { JobSummary } from '$lib/types';
  import { formatInt, formatMoney, formatNum, formatPct } from '$lib/format';

  let { summary }: { summary: JobSummary } = $props();

  const hasClv = $derived((summary.quality_counts.ok ?? 0) > 0);
  const limited = $derived(summary.n_customers - (summary.quality_counts.ok ?? 0));
</script>

<div class="tiles">
  <div class="tile"><span class="k">Customers</span><span class="v">{formatInt(summary.n_customers)}</span></div>
  <div class="tile">
    <span class="k">Expected purchases (total)</span><span class="v">{formatNum(summary.total_expected_purchases)}</span>
  </div>
  <div class="tile"><span class="k">Mean P(alive)</span><span class="v">{formatPct(summary.mean_p_alive)}</span></div>
  {#if hasClv}
    <div class="tile"><span class="k">Total CLV</span><span class="v">{formatMoney(summary.total_clv)}</span></div>
  {/if}
</div>
{#if limited > 0}
  <p class="note">
    {formatInt(limited)} customers have limited data and are excluded from the statistics above that they cannot support.
  </p>
{/if}

<style>
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    gap: 1rem;
  }
  .tile {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
  }
  .k {
    color: var(--muted);
    font-size: 0.85rem;
  }
  .v {
    font-size: 1.6rem;
    font-weight: 600;
  }
  .note {
    color: var(--muted);
    font-size: 0.9rem;
  }
</style>
