# Deep Dive & Living Literature Monitor

> **Status:** initialized 2026-08-03. **Stage 0 complete 2026-08-10 — all 5 candidates + 6 appendix
> churn papers read; the novelty defense is confirmed (see [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md)
> §1): no ML customer-forecast paper evaluates by calibration, and both field reviews omit BTYD *and*
> calibration entirely.** Remaining: the OpenAlex forward-citation monitor (§4, not yet run) and the
> optional deep read of the core BTYD rows (low risk). Update the trackers (§8) each pass.
>
> **2026-08-11 — deep-research thread substantially COMPLETE.** Added: the full corpus critique
> ([`corpus_critique.md`](corpus_critique.md)); the OpenAlex live forward-citation monitor (novelty
> confirmed vs the live graph, §8); and bibliography-mining of Ulrich's + Valendin's reference lists
> (6 OpenAlex-verified cites folded into the manuscript, now v2.0.8, 46 cited refs, compiles clean).
> Remaining is optional/gated: a pre-submission re-sweep, tracker-73 GUI mining (needs the app), and
> CORP reliability diagrams (needs per-customer predictions → an experiment re-run).

Two jobs:
1. **One-time deep read** of the current reference library to fill gaps and improve the two manuscripts.
2. **Ongoing OpenAlex monitor** to catch new developments and keep the papers current **until publication**.

Library lives in [`../references/`](../references/) (organized by reading order); new/un-triaged papers
sit in [`../references/candidates/`](../references/candidates/). Manuscript audit: `../manuscript_phase2_audit.md`.

---

## Deep-dive series — one structured doc per key paper (2026-08-11)

Individual Ulrich-style deep-dives, each answering the same questions — **what it does · its novelty ·
how it differs from our paper · how we use it to improve our paper · verdict** — with a per-paper
compare/contrast table. Saved separately:

| Paper | Role vs. our paper | Deep-dive |
|---|---|---|
| **Ulrich (2026)** | concurrent BTYD-aliveness-calibration (complement) | [`ulrich_deep_dive.md`](ulrich_deep_dive.md) |
| **Simon (2025)** | **our source paper** — we adopt her 4 tasks, replace point-error with calibration, overturn timing+cost | [`simon2025_deep_dive.md`](simon2025_deep_dive.md) |
| **Valendin (2022)** | closest ML-vs-BTYD benchmark; the RNN comparator under our lens | [`valendin2022_deep_dive.md`](valendin2022_deep_dive.md) |
| **Wang (2019) ZILN** | our value comparator; the ⚠️ closest to calibration (decile charts) | [`wang2019_deep_dive.md`](wang2019_deep_dive.md) |
| **Platzer (2016) Pareto/GGG** | our structural timing repair (Repair II) | [`platzer2016_deep_dive.md`](platzer2016_deep_dive.md) |
| **Fader et al. (2005) BG/NBD** | the family variant we show is immaterial; we answer their open question | [`fader2005_deep_dive.md`](fader2005_deep_dive.md) |
| **Manzoor (2024)** | field review #1; profit-metric lineage; the calibration reverse-gap | [`manzoor2024_deep_dive.md`](manzoor2024_deep_dive.md) |
| **Imani (2025)** | field review #2 (PRISMA); funnel + taxonomy templates | [`imani2025_deep_dive.md`](imani2025_deep_dive.md) |

*Scope of the series: the papers we **position against** — direct competitors, structural foundations, and
field reviews. The **evaluation-tool** papers (Gneiting ×2, Czado, Guo, Kuleshov, Lilliefors, Friedman,
Koenker, Cranmer) are methods we use in the regime they were designed for — covered in
[`corpus_critique.md`](corpus_critique.md) §4, no standalone deep-dive needed. **Peripheral CLV/churn**
papers (Gupta 2006, Chamberlain 2017, Buckinx 2005, Miguéis 2012, and the recent churn set — De Caigny,
ChurnNet, Boukrouh, Coolwijk, Wachwanakijkul, Mufti, Leoni–Perego, Sci Reports) get the per-paper
takeaway/flaw/coverage treatment in [`corpus_critique.md`](corpus_critique.md) §2–3.*

