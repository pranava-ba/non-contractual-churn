<script lang="ts">
  import { page } from '$app/state';
  import JobView from '$lib/components/JobView.svelte';
</script>

<JobView id={page.params.id as string} />
