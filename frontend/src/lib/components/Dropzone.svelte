<script lang="ts">
  let { onselect, disabled = false }: { onselect: (file: File) => void; disabled?: boolean } = $props();
  let over = $state(false);

  function pick(files: FileList | File[] | null | undefined) {
    const first = files?.[0];
    if (!disabled && first) onselect(first);
  }
</script>

<div
  class="zone"
  class:over
  data-testid="dropzone"
  role="group"
  aria-label="CSV drop zone"
  ondragover={(e) => {
    e.preventDefault();
    if (!disabled) over = true;
  }}
  ondragleave={() => (over = false)}
  ondrop={(e) => {
    e.preventDefault();
    over = false;
    pick(e.dataTransfer?.files);
  }}
>
  <p>Drag a transaction-log CSV here, or</p>
  <label class="pick">
    Choose a CSV file
    <input type="file" accept=".csv,text/csv" {disabled} onchange={(e) => pick(e.currentTarget.files)} />
  </label>
</div>

<style>
  .zone {
    border: 2px dashed var(--line);
    border-radius: 12px;
    padding: 2.5rem 1rem;
    text-align: center;
    background: var(--card);
  }
  .zone.over {
    border-color: var(--accent);
    background: #eff4ff;
  }
  .pick {
    color: var(--accent);
    font-weight: 600;
    cursor: pointer;
  }
  .pick input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
  }
  .pick:focus-within {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>