---

## 1. Deep-dive plan (stages)

### Stage 0 — Triage `candidates/` first (highest ROI)
Read the five new papers, **Ulrich first**, and decide per paper: *promote to a reading list / cite / discard*.
- ⭐ **Ulrich (2026) "Dead Reckoning"** — a direct BTYD successor. Key questions: does it **scoop or
  complement** our contribution? **Does it evaluate by calibration?** (If not, our novelty claim
  survives; if so, cite + distinguish.) Affects positioning of **both** Phase 1 and Phase 2.
- **Imani (2025)** & **TU Dublin (2024)** reviews — mine their bibliographies for anything we're
  missing; use one as the survey citation that fills the unavailable-Colli gap.
- **Leoni & Perego (2022)** thesis, **Sci. Reports (2024)** ensemble-fusion — appendix-tier; skim.

### Stage 1 — Structured read (template §5) → [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md)
One row per paper capturing the six fields in §5. This is the artifact the gap analysis runs on.
**Scaffolded** (2026-08-03) with the full library; structural columns filled, deep-read columns (esp.
the **Calib?** novelty-defense column) pending the read.

### Stage 2 — Gap analysis vs. the manuscript (checklist §6)
Three checks: **novelty defense**, **related-work completeness**, **datasets (incl. F8 India)**.

### Stage 3 — OpenAlex discovery (engine §4)
Forward-citation + reference-mining + topical search, seeded by our core papers, 2023+.

### Stage 4 — Fold into the paper (loop §7)
Findings → manuscript edits → version bump. Each batch lands as a `2.0.x` revision.

---

## 2. Reading priority for the deep read

Ulrich → the two reviews (for their bibliographies) → Buckinx/Miguéis (already cited, confirm framing)
→ Valendin (the ML-vs-BTYD benchmark, §2.2) → the calibration core (confirm we use each correctly) →
the appendix case studies (skim for any that calibrate).

---

## 4. The OpenAlex monitor (the engine)

Uses the same API as `paper-explorer` (`explorer/openalex.py`): `https://api.openalex.org/works`,
polite pool (`mailto`), **2023+ floor**. Three query modes:

| Mode | OpenAlex filter | Purpose |
|---|---|---|
| **Forward citations** | `cites:<WorkID>` | who is building on our core papers *now* |
| **Reference mining** | `cited_by:<WorkID>` | pull a survey/paper's bibliography to find what we miss |
| **Topical search** | `search=<query>` + `type:article`, `from_publication_date` | net for new work not yet citing us |

**Recipe:** resolve each seed DOI/title → OpenAlex work ID (`GET /works/doi:<DOI>`), then run
`cites:` (recent + most-cited) and, for surveys, `cited_by:`. Reconstruct abstracts from the inverted
index. Rank by `cited_by_count` and recency; keep journal articles (`primary_location.source.type:journal`).

### Seed papers to monitor (forward-citation `cites:`)
DOIs are the starting point — if one doesn't resolve, fall back to a title search.

| Paper | DOI / id | Why monitor |
|---|---|---|
| Schmittlein, Morrison & Colombo (1987) Pareto/NBD | `10.1287/mnsc.33.1.1` | new BTYD extensions |
| Fader, Hardie & Lee (2005) BG/NBD | `10.1287/mksc.1040.0098` | variants / applications |
| Platzer & Reutterer (2016) Pareto/GGG | `10.1287/mksc.2015.0963` | timing / GGG follow-ups |
| Abe (2009) HB Pareto/NBD | `10.1287/mksc.1090.0502` | Bayesian estimation |
| Valendin et al. (2022) RNN CBA | `10.1016/j.ijresmar.2022.02.001` | ML-vs-BTYD frontier |
| Wang, Liu & Miao (2019) ZILN | `arXiv:1912.07753` | probabilistic CLV |
| Simon (2025) — our source paper | `10.1007/s11573-025-01237-8` | anyone else extending it |

