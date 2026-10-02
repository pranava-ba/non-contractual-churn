<script lang="ts">
  import { goto } from '$app/navigation';
  import { api, ApiError } from '$lib/api';
  import { validateFile } from '$lib/csvHeader';
  import Dropzone from '$lib/components/Dropzone.svelte';

  let file = $state<File | null>(null);
  let problems = $state<string[]>([]);
  let hasAmount = $state(true);
  let serverError = $state('');
  let busy = $state(false);

  async function onselect(f: File) {
    file = null;
    serverError = '';
    const check = await validateFile(f);
    problems = check.errors;
    hasAmount = check.hasAmount;
    if (check.ok) file = f;
  }

  async function submit() {
    if (!file) return;
    busy = true;
    serverError = '';
    try {
      const { job_id } = await api.uploadCsv(file);
      await goto(`/jobs/${job_id}`);
    } catch (e) {
      serverError = e instanceof ApiError ? e.message : 'Upload failed';
    } finally {
      busy = false;
    }
  }
</script>

<h1>Upload a transaction log</h1>
<p class="lede">
  One row per purchase, with columns <code>customer_id</code>, <code>transaction_date</code> and (optional)
  <code>amount</code>. You get per-customer purchase, retention and lifetime-value forecasts back.
</p>

<Dropzone {onselect} disabled={busy} />

{#if problems.length}
  <ul class="errors" role="alert">
    {#each problems as p}<li>{p}</li>{/each}
  </ul>
{/if}

{#if file}
  <div class="ready">
    <p><strong>{file.name}</strong> ({(file.size / 1024).toFixed(0)} KB)</p>
    {#if !hasAmount}
      <p class="note">
        No <code>amount</code> column — purchase forecasts only, no lifetime-value (CLV) figures.
      </p>
    {/if}
    <button onclick={submit} disabled={busy}>{busy ? 'Uploading…' : 'Upload and forecast'}</button>
  </div>
{/if}

{#if serverError}<p class="errors" role="alert">{serverError}</p>{/if}

<style>
  .lede {
    color: var(--muted);
    max-width: 46rem;
  }
  .errors {
    color: var(--bad);
  }
  .note {
    color: var(--warn);
  }
  .ready {
    margin-top: 1rem;
  }
  button {
    background: var(--accent);
    color: #fff;
    border: 0;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-size: 1rem;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.6;
    cursor: wait;
  }
</style>
