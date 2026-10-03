<script lang="ts">
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api';
  import { QUALITY_LABEL, formatMoney, formatNum, formatPct } from '$lib/format';
  import type { CustomerRow, DataQuality, ResultsQuery, SortKey } from '$lib/types';
  import QualityBadge from './QualityBadge.svelte';

  let {
    jobId,
    hasClvInterval,
    qualities
  }: { jobId: string; hasClvInterval: boolean; qualities: readonly DataQuality[] } = $props();

  const PAGE_SIZE = 50;
  let sort = $state<SortKey>('customer_id');
  let order = $state<'asc' | 'desc'>('asc');
  let quality = $state<DataQuality | ''>('');
  let search = $state('');
  let pageNo = $state(1);

  let rows = $state<CustomerRow[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let error = $state('');
  let seq = 0; // discards responses that arrive after a newer request was issued

  const pageCount = $derived(Math.max(1, Math.ceil(total / PAGE_SIZE)));

  async function load() {
    const mine = ++seq;
    loading = true;
    error = '';
    const query: ResultsQuery = { page: pageNo, pageSize: PAGE_SIZE, sort, order, quality, q: search };
    try {
      const res = await api.getResults(jobId, query);
      if (mine !== seq) return;
      rows = res.customers;
      total = res.total;
    } catch (e) {
      if (mine !== seq) return;
      error = e instanceof ApiError ? e.message : 'Could not load customers';
    } finally {
      if (mine === seq) loading = false;
    }
  }

  onMount(load);

  function sortBy(key: SortKey) {
    if (sort === key) order = order === 'asc' ? 'desc' : 'asc';
    else {
      sort = key;
      order = 'asc';
    }
    pageNo = 1;
    load();
  }
  function onQuality(e: Event) {
    quality = (e.currentTarget as HTMLSelectElement).value as DataQuality | '';
    pageNo = 1;
    load();
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  function onSearch(e: Event) {
    search = (e.currentTarget as HTMLInputElement).value;
    clearTimeout(timer);
    timer = setTimeout(() => {
      pageNo = 1;
      load();
    }, 300);
  }
  function go(delta: number) {
    pageNo += delta;
    load();
  }

  const ariaSort = (key: SortKey) => (sort !== key ? 'none' : order === 'asc' ? 'ascending' : 'descending');
  // Placeholder values (0.0 written by the worker, see data_quality) are never shown as numbers.
  const hasForecast = (r: CustomerRow) => r.data_quality !== 'forecast_unavailable';
  const hasClv = (r: CustomerRow) =>
    hasForecast(r) &&
    r.data_quality !== 'clv_unavailable' &&
    (r.data_quality !== 'insufficient_history' || r.clv_point > 0);

  const COLS: { key: SortKey; label: string }[] = [
    { key: 'customer_id', label: 'Customer' },
    { key: 'expected_purchases', label: 'Expected purchases' },
    { key: 'p_alive', label: 'P(alive)' },
    { key: 'clv_point', label: 'CLV' }
  ];
  const arrow = (key: SortKey) => (sort === key ? (order === 'asc' ? ' ▲' : ' ▼') : '');
</script>

<section class="wrap">
  <h2>Customers</h2>
  <div class="controls">
    <label>Search customer ID <input type="search" oninput={onSearch} /></label>
    <label
      >Data quality
      <select onchange={onQuality}>
        <option value="">All</option>
        {#each qualities as q}<option value={q}>{QUALITY_LABEL[q]}</option>{/each}
      </select>
    </label>
  </div>

  {#if error}
    <p role="alert" class="err">{error}</p>
  {:else if !loading && rows.length === 0}
    <p>No customers match these filters.</p>
  {:else}
    <div class="scroll">
      <table class:loading>
        <thead>
          <tr>
            {#each COLS as c}
              <th scope="col" aria-sort={ariaSort(c.key)}>
                <button onclick={() => sortBy(c.key)}>{c.label}{arrow(c.key)}</button>
              </th>
            {/each}
            {#if hasClvInterval}<th scope="col">CLV range</th>{/if}
            <th scope="col" aria-sort={ariaSort('data_quality')}>
              <button onclick={() => sortBy('data_quality')}>Data quality{arrow('data_quality')}</button>
            </th>
          </tr>
        </thead>
        <tbody>
          {#each rows as r (r.customer_id)}
            <tr>
              <td>{r.customer_id}</td>
              <td class="num">{hasForecast(r) ? formatNum(r.expected_purchases) : '—'}</td>
              <td class="num">{hasForecast(r) ? formatPct(r.p_alive) : '—'}</td>
              <td class="num">{hasClv(r) ? formatMoney(r.clv_point) : '—'}</td>
              {#if hasClvInterval}
                <td class="num"
                  >{hasClv(r) ? `${formatMoney(r.clv_lower)} – ${formatMoney(r.clv_upper)}` : '—'}</td
                >
              {/if}
              <td><QualityBadge quality={r.data_quality} /></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="pager">
      <button onclick={() => go(-1)} disabled={pageNo <= 1 || loading}>Previous</button>
      <span>Page {pageNo} of {pageCount}</span>
      <button onclick={() => go(1)} disabled={pageNo >= pageCount || loading}>Next</button>
    </div>
  {/if}
</section>

<style>
  .wrap {
    margin-top: 2rem;
  }
  .controls {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }
  .controls label {
    display: flex;
    flex-direction: column;
    font-size: 0.85rem;
    color: var(--muted);
    gap: 0.2rem;
  }
  .scroll {
    overflow-x: auto;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  table.loading {
    opacity: 0.6;
  }
  th,
  td {
    padding: 0.5rem 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--line);
  }
  th button {
    all: unset;
    cursor: pointer;
    font-weight: 600;
  }
  th button:focus-visible {
    outline: 2px solid var(--accent);
  }
  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .pager {
    display: flex;
    gap: 1rem;
    align-items: center;
    justify-content: flex-end;
    margin-top: 0.75rem;
  }
  .err {
    color: var(--bad);
  }
</style>
