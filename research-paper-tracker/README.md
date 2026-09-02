# Research Paper Tracker

Living literature tracker for the **non-contractual churn / BTYD calibration** paper
(part of the `pareto-nbd-extension` project). Pulls new papers from OpenAlex and
Crossref, bucketed into four keyword categories, floored at 2023. Pulls at
least **title + DOI** for each paper, dedupes across runs, and writes a master CSV per
category. The SQLite DB (`data/tracker.db`) is the source of truth.

## Categories

1. **Non-Contractual Churn** *(priority)*
2. Buy-Till-You-Die Models (BG/NBD, Pareto/NBD)
3. CLV & RFM in Non-Contractual Settings
4. ML / Deep Learning for Non-Contractual Churn

> Scope note: this tracker was repurposed from an earlier finance/information-theory
> tracker (the old config is preserved under `config/_finance_backup/`). All four
> categories now target the non-contractual customer-base-analysis literature.

## How it works

- **Sources:** [OpenAlex](https://openalex.org) and [Crossref](https://www.crossref.org),
  by keyword search across all venues (2023+). An arXiv source module ships in
  `src/sources/arxiv.py`, but the current churn categories use the keyword feeds.
- **Scope:** all four categories use open keyword search across all venues, with
  per-category `require_all` term groups + `exclude` terms for precision; the curated
  `config/journals.yaml` list only assigns journal **tiers** used to break ranking ties.
- **SQLite is the source of truth** (`data/tracker.db`). CSV exports and the GUI are
  read-layers over it. A `seen` table guarantees a paper is surfaced once.
- **Precision:** each keyword category has `require_all` term groups and `exclude`
  terms; `min_hits` per group (a title hit counts double) kills incidental matches;
  a per-venue diversity cap can stop one journal from monopolising a category; broad
  mega-journals (e.g. IEEE Access, Scientific Reports) can be flagged to pass a
  topical `sieve`.
- **Ranking → top N:** categories rank by match strength, then OpenAlex relevance,
  journal tier, and recency. Capped at `top_n` new papers per category per run
  (default 120; this survey config sets 120–150 to keep the whole corpus).

## Quick start

```bash
pip install -r requirements.txt
python -m src.run                 # refresh (auto window since last refresh)
python -m src.status              # last refreshed / due / overdue
python -m src.run --lookback 30   # force a specific window (days)
python -m src.run --dry-run       # fetch + rank, write nothing
```

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
| `config/categories.yaml` | the four categories: feeds, `require_all`/`exclude` terms, `min_hits`, `top_n`, `sieve_terms` |
| `config/settings.yaml`   | contact email, `lookback_days`, `default_top_n`, `max_per_venue`, repository filter |

Term matching is case-insensitive and word-boundary aware; spaces and hyphens are
interchangeable; a trailing `*` is a prefix match (e.g. `predict*`).

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
python tools/curate.py            # DRY RUN: writes review + snapshot + funnel, changes nothing
python tools/curate.py --apply    # hide the removals (after a timestamped DB backup)
```

Outputs (all under `data/out/`):

| File | What it is |
|------|------------|
| `all_papers.csv`       | regenerable snapshot of **every** paper + its categories + read/star/hidden state |
| `curation_review.csv`  | per-paper keep/remove **decision + reason** (audit every call) |
| `removed_papers.csv`   | every hidden paper with its removal reason |
| `funnel_counts.csv`    | PRISMA-style counts per category (identified → excluded-by-reason → kept) — the numbers for the paper's figure |

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

**Two tabs:**
- **Papers** — category sidebar (collapsible; the priority Non-Contractual Churn bucket starred),
  **Week** filter, **search** (title/author/term), **sort** (rank/date/venue), and a
  **Show** filter (all / unread / starred). Each row has a **read tick** (read papers
  dim), a **star**, a **download** button, and **copy citation**; it shows **why it
  surfaced** (matched-term chips or a "Top-journal pick / arXiv preprint" tag). Click a
  row for the abstract + match detail, or a title to open its DOI.
- **Analytics** — KPI cards (incl. read/starred counts) + charts: papers per category,
  papers per week, source split, top venues, and hot topics (most frequent matched terms).

**Downloads.** The download button fetches the PDF to `data/downloads/` and opens it:
arXiv papers and open-access links are used first (legal); for paywalled DOIs it falls
back to the Sci-Hub mirrors in `settings.yaml` — access to Sci-Hub may be legally
restricted in your jurisdiction, so it's opt-in (clear `scihub_mirrors` to disable).

- **Status banner** (green/amber/red) and **Refresh** button with a **spinner +
  determinate progress bar** ("Fetching … 3/7").
- **Exit** button; **keyboard shortcuts** (`R` refresh, `/` search, `Esc` collapse
  sidebar, `1–9` category); remembers your last tab/category/week/sidebar state.
- All displayed dates are **dd/mm/yyyy**.

## Roadmap

- Package the GUI as a standalone Windows `.exe` (PyInstaller; already in
  `requirements-gui.txt`).
