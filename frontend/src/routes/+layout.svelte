<script lang="ts">
  let { children } = $props();
</script>

<header class="bar">
  <a href="/" class="brand">CLV Forecasts</a>
</header>
<main>{@render children()}</main>

<style>
  :global(:root) {
    --bg: #f7f8fa; --fg: #14181f; --muted: #5b6573; --card: #ffffff;
    --line: #dde1e7; --accent: #2563eb; --warn: #b45309; --bad: #b91c1c; --good: #15803d;
  }
  :global(body) {
    margin: 0; background: var(--bg); color: var(--fg);
    font: 16px/1.5 system-ui, -apple-system, 'Segoe UI', sans-serif;
  }
  .bar { background: var(--card); border-bottom: 1px solid var(--line); padding: 0.75rem 1.5rem; }
  .brand { font-weight: 600; color: var(--fg); text-decoration: none; }
  main { max-width: 72rem; margin: 0 auto; padding: 1.5rem; }
</style>
