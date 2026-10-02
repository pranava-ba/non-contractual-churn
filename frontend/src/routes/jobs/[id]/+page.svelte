<script lang="ts">
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api';
  import { pollJob } from '$lib/poller';
  import type { JobInfo } from '$lib/types';

  const id = page.params.id as string;
  let job = $state<JobInfo | null>(null);
  let notFound = $state(false);
  let netError = $state('');

  onMount(() => {
    const ctl = new AbortController();
    pollJob(id, { getJob: api.getJob, onUpdate: (j) => (job = j), signal: ctl.signal }).catch((e) => {
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
    <h1>Forecast ready</h1>
    <!-- Tasks 9–11 mount the dashboard, table and export button here. -->
  </div>
{/if}