*General method papers (Gneiting 2007, Kuleshov 2018) have too many citers to forward-monitor —
catch their CBA use via topical search instead.*

### Topical searches (`search=`, 2023+, journals)
- `Pareto/NBD customer base analysis forecast`
- `buy till you die probabilistic customer lifetime value`
- `non-contractual customer churn calibration`
- `customer lifetime value deep learning probabilistic`
- `purchase forecast calibration proper scoring rule`
- `non-contractual customer churn India retail` *(targets the open F8 dataset gap)*

### Triage rule (per hit)
Relevant + 2023+ → download PDF into `../references/candidates/` (name `author_year_topic.pdf`) and add
a row to the candidate tracker (§8). Not relevant → log the id in the monitor log so we don't re-review it.

### Cadence
Monthly while drafting; **and** a fresh sweep immediately before each submission / revision, so the
related work is current at the moment of publishing. Log every run in §8.

---

## 5. Structured-read template (one per paper)

```
Paper:            author, year, venue
We cite it for:   (claim / method)
Does it support:  yes / partly / no  — note
Datasets:         
Evaluation:       point-error? PIT/CRPS/coverage? [FLAG if it evaluates calibration]
Limitations:      (their own admitted gaps)
Chase these refs: (papers it cites that we should read)
Action:           promote to reading list / cite / discard
```

## 6. Gap-analysis checklist (vs. `manuscript_phase2.tex`)

- [x] **Novelty defense** — *done 2026-08-10.* Scanned every ML-CLV/churn paper's evaluation section:
      **none** evaluates ML customer forecasts by calibration → claim is bulletproof (cite the matrix).
      Ulrich is ✅ but BTYD-only (concurrent, cited + distinguished); Wang ZILN ⚠️ (decile charts only).
- [x] **Related work** — Buckinx + Miguéis (v2.0.2); Ulrich + Manzoor + Imani + ChurnNet folded in (v2.0.3).
- [ ] **Datasets / F8** — *reviews mined 2026-08-10: no India non-contractual transaction dataset found.*
      Topical India OpenAlex search (§4) still to run; otherwise a user decision. Open.
- [x] **New methods** — *checked 2026-08-10.* No 2023+ paper benchmarks a *calibration-aware* ML churn/CLV
      model (De Caigny, Coolwijk, Wachwanakijkul, ChurnNet, Mufti, Sci Rep all ❌). ChurnNet (2026)
      corroborates our thesis (conventional ML beats deep) — cited, not added to the comparison set.

## 7. Paper-update loop

Findings → edits, batched by revision:
1. Add citation(s) to `refs_phase2.bib` (or `refs.bib`), verify each against the actual paper.
2. Edit the manuscript (related work / novelty / datasets / methods).
3. Bump the version (`2.0.x`) per [[manuscript-versioning]]; recompile clean (0 undefined refs).
4. Log the batch in `../CHANGELOG.md` per [[changelog-worklog-habit]].
5. Update the trackers below.

---

## 8. Living trackers

