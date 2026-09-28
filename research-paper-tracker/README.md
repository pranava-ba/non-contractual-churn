# Research Paper Tracker

Living literature tracker for the **non-contractual churn / BTYD calibration** paper
(part of the `pareto-nbd-extension` project). Pulls new papers from OpenAlex and
Crossref, bucketed into four keyword categories, floored at 2023. Pulls at
least **title + DOI** for each paper, dedupes across runs, and writes a master CSV per
category. The SQLite DB (`data/tracker.db`) is the source of truth.

## Categories

**Living keyword monitor (2023+):**
1. **Non-Contractual Churn** *(priority)*
2. Buy-Till-You-Die Models (BG/NBD, Pareto/NBD)
3. CLV & RFM in Non-Contractual Settings
4. ML / Deep Learning for Non-Contractual Churn

**Static historical layer (ingestion-only, not keyword-refreshed):**
5. **Foundations & Origins** — the ~38 seed papers (Ehrenberg 1959 → Simon 2025 / Ulrich 2026)
6. **Genealogy — full citation tree** — the whole 3,000-paper historical corpus
7. **Core reading (Tier A)** — the sifted spine (~130 papers) from the triage funnel

> Scope note: this tracker was repurposed from an earlier finance/information-theory
> tracker (the old config is preserved under `config/_finance_backup/`). Categories 1–4
> target the non-contractual customer-base-analysis literature.
>
> **Genealogy layer (added 2026-09-20).** Categories 5–7 hold the field's *history* —
> a citation tree from the origins (Ehrenberg 1959) to the present, built and sifted by
> [`tools/genealogy/`](tools/genealogy/) and ingested into `tracker.db` (`source='genealogy'`).
> The publication floor was lowered `2023 → 1959` so the DB is **one unified corpus**
> spanning the field's history → the live monitor. `tools/curate.py` never auto-hides
> genealogy papers. See [`deep_research/FIELD_GENEALOGY.md`](../deep_research/FIELD_GENEALOGY.md)
> and `tools/genealogy/README.md` for the method and the triage funnel (how ~3,000 papers
> become a ~130-paper reading list).

## How it works

