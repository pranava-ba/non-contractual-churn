<script lang="ts">
  import { goto } from '$app/navigation';
  import { api, ApiError } from '$lib/api';
  import { pollJob } from '$lib/poller';
  import Dashboard from '$lib/components/Dashboard.svelte';
  import type { JobInfo } from '$lib/types';

  let { id }: { id: string } = $props();

  let job = $state<JobInfo | null>(null);
  let notFound = $state(false);
  let netError = $state('');
  let refitting = $state(false);
  let refitError = $state('');

  async function refit() {
    refitting = true;
    refitError = '';
    try {
      const { job_id } = await api.refitJob(id);
      await goto(`/jobs/${job_id}`);
    } catch (e) {
      refitError = e instanceof ApiError ? e.message : 'Could not start the refit';
    } finally {
      refitting = false;
    }
  }

  // SvelteKit reuses this component when navigating between /jobs/A and /jobs/B (the refit
  // button does exactly that), so polling is keyed on `id` rather than started once on mount.
  $effect(() => {
    const jobId = id;
    job = null;
    notFound = false;
    netError = '';
    refitError = '';
    const ctl = new AbortController();
    pollJob(jobId, { getJob: api.getJob, onUpdate: (j) => (job = j), signal: ctl.signal }).catch((e) => {
      if (e?.name === 'AbortError') return;
      if (e instanceof ApiError && (e.status === 404 || e.status === 400)) notFound = true;
      else netError = e instanceof ApiError ? e.message : 'Lost contact with the server';
    });
    return () => ctl.abort();
  });
</script>

{#if notFound}
  <h1>Job not found</h1>
  <p>We couldn't find that job. <a href="/">Upload a file</a> to start a new one.</p>
{:else if netError}
  <h1>Connection problem</h1>
  <p role="alert">{netError}. <a href={`/jobs/${id}`}>Retry</a></p>
{:else if !job || job.status === 'queued' || job.status === 'running'}
  <h1>Working on your forecast…</h1>
  <p aria-live="polite">Status: <strong>{job?.status ?? 'queued'}</strong>. This page updates automatically.</p>
{:else if job.status === 'failed'}
  <h1>Forecast failed</h1>
  <p role="alert">{job.error_reason ?? 'The job failed for an unknown reason.'}</p>
  <p><a href="/">Upload another file</a></p>
{:else}
  <div data-testid="job-done">
    <h1>Your forecast</h1>
    <p class="fit" data-testid="fit-info">
      Fitted with: <strong>{job.fit_method === 'mcmc' ? 'High-precision (MCMC)' : 'Fast estimator'}</strong>
      {#if job.fit_method !== 'mcmc'}
        <button onclick={refit} disabled={refitting}>
          {refitting ? 'Starting…' : 'Refit with high-precision MCMC'}
        </button>
      {/if}
    </p>
    {#if job.fit_note}<p class="note">{job.fit_note}</p>{/if}
    {#if refitError}<p class="errors" role="alert">{refitError}</p>{/if}
    {#key id}
      <Dashboard jobId={id} />
    {/key}
  </div>
{/if}

<style>
  .note {
    color: var(--warn);
  }
  .errors {
    color: var(--bad);
  }
  .fit button {
    margin-left: 0.75rem;
    background: var(--accent);
    color: #fff;
    border: 0;
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    cursor: pointer;
  }
  .fit button:disabled {
    opacity: 0.6;
    cursor: wait;
  }
</style>
