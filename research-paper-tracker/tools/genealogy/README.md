# Genealogy — historical citation-tree builder + triage

Builds the **field's historical corpus** (origins → present) as a citation tree and
sifts it into read-tiers, then folds it into the main `tracker.db` as one unified
corpus. This is the *static history* layer under the living 2023+ keyword monitor.

See the narrative in [`deep_research/FIELD_GENEALOGY.md`](../../../deep_research/FIELD_GENEALOGY.md),
the industries map in [`INDUSTRIES_NONCONTRACTUAL.md`](../../../deep_research/INDUSTRIES_NONCONTRACTUAL.md),
the sifted reading list in [`CORE_READING_LIST.md`](../../../deep_research/CORE_READING_LIST.md),
and the year-by-year table in [`HISTORICAL_PROGRESSION.md`](../../../deep_research/HISTORICAL_PROGRESSION.md).

## Why not OpenAlex?

The builder originally used OpenAlex, but its **keyless daily IP budget** (1000 list
requests/day, shared per IP, resets midnight UTC) gets exhausted fast, and its
DOI-lookup path is budget-counted too. So the builder runs entirely on:

- **Crossref** `/works/{doi}` — metadata + `reference[]` (backward). Polite pool (mailto),
  generous limits. Also `/works?query.bibliographic=` to resolve each seed to its
  **canonical** version (prefers journal-article + high citations over preprint/report/
  thesis clones — this matters: several seeds otherwise resolve to a DTIC report or a
  Research-Square preprint of the real paper).
- **OpenCitations COCI** `/citations/{doi}` — citing DOIs (forward) of the seeds; free.

(If you have an OpenAlex API key, an OpenAlex builder is faster and gives cleaner
forward-citation lists — but this toolchain needs no key and no budget.)

## Pipeline (run in order)

```bash
cd research-paper-tracker/tools/genealogy
python 1_build_tree.py      # Crossref+COCI -> tree_nodes.csv, tree_edges.csv  (~10 min, network)
python 2_ingest_tree.py     # -> tracker.db (source='genealogy') + citation_edges table (backs up first)
python 3_triage.py          # -> genealogy_triage.csv + CORE_READING_LIST.md + DB tier tags
python 4_gen_history.py     # -> HISTORICAL_PROGRESSION.md
```

`1_build_tree.py` seeds from the field's origin papers + everything the manuscript
cites (~38 seeds), then expands **backward references depth 2** (relevance-gated at
depth 2 so refs-of-refs stays high-signal, not a 25k explosion) and **forward citations
of the seeds** (OpenCitations). Result: ~3000 papers, ~20k edges, spanning 1959→present.

## The triage funnel — how ~3000 papers become a reading list

`3_triage.py` scores every paper on **independent** signals and assigns a tier. No paper
is deleted; each is *labelled* (tier written to `paper_state.tags` as `tier:A/B/C/D`,
and Tier-A also gets a `core_reading` category so the GUI shows it as a bucket).

| Signal | Meaning |
|---|---|
| keyword relevance (0–9) | BTYD +3, churn +2, CLV +2, calibration +2 (title/abstract/venue) |
| seed-connectivity | # distinct foundational seeds a paper is edge-connected to |
| in-corpus degree | # corpus papers that cite it (forward influence *within the field*) |
| cross-source corroboration | reached via *both* a seed's references *and* something citing a seed |
| global citations | Crossref `is-referenced-by-count` |
| recency | 2023+ → candidate to promote into the live keyword monitor |

**Tiers**

- **A — core spine (read):** seeds; BTYD-tagged & well-connected; or high-relevance
  high-citation. *This is the literature review* (~130 papers).
- **B — on-topic (scan):** churn/CLV/BTYD/calibration with real links (~700).
- **C — weakly-linked on-topic (reference tail):** kept for lineage (~230).
- **D — tools / off-topic (archive):** keyword-relevance 0 — statistics/ML method papers
  and unrelated hits; kept so the citation tree stays complete, excluded from reading
  lists (~2000).

**QC passes:** duplicate/preprint-vs-published detection (same normalized title, different
DOI), orphan nodes (no edges → resolution noise), and year sanity. Flags are columns in
`genealogy_triage.csv` (`dup`, `orphan`), not deletions.

The last-mile human judgement then happens in the GUI (star/read/search over the
`core_reading` bucket) and in `deep_research/LITERATURE_MATRIX.md` (the calibration-lens
novelty screen for the specific paper).

## Outputs

| File | What |
|---|---|
| `tree_nodes.csv` / `tree_edges.csv` | raw graph (kept here for re-triage without a rebuild) |
| `research-paper-tracker/data/out/genealogy_tree.csv` | ingested corpus, chronological |
| `research-paper-tracker/data/out/genealogy_triage.csv` | every paper + all signals + tier (audit trail) |
| `deep_research/CORE_READING_LIST.md` | Tier-A spine, grouped by era |
| `deep_research/HISTORICAL_PROGRESSION.md` | year-by-year spine + forward descendants |

## Refreshing

The genealogy is a **static historical layer** — rebuild it only when you add seeds or
want to re-expand. The living 2023+ monitor (`python -m src.run`) is separate and
unaffected; `tools/curate.py` is patched to **never auto-hide** `source='genealogy'`
papers. To promote a recent (2023+) Tier-A/B genealogy paper into the active keyword
categories, star it in the GUI (starred papers are curation-protected).