- **Sources:** [OpenAlex](https://openalex.org), [Crossref](https://www.crossref.org)
  and [arXiv](https://arxiv.org) (`src/sources/arxiv.py`; used directly by the causal-ML
  categories, see `config/categories.yaml`). **Semantic Scholar**
  (`src/sources/semanticscholar.py`) is not a feed — it's a best-effort abstract
  backfill: when both OpenAlex and Crossref return no abstract for a candidate (common
  for publishers that don't hand Crossref one), it's looked up by DOI/arXiv id before
  matching, since a title-only record otherwise weakens `src/match.py`'s scoring.
- **Scope:** every keyword category uses open search across all venues, with
  per-category `require_all` term groups + `exclude` terms for precision; the curated
  `config/journals.yaml` list only assigns journal **tiers** used to break ranking ties.
  Each category also carries a `group: nbd | causal` used by the Coverage page (below).
- **SQLite is the source of truth** (`data/tracker.db`). CSV exports and the GUI are
  read-layers over it. A `seen` table guarantees a paper is surfaced once. Config is
  validated upfront (`src/config.py`) — a typo in `categories.yaml`/`settings.yaml`
  raises a clear error before any API call, instead of a bare `KeyError` mid-run.
- **Precision:** each keyword category has `require_all` term groups and `exclude`
  terms; `min_hits` per group (a title hit counts double) kills incidental matches;
  a per-venue diversity cap can stop one journal from monopolising a category; broad
  mega-journals (e.g. IEEE Access, Scientific Reports) can be flagged to pass a
  topical `sieve`; OpenAlex's own topic `concepts` are also captured per paper as a
  secondary relevance signal alongside the keyword regex.
- **Ranking → top N:** categories rank by match strength, then OpenAlex relevance,
  journal tier, and recency. Capped at `top_n` new papers per category per run
  (default 120; this survey config sets 120–150 to keep the whole corpus).
- **Resilience:** a rate-limit failure partway through paging keeps whatever pages
  already succeeded instead of discarding them; a config/logic error in one category
  no longer aborts the whole run (each category is isolated, like each feed already
  was); OpenAlex/Crossref call counts are logged per run and checked against a
  documented shared daily budget (`openalex_daily_budget` in `settings.yaml`).
- **Same-run feed cache:** if two categories resolve to the literal same
  `(source, mode, query, window)`, it's fetched once and reused, not re-paged per
  category.

## Quick start

```bash
pip install -r requirements.txt
python -m src.run                 # refresh (auto window since last refresh)
python -m src.status              # last refreshed / due / overdue
python -m src.run --lookback 30   # force a specific window (days)
python -m src.run --dry-run       # fetch + rank, write nothing
```

**Tests.** `pip install -r requirements-dev.txt` then `pytest` (from this directory).
Covers config validation, term-matching/ranking, storage, the `.bib` cross-reference
parser, the refresh-window calculation, and a golden-set regression suite: representative
fixtures (not real paper text) for each live category, including the exact "bare RFM +
clustering" and "pure contractual churn" near-misses that once slipped through — a future
`categories.yaml` edit that silently narrows or widens a term group should fail one of
these before it costs another manual curation pass to notice.

Output: one CSV per category in `data/out/` (columns: date_added, rank, title, doi,
arxiv_id, authors, venue, publication_date, source, matched_terms, match_score,
relevance, url). Dates are dd/mm/yyyy.

## Refresh model (manual)

Refreshing is manual — you decide when. Each refresh records its date, and the
tracker reports status (`python -m src.status`, or the GUI):

- *Up to date - next refresh in 5 days (due 2026-07-16).*
- *Refresh due today.*
- *Refresh overdue by 8 days - last refreshed 2026-07-09 (15 days ago).*

The cadence is `refresh_interval_days` (default 7). The lookback window **auto-covers
everything since the last refresh** (plus `lag_margin_days` for publication-date lag,
capped at `max_lookback_days`), so a late refresh never misses papers, and dedup means
overlap never repeats one.

## Configuration (no code needed)

| File | What to edit |
|------|--------------|
| `config/journals.yaml`   | curated journals per area; `issn`, `tier`, optional `sieve` |
| `config/categories.yaml` | categories: feeds, `require_all`/`exclude` terms, `min_hits`, `top_n`, `sieve_terms`, `group` (`nbd`/`causal`, for the Coverage page) |
| `config/settings.yaml`   | contact email, `lookback_days`, `default_top_n`, `max_per_venue`, repository filter, `bib_files`, budget/Unpaywall/Semantic-Scholar settings |

Term matching is case-insensitive and word-boundary aware; spaces and hyphens are
interchangeable; a trailing `*` is a prefix match (e.g. `predict*`). All three config
files are validated on load (`src/config.py`) — a missing required key or a bad
`group` value raises a `ConfigError` immediately, before any API call.

## Curation — two-stage filtering

The keyword filter (`config/categories.yaml`) is tuned for **recall** — catch
everything on topic. A second **precision** pass, `tools/curate.py`, drops what still
leaks through: generic *RFM + clustering segmentation* papers, contractual
telecom/subscription/OTT/SaaS churn (out of scope for a non-contractual paper),
non-English titles, and hard off-topic keyword false positives (e.g. remote-sensing
"RFM"). This split is deliberate: an `exclude` on `telecom`/`segmentation` in the
keyword config would also drop good methodology papers that merely *benchmark* on such
data, so the topical calls are made title-aware in `curate.py`, not by blunt keyword.

```bash
python tools/curate.py                # DRY RUN: writes review + snapshot + funnel, changes nothing
python tools/curate.py --apply        # hide the removals (after a timestamped DB backup)
python tools/curate.py --dedupe-check # also write possible_duplicates.csv (audit-only)
```

Outputs (all under `data/out/`):

| File | What it is |
|------|------------|
| `all_papers.csv`            | regenerable snapshot of **every** paper + its categories + read/star/hidden state |
| `curation_review.csv`       | per-paper keep/remove **decision + reason** (audit every call) |
| `removed_papers.csv`        | every hidden paper with its removal reason |
| `funnel_counts.csv`         | PRISMA-style counts per category (identified → excluded-by-reason → kept) — the numbers for the paper's figure |
| `possible_duplicates.csv`   | (`--dedupe-check` only) candidate duplicate pairs by normalized title — e.g. an arXiv preprint and its later DOI'd version, which get different `uid`s and are never merged automatically. Audit-only: nothing is hidden or merged for you; hide whichever `uid` you don't want counted. |

Removals are **reversible**: they set `paper_state.hidden=1` (not a delete), a fresh
`tracker.db.bak-*` is written first, and the GUI's **Show → Hidden** filter + each
row's eye button let you un-hide anything. Re-run `curate.py --apply` after each
refresh to re-clean newly surfaced papers.

**Recommended daily workflow:** open the app (it auto-shows refresh status) → **Refresh**
(or `python -m src.run`) → `python tools/curate.py --apply` → skim, star, and cite.

## Desktop app (GUI)

A PyQt6 WebEngine dashboard over the same SQLite DB. Visual design generated with
the **ui-ux-pro-max** skill: indigo/violet **cinematic glassmorphism** — deep
gradient backdrop with ambient glow, frosted-glass panels, Sora + Inter, light/dark,
WCAG-AA.

```bash
pip install -r requirements-gui.txt
python -m gui
```

**Desktop shortcut (no exe needed).** Run `python tools/make_shortcut.py` once — it puts a
**"Paper Tracker"** shortcut with a custom icon on your Desktop that launches the app via
`pythonw.exe` (no console window). Right-click it → *Pin to Start* / *Pin to taskbar*.
Re-run the script if you move the project folder.

**Three tabs:**
- **Papers** — category sidebar (collapsible; the priority Non-Contractual Churn bucket starred),
  **Week** filter, **search** (title/author/term), **sort** (rank/date/venue), and a
  **Show** filter (all / unread / starred). Each row has a **read tick** (read papers
  dim), a **star**, a **download** button, and **copy citation**; it shows **why it
  surfaced** (matched-term chips or a "Top-journal pick / arXiv preprint" tag). Click a
  row for the abstract + match detail, or a title to open its DOI.
- **Analytics** — KPI cards (incl. read/starred counts) + charts: papers per category,
  papers per week, source split, top venues, and hot topics (most frequent matched terms).
- **Coverage** — a review-status board split into the two research tracks (each
  category's `group:` in `categories.yaml`): **Non-Contractual / BTYD (Gear 1)** and
  **Causal ML / Uplift (Gear 2)**. Every tracked (non-hidden) paper in the group appears
  once with three independent flags:
  - **Read** — the same skim-read tick as the Papers tab.
  - **Analyzed** — a separate, deeper flag for "actually deep-dived / evaluated," not
    just skimmed (e.g. the deep_research/*_deep_dive.md treatment some papers get).
  - **Used** — auto-detected by cross-referencing the paper's DOI/arXiv id/normalized
    title against that group's manuscript `.bib` file (`bib_files` in `settings.yaml`:
    `paper/refs_phase2.bib` for nbd, `paper_gear2/refs_gear2.bib` for causal) — a green
    "Used ✓" badge means it's actually cited in the manuscript. Click the badge to
    manually override it (cycles auto → forced-yes → forced-no → auto again), for a
    paper cited under a bib key that doesn't cleanly DOI/title-match.
  Each panel's header shows read/analyzed/used counts out of its total; rows sort
  unread-and-unanalyzed first so what still needs attention floats to the top.

**Downloads.** The download button fetches the PDF to `data/downloads/` and opens it, in
order: arXiv → OpenAlex's cached open-access link → **Unpaywall** (queried directly by
DOI, since OpenAlex's cache can lag it; `unpaywall_enabled` in `settings.yaml`) → Sci-Hub
mirrors — access to Sci-Hub may be legally restricted in your jurisdiction, so it's
opt-in (clear `scihub_mirrors` to disable).

- **Status banner** (green/amber/red) and **Refresh** button with a **spinner +
  determinate progress bar** ("Fetching … 3/7").
- **Exit** button; **keyboard shortcuts** (`R` refresh, `/` search, `Esc` collapse
  sidebar, `1–9` category); remembers your last tab/category/week/sidebar state.
- All displayed dates are **dd/mm/yyyy**.

## Roadmap

- Package the GUI as a standalone Windows `.exe` (PyInstaller; already in
  `requirements-gui.txt`).
