<script lang="ts">
  let { label }: { option: unknown; label: string; height?: string } = $props();
</script>

<div role="img" aria-label={label}></div>