### Monitor log
| Date | Mode | Seed/query | New hits | Kept → candidates | Notes |
|---|---|---|---|---|---|
| 2026-08-10 | Library deep-read (Calib? scan) | `candidates/` + `phase2/appendix/` + Valendin/Wang | 0 new must-cite | — | 13 PDFs full-text term-scanned (`scratchpad/scan_lit.py`). **No ML calibration paper found**; both reviews omit BTYD + calibration; F8 India not in review bibliographies. Novelty defense confirmed. |
| 2026-08-11 | OpenAlex forward-citation + topical | 6 seeds (Schmittlein/Fader/Platzer/Abe/Valendin/Simon) + 5 topical, 2023+ (`openalex_monitor.py`) | ~90 works scanned | 0 new must-cite | **Novelty confirmed vs the LIVE literature — 0 works evaluate BTYD-vs-ML by calibration** (only false-positive: a generic AI-marketing paper on "coverage"). No India non-contractual transaction dataset (F8 still open). Optional parallel work noted: a 2026 Hurdle-GBM zero-inflated-CLV **code deposit** (Zenodo, Online Retail~II, no calibration eval) — not a must-cite. |

### Candidate triage
| Paper | In `candidates/` | Read? | Calibrates? | Verdict | Placed |
|---|---|---|---|---|---|
| Ulrich (2026) Dead Reckoning | ✅ | ☑ 2026-08-10 | ✅ (BTYD-only: Brier / CORP reliability / ECE / AUC, out-of-time (v,H) grid) | **cite + distinguish — complement, not competitor** (see below) | Related Work; "first" claim §1; churn §7.7; robustness/seasonality — **✅ folded into manuscript v2.0.3 (2026-08-10)** |
| Imani et al. (2025) review | ✅ | ☑ 2026-08-10 | 🔬 review — **0 calibration, 0 BTYD** in full text; flags profit/XAI/concept-drift gaps; telecom-dominated | **cite as field survey (done)** | Related Work — **✅ folded into manuscript v2.0.3** |
| TU Dublin = Manzoor et al. (2024) review | ✅ | ◑ §VI + Appendix (2026-08-10) | 🔬 review — flags **profit** metrics (MPC/EMP), **not calibration** | **cite as field survey + profit-metric lineage; crosswalk done** → [`gap_crosswalk_manzoor2024.md`](gap_crosswalk_manzoor2024.md) (we patch 4/5 gaps, fill the calibration gap it misses) | Related Work; §profit (V2); Limitations (XAI) — **✅ folded into manuscript v2.0.3 (2026-08-10)** |
| Leoni & Perego (2022) thesis | ✅ | ☑ 2026-08-10 | ❌ point/profit (calibrat=0) | **discard / optional** — PoliMi MSc thesis; non-contractual retail, transactional + private-label features; no new must-cite | — |
| Sci. Reports (2024) ensemble-fusion | ✅ | ☑ 2026-08-10 | ❌ AUC/ROC/F1/accuracy (calibrat=0) | **discard** — telecom ML churn, no calibration | — |

**Ulrich (2026) verdict — full note.** *Dead Reckoning: Counting Your Customers Who Never Say
Goodbye* (Karl T. Ulrich, Wharton; working draft v4, 6 Jul 2026; arXiv:2607.18623; thanks P. Fader;
data from MakerStock, which he co-founded). **Thesis:** summed P(alive) is only *partially
identified* — it is the infinite-horizon limit `A = lim_{H→∞} R_H` of an observable family of
finite-horizon return probabilities `R_H = P(X_H ≥ 1)`. The reported "alive" count is therefore
set-identified: realized returners are a hard lower bound; estimation conventions (structure, prior,
a software-default ridge penalty) pick the point above it (7.6× spread across observationally
interchangeable specs on his panel; 42% from a ridge default alone; 2.4× replicated on CDNOW).
**Central practical claim — the "category error":** summing P(alive) (=`A`) and grading it against a
finite-horizon realized-return outcome overshoots by ~2.25×, but the *same* model's own `R_H`
forecast errs by only ~1.18× — most "miscalibration" of P(alive) is a horizon category error, not a
model failure. **Remedies:** report `R_H` at a stated horizon (free); a *dynamic* recalibration layer
(actuarial Bornhuetter–Ferguson loss-development-triangle logic) that beats a static isotonic map
under drift + emits a drift alarm; report the count as an identified *interval*. **Evaluation:** yes,
he scores calibration — CORP/isotonic reliability diagrams (Dimitriadis–Gneiting–Jordan 2021), Brier
+ decomposition, ECE, aggregate bias, AUC — on an out-of-time (vintage × horizon) grid. His novelty
sentence (p.8): "*no prior work scores the probability calibration of BTYD-implied aliveness
quantities*."

