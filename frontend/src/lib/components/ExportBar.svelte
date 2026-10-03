<script lang="ts">
  import { exportUrl } from '$lib/api';
  import { QUALITY_HELP, QUALITY_LABEL, formatInt } from '$lib/format';
  import type { DataQuality } from '$lib/types';

  let { jobId, qualityCounts }: { jobId: string; qualityCounts: Partial<Record<DataQuality, number>> } = $props();

  const flagged = $derived(
    (Object.entries(qualityCounts) as [DataQuality, number][]).filter(([q, n]) => q !== 'ok' && n > 0)
  );
</script>

<div class="bar">
  <a class="dl" href={exportUrl(jobId)} download={`forecasts-${jobId}.csv`}>Download CSV</a>
  {#if flagged.length}
    <details>
      <summary>About data-quality flags</summary>
      <ul>
        {#each flagged as [q, n]}
          <li>{`${QUALITY_LABEL[q]} — ${formatInt(n)} customers. ${QUALITY_HELP[q]}`}</li>
        {/each}
      </ul>
    </details>
  {/if}
</div>

<style>
  .bar {
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
    flex-wrap: wrap;
    margin: 1rem 0;
  }
  .dl {
    background: var(--accent);
    color: #fff;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
  }
  details {
    color: var(--muted);
    max-width: 40rem;
  }
  summary {
    cursor: pointer;
  }
</style>
