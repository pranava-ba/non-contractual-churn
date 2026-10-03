<script lang="ts">
  import type { DataQuality } from '$lib/types';
  import { QUALITY_HELP, QUALITY_LABEL } from '$lib/format';
  let { quality }: { quality: DataQuality } = $props();
</script>

<span class="badge {quality}" title={QUALITY_HELP[quality]}>{QUALITY_LABEL[quality]}</span>

<style>
  .badge {
    font-size: 0.75rem;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--card);
  }
  .ok {
    color: var(--good);
  }
  .insufficient_history,
  .clv_unavailable {
    color: var(--warn);
  }
  .forecast_unavailable {
    color: var(--bad);
  }
</style>