*Why complement, not competitor (four load-bearing distinctions):*
1. **He does not run the ML horse race** — explicitly (Limitations, p.27): "we did not run the horse
   race against discriminative machine learning… the challenger reports no alive count at all
   (Valendin et al. 2022), which under this paper's findings may be a feature." Our central axis
   (**BTYD vs ML by calibration**) is untouched, and he hands us the citation for *why* it matters.
2. **He is churn/aliveness-only.** Value (CLV) and timing are out of scope (p.27: "Revenue and profit
   are out of scope"). We cover counts + value + churn + timing.
3. **The category error validates our design rather than threatening it.** Our churn study already
   scores the finite-horizon `P(x*>0)` (= his `R_H`), and the manuscript already distinguishes it from
   P(alive) `\eqref{eq:palive}` noting "the two coincide only as the horizon grows" — i.e. we
   independently state his identity `A = lim R_H` and sit on the correct side of his category error.
   Cite him to give it a name.
4. **Convergent, independent drift finding.** Our seasonal-conformal result (frozen calendar-blind
   warp does nothing, r stays 0.94; per-window conformal flattens it) is his "a static map… is a bet
   that the past persists." Cite as mutual corroboration; position our per-window conformal as the
   lightweight cousin of his loss-development-triangle layer. His fitting-side seasonality is
   explicitly *left open* (p.27) — our D2 + seasonal-conformal work addresses exactly that axis.

*Residual threat (small, handled by a citation):* his concurrent "first to score BTYD aliveness
calibration" claim overlaps our "first to evaluate … by calibration … across all four targets" on the
**churn** target. Our claim is already scoped to the **ML-vs-BTYD** comparison (§1, l.169–173), which
survives; add `ulrich2026` + one clause ("concurrent and independent work scores the calibration of
BTYD aliveness probabilities; we differ in bringing ML into the comparison and covering value and
timing"). *Do not* claim partial identification — that is his; acknowledge it as the reason the
aliveness **count** is ill-posed and note our finite-horizon framing sidesteps it.

### Open gaps
| Gap | Source | Status |
|---|---|---|
| F8 — India non-contractual dataset | referee review | open (user decision) — **review bibliographies mined 2026-08-10: no India non-contractual transaction dataset (Imani's "India" hits are conference locations); field is telecom/UCI. OpenAlex topical India search still to run.** |
| Novelty defense (no ML calibrates?) | §6 | **RESOLVED 2026-08-10 — all direct competitors + 6 appendix churn papers + both field reviews read; none evaluates ML customer forecasts by calibration. Ulrich (BTYD-only) is the sole ✅; Wang ZILN the only ⚠️ (decile charts). Reviews cite 0 BTYD + 0 calibration. Claim stands — see [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md) §1.** |
| Ulrich positioning | Stage 0 | **resolved 2026-08-10 — complement; cite + distinguish (note above); folded into manuscript v2.0.3** |

---

## 9. Automation (proposed)

**Built 2026-08-11** — `deep_research/openalex_monitor.py` (self-contained, `urllib`, polite pool).
Resolves each seed DOI → OpenAlex work id, pulls 2023+ citing works (most-cited + most-recent) and runs
the §4 topical searches, reconstructs abstracts, and flags `[CALIB]` / `[BTYD]` / `[INDIA]` hits. First
run logged in §8. Re-run before each submission/revision: `python deep_research/openalex_monitor.py`.
(Abe 2009 and Simon 2025 returned no 2023+ citers via DOI on this run — worth a title-search fallback
next pass.)
