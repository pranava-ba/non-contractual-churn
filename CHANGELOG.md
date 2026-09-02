# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

<!-- Dated development log: a running record of what was done each session (newest first),
     alongside the usual Keep-a-Changelog release notes grouped within each day. -->

### 2026-09-01
- **Repo cleanup + organization.** Tidied the working tree without touching any tracked source or
  deleting untracked data. Removed regenerable build artifacts (all `__pycache__/`; the LaTeX
  `.aux/.bbl/.blg/.fdb_latexmk/.fls/.log/.out` cruft in the gitignored `paper/`, keeping `.tex/.pdf`).
  Cleared the root of loose files into logical homes: presentation/first-review materials
  (`First_Review_PPT_bundle.zip`, `PPT_BUILD_GUIDE.md`, `PPT_QA_EXPLAINER.md`, the rubrics `.docx`)
  → new `first_review/`; the two manuscript notes (`manuscript_phase2_audit.md`,
  `manuscript_phase2_review_notes.md`) → `deep_research/`; the 49 MB `references.zip` backup →
  new `archive/` (now gitignored). Root now holds only standard project files.
- **Explainer Q&A docs — answering the doubts `.txt` files → `deep_research/explainers/`.** New
  plain-English, jargon-defined-on-first-use answer docs in the house `PPT_QA_EXPLAINER.md` style,
  one per doubts file: `01_why_paretonbd_is_hard_and_bgnbd_is_easy.md` (Pareto/NBD difficulty,
  difficult likelihood, Gauss hypergeometric functions, closed-form expressions, the BG/NBD thesis
  unpacked; from `doubts_to_be_clarified.txt`); `02_simon2025_abstract_quote_by_quote.md` (every
  flagged Simon-2025 abstract/intro quote, incl. *why timing is "too large to use"* and *should we add
  a fifth forecast?*; from `section_questions.txt`); `03_four_forecasts_and_active_customer.md` (the
  four targets + the unobservable-`P(alive)` → validatable-`x*>0` active-customer redefinition; from
  `goals_and_gaps.txt`); `04_key_terms_glossary.md` (~60-term glossary: definition + plain English +
  example + diagrams, grouped by paper section; from `key_terms.txt`); plus a `README.md` index mapping
  each doubts file to its answer doc. All grounded in the existing deep-dives (Simon 2025, Fader 2005).

### 2026-08-11
- **Deep-dive series — one structured doc per key paper.** Extended the Ulrich-style deep-dive treatment
  (what it does · novelty · how it differs from our paper · how we use it · verdict, each with a
  compare/contrast table and clean LaTeX math) to every paper we position against, saved separately:
  `simon2025_deep_dive.md` (our source paper — we adopt her 4 tasks, replace point-error with calibration,
  overturn timing+cost), `valendin2022_deep_dive.md` (closest ML-vs-BTYD benchmark; its RNN + seasonality
  strength = our limitation), `wang2019_deep_dive.md` (ZILN value comparator; decile-charts ⚠️, not
  distributional), `platzer2016_deep_dive.md` (Pareto/GGG timing repair), `fader2005_deep_dive.md` (BG/NBD
  variant; we answer their rate–dropout open question), `manzoor2024_deep_dive.md` + `imani2025_deep_dive.md`
  (the two field reviews; profit/drift but no calibration, no BTYD). Indexed in `deep_dive.md` (new
  "Deep-dive series" section) and pointed to from `LITERATURE_MATRIX.md` §2. Tool papers stay in
  `corpus_critique.md` §4 (methods we use); peripheral CLV/churn papers in §2–3.
- **Ulrich (2026) full deep-dive → `deep_research/ulrich_deep_dive.md` + v2.0.11.** Section-by-section
  read of all 39 pp (framework/partial-ID, audit method, all empirical results, managerial operating
  system) with a precise map of our five cite sites vs his claims. Two sharpenings landed in §churn:
  (a) our finite-horizon target sits on the *well-identified* part of the model — his §4.3 "dial" shows
  all six specifications agree on $N_{18}\in[2433,3047]$ while $N_\infty$ spans **7.6×** [3654, 27734],
  entirely in the unidentifiable count; (b) our new CORP reliability figure uses the *same*
  reliability-diagram standard (Dimitriadis–Gneiting–Jordan 2021) he adopts. Verdict reinforced:
  complement, not competitor. Memory [[ulrich-dead-reckoning]] updated. Springer clean (49 pp).
- **Tracker: persistent checks + filter-out-once-checked fixed.** Audited the tracker's persistence and
  filtering. Persistence of read/starred/hidden works (verified round-trip through `store.set_state` →
  `data.snapshot`), and the `seen` table correctly prevents re-surfacing. Two real gaps fixed:
  - **`tools/curate.py` now respects manual keeps.** `classify()` never saw the `starred` flag, so
    `curate.py --apply` could auto-hide a paper the user had explicitly starred (kept) — undoing a
    manual check. Now a starred paper is a persistent "keep" (`reason=user_kept`) and is never
    auto-hidden. Precedence: already-hidden > manual keep > auto-classify.
  - **`gui/page.py`: the category badge now counts papers still TO REVIEW** (not hidden *and* not yet
    read), so checking a paper visibly drops it out of the queue; the badge updates live on each tick
    (`renderCats()` in the read handler). "Filter out once checked" is now real, not just a greyed row.
- **Tracker mining: 73 kept papers cross-checked against the bibliography → v2.0.10.** Mined the
  research-paper-tracker's 73 kept papers for must-cites (the explicit ACTION_BOARD Phase-3 item).
  Result persisted to `research-paper-tracker/data/out/cite_triage.csv` (each kept paper × cited? ×
  calib-flag × btyd-flag × verdict): **0 must-cites, 0 calibration papers** other than Ulrich (already
  cited) — novelty confirmed against the tracker too. 68 are recent applications/low-tier reviews; 3
  already cited; 2 optional. Added the one genuinely-relevant parallel-work cite it surfaced —
  `lin2026` (Lin et al. 2026, two-stage Hurdle-GBM for zero-inflated CLV, Applied Sciences 16(13):6550),
  next to our own Hurdle-GBM (§ml). Springer clean (49 pp, 48 refs, 0 undefined).
- **CORP reliability diagrams for churn → v2.0.9.** Implemented the reliability-diagram standard used by
  Ulrich — the isotonic/PAV method of Dimitriadis, Gneiting & Jordan (2021, PNAS; `dimitriadis2021`
  added). `churn.py` gained a `return_curves` flag so `compare_churn` can emit per-customer P(active);
  new `src/make_reliability_data.py` pools those over four held-out splits for four contrasting cohorts
  and fits the CORP (PAV) curve; `make_phase2_inspiration_figures.py:fig_reliability()` draws the 2×2
  fit/break panel (`fig:reliability`, §churn). The picture matches the thesis: BTYD hugs the diagonal on
  Simulated/Grocery (ECE 0.011/0.032) and departs badly on Online Retail~II (0.177, over-stating
  activeness) / Dunnhumby, while the distribution-free ML classifier stays close. Springer recompiles
  clean (49 pp, 47 cited refs, 0 undefined). This closes the "one genuine methodology upgrade" the
  corpus critique had flagged for a future revision.
- **OpenAlex live monitor + Ulrich-bibliography mining → v2.0.8.** Built
  `deep_research/openalex_monitor.py` (self-contained forward-citation + topical sweep) and ran it: of
  ~90 works citing our six seeds (2023+), **0 evaluate BTYD-vs-ML by calibration** — the novelty claim
  now holds against the *live* literature, not just the local library. F8 India still open (only
  contractual SaaS/banking hits). Then mined Ulrich (2026)'s 39-page reference list and added **four
  OpenAlex-verified cites**: `gopalakrishnan2017` (cross-cohort changepoint) and `bachmann2021`
  (time-varying latent attrition) — two *structural* non-stationarity models that now ground the
  seasonality future-work in §Limitations; `jerath2011` (Pareto/NBD dropout generalization, Related
  Work); `vancalster2019` ("calibration = the Achilles heel of predictive analytics", intro
  motivation). Springer recompiles clean (48 pp, 0 undefined). Trackers updated (deep_dive §8/§9,
  LITERATURE_MATRIX §1, corpus_critique §6).
- **Corpus deep-dive critique + v2.0.7 fold-in.** Wrote `deep_research/corpus_critique.md` — a
  paper-by-paper critical read of the whole `references/` library (best takeaway / biggest flaw /
  does our paper cover it), with the deepest treatment of Ulrich (2026) and Simon (2025). It surfaced
  seven improvements; folded the safe/high-value ones into the manuscript (v2.0.7):
  - **A2 — answered a 20-year-old open question.** Our dependence-stress result now explicitly settles
    Fader (2005)'s admitted-open question of whether the purchase–dropout correlation is "good or bad":
    over $\rho\in[-0.6,0.6]$ it is immaterial to calibration (§robust).
  - **A1 — Ulrich's partial-identification interval** acknowledged in §churn (attributed to him; our
    finite-horizon target sidesteps it; interval reporting = future work).
  - **A5 — temperature scaling** (Guo 2017) named among the recalibration-map variants.
  - **A4/A6 — two verified bib entries** added (`ganeson2022` JSMS 12(4):57–68; `faderhardie2010`
    Mktg Sci 29(6):1086–1108); Ganeson cited for the per-customer churn window (§churn), discrete-time
    BTYD named in Limitations. Springer recompiles clean (48 pp, 0 undefined).
  - **A3 investigated, deliberately NOT added.** Computed per-cohort regularity ($k=1/\text{CV}^2$; all
    mildly regular except memoryless Dunnhumby) and a static seasonality score — but the static metric
    *contradicts* the paper's rolling-window seasonality result (ORII 0.31 "low" vs the authoritative
    $r=0.93$), so adding it would introduce inconsistent numbers. Chips stay qualitative.
- **Manuscript v2.0.6 — palette overhaul (no pink) + Valendin-style tables.** Per review feedback:
  - **New color scheme, order blue → green → purple → red → grey, pastel-forward, and the red is a
    *true* red (`#C0392B`), never the old salmon/pink `#EE6677`.** Repointed `paper/phase2_palette.tex`
    and **both** figure scripts; regenerated all 22 figures. The 16 data figures were retinted
    (`sed` on `make_phase2_figures.py`); the 6 diagrams were redrawn.
  - **Diagrams fixed** — pastel fills + dark text + generous box sizing so no text leaks outside its
    box; fixed the broken math in the architecture input box (was wrapped mid-`$…$`) and the taxonomy
    footnote that overlapped the RNN box; calibration-map region labels moved into a clear top band.
  - **Valendin-style tables** — the Data table (`tab:data`) gains a pastel *buying-pattern* descriptor
    chip (sparse / dense / seasonal / zero-infl.) beside the solid FITS/BREAKS/CONTROL regime chip;
    results tables `tab:churn`, `tab:seasstruct`, `tab:clv` gain **green-best / red-worst** cell
    highlighting (`colortbl`), after Valendin (2022) Tables 3/6/8. Springer build recompiles clean
    (47 pp, 0 undefined). Delivered the Springer PDF only, as requested.
- **Manuscript v2.0.5 — reproduced the writing-inspiration figure/table types in our own Tol palette.**
  Turned the `writing_inspiration.md` inspiration items into real elements in the paper (all six
  figures via `src/make_phase2_inspiration_figures.py`, same palette as the existing figures), placed
  in all three builds:
  - **`fig:taxonomy`** — landscape of structural vs ML vs bridges, calibration lens as the axis (opens Related Work).
  - **`fig:prisma`** — literature-sourcing funnel from the *real* tracker counts (185 → 73 kept, 0 calibrate).
  - **`fig:churnwindow`** — finite-horizon active/churn window ($P(x^*\!>\!0)=$ Ulrich's $R_H$) in §churn.
  - **`fig:architecture`** — three inference paths (structural / amortized / ML) from one RFM summary.
  - **`fig:lift`** — per-cohort BTYD-vs-ML churn-ECE advantage (blue = BTYD wins, red = ML wins) in Discussion.
  - **`fig:timeline`** — per-customer event strips (Olist sparse → Dunnhumby dense) in §Data.
  - **`tab:related`** — novelty-scoreboard comparison (11 studies × targets × evaluation × calibration;
    only Ulrich ✅ churn-only and this paper ✅ all-four, in palette green).
  - **`tab:covariate`** — RFM vs RFM+demographics null (PIT–KS/CRPS, paired Wilcoxon $p=0.38/0.13$).
  - All three compile clean (Springer 47 pp, modern 39 pp, elegant 45 pp; 0 undefined refs). `writing_inspiration.md`
    §G audit updated: the A/B/E design candidates are now carried through.
- **Manuscript v2.0.4 — three coordinated design builds on one uniform color scheme.** Produced the paper
  in three looks, all sharing the exact **Paul Tol figure palette** (`#4477AA` blue = structure fits,
  `#EE6677` red = structure breaks, grey = control) so document chrome and figures read as one system:
  - `manuscript_phase2.tex` — **Springer** (sn-jnl, sn-basic), the submission build (44 pp).
  - `manuscript_phase2_modern.tex` — **Modern** (Times body, Helvetica blue section headings with a thin
    accent rule, blue links), article class (37 pp).
  - `manuscript_phase2_elegant.tex` — **Elegant** (Palatino, centered blue small-caps headings + rules),
    article class (41 pp).
  - New shared `paper/phase2_palette.tex` defines the palette + a `\dstag` regime-tag macro, `\input` by
    all three preambles.
  - **Writing-inspiration elements folded in** (all three): a **colored per-dataset regime tag** in the
    Data table (Valendin-style; FITS/BREAKS/CONTROL, blue/red per the calibration-map figure), and an
    **Abbreviations + Notation appendix** (Manzoor Table-6 style). Plus the siloed-literatures sentence
    (reviews omit BTYD + calibration) in Related Work.
  - **Fixed the shared-body drift at its root:** `phase2_body_std.tex` (the body the modern/elegant builds
    `\input`) had fallen behind to a pre-v2.0.2 draft. Added `paper/build_shared_body.py`, which
    regenerates it from the canonical Springer source (translating `\botrule`→`\bottomrule`,
    `\bmhead`→`\subsection*`, dropping `\backmatter`). Single source of truth going forward — re-run after
    any Springer edit. All three compile clean (0 undefined refs).

### 2026-08-10
- **Manuscript v2.0.3 — literature fold-in (Phase 4 batch).** Executed the whole
  `deep_research/ACTION_BOARD.md` §3 Phase-4 batch on `paper/manuscript_phase2.tex` +
  `paper/refs_phase2.bib`; recompiles clean (0 undefined refs, 42 pp, up from 41).
  - **Seven verified bib entries added** — every one confirmed against the PDF title page (in
    `references/`) or the version-of-record, no fabrications: `ulrich2026` (arXiv:2607.18623),
    `manzoor2024` (IEEE Access 12:70434–70463, doi 10.1109/ACCESS.2024.3402092), `imani2025`
    (Mach. Learn. Knowl. Extr. 7(3):105, doi 10.3390/make7030105), `verbraken2013` (IEEE TKDE
    25(5):961–973, doi 10.1109/TKDE.2012.50), `decaigny2024` (Decision Support Systems 181:114217,
    doi 10.1016/j.dss.2024.114217), `boukrouh2025` (IJ-AI 14(1):286–297,
    doi 10.11591/ijai.v14.i1.pp286-297), `churnnet2026` (arXiv:2606.00169). Clears the last of the
    `(to add)` items from `writing_inspiration.md` §F.
  - **Ulrich (2026) cited + distinguished** in four places: the §1 "first" claim (scoped to the
    ML comparison and to the value/timing reach), Related Work (BTYD strand, forward-pointing to the
    churn section), the churn section (our finite-horizon `P(x*>0)` = his identified `R_H`; names his
    horizon "category error" and states we sit on its correct side — *partial identification stays
    attributed to him*), and the seasonality/robustness discussion (our per-window conformal warp = the
    lightweight cousin of his dynamic recalibration layer; frozen warp = his "bet that the past persists").
  - **Field surveys + profit lineage:** Manzoor (2024) + Imani (2025) cited in Related Work as the
    capstone that the field's own syntheses reach profit but stop before calibration; Verbraken (2013)
    EMP/MPC lineage added to the §profit motivation (with Manzoor). ChurnNet (2026) added to the
    non-contractual churn strand (conventional ensembles still beat elaborate deep models — echoes our thesis).
  - **Explainability limitations paragraph** (Manzoor Gap 5): positions structural interpretability +
    Conformalized BTYD as the answer to the performance–interpretability tradeoff, and names
    SHAP-/segmented-interpretability attribution of the distribution-free learner as self-contained
    future work (De Caigny 2024, Boukrouh 2025).
  - Version stamped 2.0.2 → 2.0.3 (source-of-truth header comment + visible draft stamp).
- **Literature deep-read completed — novelty defense confirmed.** Read the remaining candidates and the
  six appendix churn papers (13 PDFs full-text term-scanned via `deep_research/.../scan_lit.py` for
  PIT/CRPS/coverage/ECE/Brier/reliability). **Result: no ML customer-forecasting paper evaluates by
  probability calibration** — the closest, Wang ZILN (2019), uses only qualitative decile charts;
  Valendin (2022)'s 45 "calibration" mentions are all the *estimation-window* sense; Ulrich (2026)
  remains the sole calibration-scoring paper and is BTYD-only. **Killer corroboration:** full-text search
  of both field reviews (Imani 2025 ~240 studies, Manzoor 2024 212 studies) returns **0** hits for
  `Pareto/NBD`/`BTYD`/`Schmittlein`/`Fader` **and 0 for `calibration`** — the churn-ML and CBA/BTYD
  literatures are siloed. Folded that finding into the Related-Work surveys capstone (one sentence). F8
  (India dataset) still open: no India non-contractual transaction dataset in either review bibliography
  (Imani's "India" hits are conference locations). Trackers updated: `LITERATURE_MATRIX.md` §1 scoreboard
  + all Calib? cells, `deep_dive.md` §6/§8, `ACTION_BOARD.md` Phase 3.
- **Research paper tracker — moved into the project, curated, and re-shortcutted.** The
  literature tracker now lives at `research-paper-tracker/` (SQLite `data/tracker.db` = source of
  truth; PyQt6 GUI; OpenAlex + arXiv + Crossref; 4 non-contractual-churn categories). This session:
  - **Findings saved to CSV** — added `tools/curate.py` which snapshots the whole DB to
    `data/out/all_papers.csv` (185 papers) and writes `curation_review.csv` + `funnel_counts.csv`.
  - **Filtered the corpus (for the PRISMA figure):** **185 identified → 73 kept**; 112 excluded
    = 23 prior + **89 newly hidden** (6 non-English, 6 off-topic keyword false positives incl. a
    remote-sensing "RFM-UNet" and a "quantum … CLV" paper, 9 contractual telecom/subscription/OTT/SaaS,
    68 generic RFM+clustering *segmentation*). Reversible: sets `paper_state.hidden=1`, backs up the DB
    (`tracker.db.bak-20260810-230957`) first, audit trail in `removed_papers.csv`; the GUI's
    Show→Hidden + eye button un-hide anything. Per-category kept: ml 44, clv_rfm 28, btyd 9, non_contractual 6.
  - **Fixed the scope leak (keyterms):** `config/categories.yaml` had bare `rfm` in *both* required
    groups of `clv_rfm`, so any RFM paper passed — the source of the segmentation flood. Removed it
    (a clv_rfm paper must now carry a real non-contractual/BTYD/transactional signal) and added a
    shared off-topic `exclude` anchor (remote sensing, quantum, credit scoring, road extraction, …).
    Validated: RFM-UNet now rejected, a real Pareto/NBD paper passes, pure RFM+K-means now fails too.
    Documented the two-stage recall/precision design in the tracker README (also de-finance-ified).
  - **Desktop shortcut refreshed** (`python tools/make_shortcut.py`) — "Paper Tracker.lnk" now points
    at the new folder (`pythonw.exe -m gui`). Daily workflow: Refresh → `curate.py --apply` → skim/star.
- **Created `deep_research/ACTION_BOARD.md` — the single task dashboard.** One doc to open for "what's
  left and how it's progressing," as tables: an at-a-glance phase summary, a done-list, the granular
  action board (Phases 3–6 with Status/Who/Task/link), the two user decisions (F8, venue), and a doc
  map. It's the status/task layer; the detail docs stay the content layer. `ROADMAP.md` now points to it
  up top; memory pointer added. Rolls together this session's Ulrich verdict, Manzoor crosswalk, and
  writing-inspiration items into one go-forward.
- **Deep dive — cross-walked Manzoor et al. (2024) §VI against our gap analysis.** Read §VI (Gap
  Analysis & Recommendations) + Appendix of the TU Dublin review (*A Review on ML Methods for Customer
  Churn Prediction…*, IEEE Access 12). Produced `deep_research/gap_crosswalk_manzoor2024.md` — a large
  synced table mapping their **5 field-level gaps** to our gap IDs. **Verdict:** we patch **4/5** (G2,
  M1–M3, U/V-series), with dataset *recency* (their Gap 1) = our open **F8**; and we **fill a gap the
  review itself omits — probability calibration** (their metric gap stops at profit-awareness / MPC-EMP).
  The one axis they push harder on is **XAI** (their Gap 5), which we answer structurally (Conformalized
  BTYD) rather than with SHAP. Concrete patch surfaced: our **§profit (V2) does not cite the EMP/MPC
  lineage** (Verbraken et al.) — add `verbraken` + `manzoor2024` to `refs_phase2.bib`. Trackers updated
  in `deep_dive.md` / `LITERATURE_MATRIX.md`.
- **Deep dive Stage 0 — read Ulrich (2026) "Dead Reckoning"** (`references/candidates/ulrich_2026_dead_reckoning.pdf`;
  Wharton wp v4, arXiv:2607.18623). The top-priority novelty-risk candidate. **Verdict: complement,
  not competitor — cite + distinguish.** He scores **BTYD aliveness** calibration (CORP reliability /
  Brier / ECE / AUC on an out-of-time (vintage × horizon) grid) and proves the "alive" **count** is
  *partially identified* (`A = lim_{H→∞} R_H`; 7.6× spread across interchangeable specs, 42% from a
  ridge default, 2.4× on CDNOW), with a "category error" (summed P(alive) vs finite-horizon `R_H`)
  accounting for most apparent miscalibration. **But** he explicitly declines the ML horse race (p.27)
  and is churn-only (value + timing out of scope), so our ML-vs-BTYD-across-four-targets claim is
  intact. Three ways it *helps* us: (1) his category error validates our design — our churn study
  already scores the finite-horizon `P(x*>0)` (= his `R_H`) and the manuscript already states his
  identity in words ("the two coincide only as the horizon grows"); (2) his static-map-fails-under-drift
  finding converges with our seasonal-conformal result (independent corroboration); (3) he is a strong,
  authoritative citation for *why* BTYD calibration matters. Full note in
  `deep_research/deep_dive.md` §8; scoreboard updated in `LITERATURE_MATRIX.md` §1.
- **Doc sync.** Reconciled the planning docs to the 2026-08-10 state: `ROADMAP.md` "Current State"
  header refreshed (was 2026-07-29, still listed writing as "what's left") — now records 30/30 gaps
  done + manuscript v2.0.2 drafted & refereed (42 tests) and names the literature deep-read as the live
  workstream with an ordered go-forward; `deep_research/deep_dive.md` and `LITERATURE_MATRIX.md`
  trackers flipped for the Ulrich read (candidates 1/5). See [[docs-directory-convention]].
- **Pending manuscript edits (not yet applied — next session):** add `ulrich2026` to
  `paper/refs_phase2.bib`; cite in Related Work; one distinguishing clause on the §1 "first" claim;
  citation on the churn target (§7.7, our `P(x*>0)` = his `R_H`) and on the seasonality/robustness
  section (our per-window conformal vs his dynamic layer). This lands as manuscript **v2.0.3**.
- **Writing aid — created `deep_research/writing_inspiration.md`.** A curated cross-reference of
  specific figures/tables/structure from the reference library to consult when drafting: Kuleshov
  (2018) calibration plots, Chamberlain (2017) CLV-embedding charts, Cranmer (2020) SBI overview,
  Valendin (2022) RNN figures incl. its **colored per-dataset tag scheme** (flagged as a strong
  adoption candidate for our 7-cohort Data section), Buckinx (2005) predictor/importance tables,
  De Caigny (2024) lit-review table, ChurnNet (2026) hyperparameter table, Boukrouh & Azmani (2025)
  for section flow, Gupta (2006) author bio, Ganeson (2022) churn-window color diagrams. Each mapped to
  its PDF + bib key. Also answered a standing question: the "how many papers screened / how top-N were
  chosen" flowchart is **Imani et al. (2025), Figure 1 (PRISMA Flowchart)** — 837→679→368→240→61.
  - **Expanded (same day)** with review-paper scaffolding (§E): **Manzoor, Qureshi, Kidney & Longo
    (2024)** (ARROW@TU Dublin) Figure 3 (literature-filtering flowchart), Table 6 (abbreviations),
    Table 7 (summary of prior reviews); **Imani et al. (2025)** Figure 12 (taxonomy of churn approaches)
    and Table 1 (conventional-ML summary). Added §F "for our own paper — remember to include": a
    **disclaimer** (data/AI-use/COI/funding), **complete verified references** (clear the `(to add)` bib
    items), and an **appendix** (derivations, diagnostics, grids, abbreviations list). Mirrored into the
    ROADMAP author-side pre-submission step.

### 2026-08-03
- **Deep dive — created `deep_research/LITERATURE_MATRIX.md`** (the synthesis grid `deep_dive.md`
  feeds). Scaffolded with the whole library (~35 substantive papers) grouped by theme; structural
  columns filled, deep-read columns provisional (marked †) or ❓. Features: a **novelty-defense
  scoreboard** built around a **Calib?** column (does each paper evaluate by calibration — the crux of
  our novelty claim), a datasets index (feeds F8), reading-progress + to-chase trackers, priority
  flags, reading-order cross-links, and a mermaid citation-lineage diagram (Ulrich flagged as the
  competitor to check). Linked both ways with `deep_dive.md`.
- **Deep dive — created `deep_research/deep_dive.md`** (living literature monitor). Encodes the
  one-time deep-read plan (Stages 0–4, Ulrich first) **and** an ongoing OpenAlex process to keep the
  paper current until publishing: three query modes (forward `cites:`, reference-mining `cited_by:`,
  topical `search=`) matching `paper-explorer/explorer/openalex.py`, a seed-paper list (Schmittlein,
  Fader, Platzer, Abe, Valendin, Wang, Simon) with DOIs, topical queries (incl. one targeting the F8
  India dataset), triage rules → `references/candidates/`, a monthly + pre-submission cadence, and
  living trackers. Proposes a `deep_research/openalex_monitor.py` to automate the sweep (not built yet).
- **Paper — `manuscript_phase2.tex` revised to v2.0.2** (compiles clean: 0 undefined refs/citations, 41 pp).
  Applied this session's validated work:
  - **§7.12 seasonality rewritten.** Replaced the "a structural seasonal model is the cleaner long-run
    fix" claim (which the full test did *not* support on real data) with the actual scoped result +
    new **Table `tab:seasstruct`**: the structural seasonal rate term halves miscalibration on a
    controlled sim (PIT-KS 0.090→0.030, OOS β removes the bias) but adds nothing on the real cohorts,
    where conformal recalibration alone suffices (Online Retail II 0.082→0.021, β≈0.5). See
    [[seasonality-finding]].
  - **Related work + bib:** added Buckinx & Van den Poel (2005) and Miguéis et al. (2012) — the classic
    non-contractual churn-classification lineage (closes audit §3.4) — to §2 and `refs_phase2.bib`.
  - **Audit fixes:** Table 14 (`tab:mltiming`) caption now explains the split/seed shift vs. Table 13
    (§1.1); §5 clarifies table p-values are raw paired-Wilcoxon unless noted (§2.4); demographic-null
    claim scope-qualified to the one cohort with demographics (§2.3).
  - **Version:** 2.0.1 → 2.0.2 (top-of-file comment + visible draft stamp).
  - **Deferred:** figures untouched — a **uniform color theme across all figures** is flagged for a
    future version, not this one (see [[uniform-figure-theme]]).
- **References — added Phase 2 reading-order companion.** New `references/READING_ORDER_PHASE2.md`:
  a staged (easy→hard) path through the ML / ML-vs-BTYD literature Phase 2 benchmarks against,
  modelled on the existing Phase 1 `READING_ORDER.md` and cross-linked both ways (added a *Sequel*
  pointer to the Phase 1 doc's footer).
  - **Recommended bib additions flagged** (not yet in `paper/refs_phase2.bib`): Buckinx & Van den
    Poel (2005, EJOR — canonical non-contractual ML churn), Migueis et al. (2012, partial churn),
    Colli et al. (2025, systematic review). These fill the Related-Work gap; the phase2 bib currently
    holds the *methods* spine (ZILN, GBM, quantile reg, calibration) but not the churn-ML lineage.
  - **Flagged for verification before citing:** recent web-sourced items (ChurnNet arXiv:2606.00169,
    rolling-window car-wash arXiv:2606.06776, Coolwijk ViT, Jarumaneeroj, Boukrouh & Azmani,
    De Caigny 2024) — IDs/author lists unverified; quarantined in an appendix, not the main list.
  - Relates to open review item **F8** (Indian dataset) — the field-scoping pass also surfaced
    candidate India non-contractual datasets (Kaggle "Ecommerce Customer Churn Analysis and
    Prediction", derived-label Indian e-commerce sets).
- **References — full library reorganised into reading-order subfolders + new papers identified.**
  The user populated `references/` with the actual PDF texts (~30 files, many with publisher/arXiv
  slug names). Identified every one (extracted titles for the opaque ones), renamed to
  `NN_author_year_topic` (NN = reading-order item #), and filed into `phase1/`, `phase2/`,
  `phase2/appendix/`, and `candidates/`. Updated `READING_ORDER.md` (📄 paths → `phase1/`),
  `READING_ORDER_PHASE2.md` (added 📄 paths for items 3–19, de-flagged + identified all six appendix
  case studies, added a "New in the library" section), and `README.md` (rewritten as the folder map).
  - **New papers not previously in the lists** (now in `candidates/`, for the deep dive): ⭐ **Ulrich
    (2026) "Dead Reckoning: Counting Your Customers Who Never Say Goodbye"** (Wharton working draft — a
    direct BTYD successor, non-contractual; potential positioning impact on BOTH phases); Imani et al.
    (2025) and TU Dublin (2024) systematic reviews (concrete stand-ins for the unavailable Colli survey);
    Leoni & Perego (2022) partial-defection MSc thesis; Scientific Reports (2024) ensemble-fusion churn.
  - **Appendix case studies now identified** (were "verify before citing"): De Caigny, De Bock &
    Verboven (2024, DSS); Wachwanakijkul et al. (2024, car-sharing); Boukrouh & Azmani (2025, IJ-AI);
    Coolwijk et al. (2024, ViT); ChurnNet (2026); Mufti et al. (2026, rolling-window). Next phase =
    deep-dive lit review (see plan).
- **Research spike — minimal seasonal extension (review item §2.1 / `sec:robust`).** New standalone
  runner `src/run_seasonal_structural.py`: scales each customer's forecast-window Pareto/NBD rate by a
  single calendar-derived seasonal multiplier (`Poisson(λ·L·m)`), fitted `(λ,μ,τ)` untouched, evaluated
  on the same Online Retail II rolling windows as `run_seasonal_conformal.py`. Findings:
  - Sanity: raw stationary reproduces the paper's bias (r=+0.93 vs +0.94).
  - The full multiplier (m = aggregate seasonal intensity) **over-corrects**: directional bias flips
    +0.93 → −0.78 (oracle −0.76 too), because market-volume seasonality overstates the cohort's
    repeat-rate seasonality (acquisition is in the volume, not the cohort's rate).
  - A **one-parameter damped loading** `m = 1 + β(intensity−1)`, β≈0.58, cuts the calendar-conditional
    bias to **r=+0.16** — beating the per-window conformal residual (+0.43, `tab:seasconf`) that §2.1
    flagged — and improves mean PIT-KS **0.081 → 0.067** (matches the oracle), deployable from the
    calendar shape alone.
  - Caveats before it's paper-ready: β is in-sample on 9 windows here (full model must estimate it
    out-of-sample, ideally from the cohort's own repeat-purchase seasonality); a residual *level* bias
    remains (loaded ratios 0.69–0.90, all <1) that a level/conformal recalibration would close; tested
    only on Online Retail II. Verdict: the structural lever works — worth promoting to a fuller model.
- **Research — FULL seasonal test (follows the minimal spike above).** New `src/run_seasonal_full.py`:
  repeat-purchase seasonal profile (drops acquisition volume), conformal LEVEL-recal stack, and an
  out-of-sample loading β (leave-one-window-out), validated on Online Retail II + Grocery + a
  controlled simulated DGP with KNOWN amplitude (A=0.6). Rigorous baseline added: conformal
  recalibration *alone* (β=0), the bar the structural term must clear. Findings (PIT-KS = the metric):
  - **Controlled sim (ground truth): the structural seasonal term works.** PIT-KS 0.090 → 0.043
    (seasonal) → 0.030 (seasonal+conformal), both beating conformal-alone (0.049); OOS β≈1.25 drives
    the directional bias +0.95 → **+0.02**. Mechanism confirmed where seasonality is the whole story.
  - **Real headline case (Online Retail II): conformal recal ALONE already solves it** —
    PIT-KS 0.082 → **0.021**, *better* than seasonal+conformal (0.026). The structural term does NOT
    add value here because real non-stationarity is only ~half calendar-seasonal (OOS β≈0.50), so a
    pure seasonal multiplier over-corrects (repeat-profile too: r −0.72). 
  - **Grocery (mild): nothing to fix**; seasonal term is a slight, harmless over-fit (0.047→0.052).
  - **Metric caveat:** §7.12's directional-r is fragile once the level is recalibrated (reads high,
    +0.79 on OR-II, on ±0.05 residuals while PIT-KS is 0.021) — report PIT-KS, not r.
  - **Verdict:** the minimal spike's promise was partly a metric artifact. A structural seasonal term
    is real and validated on dominantly-seasonal data, but on the paper's own real cohorts the
    conformal recalibration it ALREADY has is sufficient/better. Recommendation for §7.12: report this
    as a scoped result (built + validated on controlled data; conformal suffices on the real cohorts;
    structure earns its keep only when seasonality dominates) rather than claiming structure is "the
    cleaner fix." Both the minimal (`run_seasonal_structural.py`) and full (`run_seasonal_full.py`)
    runners are kept.
- **Paper — full audit of `manuscript_phase2_review_notes.md` against `manuscript_phase2.tex`**
  (v2.0.1) → written up in `manuscript_phase2_audit.md`. Every numeric claim traced to source and
  **confirmed** (§1.1 timing 5.33/9.50 etc.; §1.2/1.3 PIT-KS 0.169/0.166/0.164 and 0.211/0.207/0.210/
  0.212; §2.1 seasonality r +0.94→+0.43). Resolved the notes' float numbering (their "Table 2" =
  `tab:counts`, the count PIT-KS table my first grep missed; "Section 7.x" = Results subsections).
  Findings that change the fix list: 4.1 (novelty hedge already present; cited as §2 but it's §1) and
  4.2 (garbled `Rb`/`λˆi`/`T*` are PDF-extraction artifacts) need **no** manuscript change; 1.2/1.3 are
  **partly pre-addressed** by the `tab:counts` caption; 3.3 delta is already credited to `[phase1]`.
  Real remaining work: 1.1 footnote, 2.1 seasonality decision, 2.2 Valendin, 2.3/2.4 scope+correction,
  3.4 add Buckinx & Miguéis. These land as the v2.0.2 revision.
- **Manuscripts — introduced version numbers (new convention).** From now, each manuscript carries a
  phase-based semantic version (major = phase: Phase 1 → 1.x.x, Phase 2 → 2.x.x, …), bumped every
  revision pass. Placement is twofold: a `%% Version:` comment at the top of the `.tex` (source of
  truth) and a visible `Draft vX.Y.Z` stamp after `\maketitle`, wrapped in strip-before-submission
  markers. **`paper/manuscript_phase2.tex` stamped at v2.0.1** (next revision → 2.0.2). The `_modern`/
  `_elegant` variants and the Phase 1 manuscript are not yet stamped.
- **References — folder cleanup + reorganization.**
  - **Verified** the three recommended Phase 2 additions and finalized their citations in the reading
    order (no longer provisional): Buckinx & Van den Poel (2005) *EJOR* 164(1):252–268; Miguéis et al.
    (2012) *Expert Systems with Applications* 39(12):11250–11256; Colli et al. (2025, under review).
    Also confirmed **ChurnNet arXiv:2606.00169** resolves to a real preprint (de-flagged); remaining
    web-sourced case studies stay quarantined in the appendix with per-item verification marks.
  - **Renamed** the six local PDFs from publisher slugs to an `author_year_topic` scheme
    (e.g. `s11573-025-01237-8.pdf` → `simon_2025_generalised_comparison.pdf`,
    `Vol.12.No.04.04.pdf` → `ganeson_2022_churn_window.pdf`); updated all 📄 links in
    `READING_ORDER.md` accordingly. Only that file referenced the filenames (ROADMAP / gap-analysis
    cite the DOI, not the file).
  - **Removed** redundant `references.txt` (its two URLs are already items 1–2 of the Phase 1 list).
  - **Added** `references/README.md` — a folder index (which list to read, PDF table, naming
    conventions). Note: the whole `references/` folder is still git-**untracked** (moved in from repo
    root; the root copies show as deleted) — commit when ready.

### 2026-08-02
- **Paper — proofread + refresh pass on `paper/manuscript_phase2.tex` (40 pp).**
  - **Fixed:** the Introduction's Pareto/GGG timing-reduction figure was stale ("a fifth to a third"),
    left over from before the abstract was rescoped. Corrected to "roughly a sixth to a quarter" to
    match the abstract and the actual table numbers (MdAE reductions of 17.6%/23.4%/28.1% on
    Sim-k2/Grocery/Sim-k3 → a sixth–quarter, not a fifth–third).
  - **Verified (no change needed):** the abstract is accurate and current — every headline number
    checked against `results/*_summary.csv` (conformal PIT-KS repairs match exactly: CDNow
    0.056→0.034, Dunnhumby 0.164→0.097, Online Retail II 0.212→0.044, Grocery 0.036→0.036 p=0.978,
    Ta-Feng 0.072→0.027); all four batch-4 referee items (amortized break-even ≈150 fits, covariate
    null on counts & churn, conformal-on-ML table, 50-cohort amortized set) are reflected in the text.
  - Compile is clean: 0 undefined references, 0 undefined citations; PDF rebuilt (40 pp). Remaining
    known cosmetics only (one 6 pt overfull hbox in the decision-rule table; hyperref bookmark-level
    notices). Only open review item is still F8 (Indian dataset, needs sourcing).

### 2026-08-01
- **Paper — referee-review response, batch 4 (40 pp): the remaining follow-ups (F3–F6).** With F8
  (Indian dataset, needs sourcing) the only open item, the full review is now addressed.
  - **F3 amortized break-even** (§cost): training 98s; per-fit saving over MCMC ~0.6s at N=8000 (the
    shared individual augmentation dominates), so break-even ≈150 fits — worthwhile at scale/frequency,
    not for a one-off. Stated honestly rather than oversold.
  - **F4 covariate null → counts & churn** (`run_covariate_targets.py`, §clv): on the count target
    demographics add nothing over RFM (PIT-KS 0.207 vs 0.205, p=0.38), so the null generalises; the
    churn target is degenerate on the demo subset (100% active) and reported as such.
  - **F5 full conformal-on-ML table** (`tab:conformalml`): promoted the M3 spot-check — recalibration
    repairs the parametric Poisson-GBM (Dunnhumby 0.241→0.115) and leaves the distribution-free
    Quantile-GBM untouched. Closes M3.
  - **F6 amortized held-out set 25→50** (`run_amortized_check.py`): TOST still EQUIVALENT (CRPS +0.35%
    [−0.12,+0.82]); refreshed Table 4, the TOST table, §estinv prose, and the figure.
  - Compiles clean; 42 tests pass; variants regenerated. **All review items closed except F8.**
- **Paper — referee-review response, batch 3 (39 pp): follow-up experiments (F1, F2, F7).**
  - **F1 — extend timing to dense cohorts (`run_timing_dense.py`): negative, reported honestly.**
    Pareto/GGG ties/loses on Dunnhumby, Online Retail II, Ta-Feng — estimated regularity is only mild
    (k̂≈1.5; "dense" ≠ "regular"), and Ta-Feng is pathological (likely a short-horizon artifact). Did
    NOT force it into a table; added a one-line qualifier to §timing that the advantage is
    regularity-dependent, which sharpens the claim and pre-empts the exact test.
  - **F2 — stack the repairs (`run_timing_stack.py`): strong positive.** Conformal recalibration of the
    Pareto/GGG wait-time predictive improves MdAE and CRPS on all three cohorts and **rescues CDNow's
    archetypal "too inaccurate to use" case (median error 104→10 weeks)**. Added as §"Stacking the two
    repairs" (`tab:stack`): the model-agnostic repair generalises to the timing target and the two
    repairs are complementary. Together F1+F2 tell a coherent story — the structural fix is limited to
    regular processes, the post-hoc fix is general.
  - **F7 — Cranmer et al. (2020) citation** (verified PNAS 117(48):30055–30062) added to
    `refs_phase2.bib`; §amortized now situates the estimator in the simulation-based-inference paradigm.
  - Compiles clean; 42 tests pass; variants regenerated. (F3–F6 and F8 remain; F8 needs data sourcing.)
- **Paper — referee-review response, batch 2 (38 pp): the sharpest test + the §8→§7 promotions.**
  - **D1, the seasonal-conformal test (the referee's sharpest follow-up).** `src/run_seasonal_conformal.py`
    (`results/seasonal_conformal_summary.csv`), written into §robust as `tab:seasconf`. A genuinely
    nuanced, publishable result confirming *both* readings: rolling the cut-point on Online Retail II,
    the raw seasonal bias (r=+0.94) is **largely repaired by per-window conformal** — the paper's
    procedure, learned on same-season held-out data (r→+0.43, forecast ratios pulled to 0.88–1.05) —
    but a **frozen, calendar-blind warp does nothing** (r stays +0.94). Lesson: recalibration works but
    must be refreshed each period; the residual (r=0.43≠0) motivates a time-aware model as the clean
    long-run fix. Directly answers the "static correction can't track calendar" concern.
  - **C1 profit (V2) promoted §8→§7** (`sec:profit`, `tab:profit`): economics stated (margin M=1,
    break-even c/M) with a sensitivity sweep over three contact costs; the pattern mirrors the
    calibration map (structure's targeting edge is largest where its assumptions hold and the budget is
    tight; the learner/heuristic pull ahead on the dense miscalibrated cohort).
  - **C2 tenure (F3) promoted §8→§7** (`sec:tenure`): geometric estimator named, 95% customer-bootstrap
    CIs added (`_tenure_from_counts` + bootstrap in `run_rolling_study.py`; CDNow 1.76 [1.64,1.82],
    Grocery 2.52 [2.34,2.80]).
  - **B1 (Table-2 discrepancy) resolved:** root cause is that Table 2 scores the 30% held-out test
    split (KS floor ~1/√n reads higher on smaller samples), not a stale pipeline; added a footnote.
  - §8.2 Managerial trimmed to reference the new §7 results instead of asserting raw numbers. Compiles
    clean; 41 tests pass; variants regenerated.
- **Paper — referee-review response, batch 1 (36 pp).** Acted on a detailed referee-style review;
  tracker at `deep_research/referee_review_response.md`. Closed both blockers and all seven smaller
  catches; the larger items (Table-2 reconciliation, §8→§7 promotions, seasonal-conformal test,
  follow-up experiments) are logged and pending.
  - **Blocker A1 (M2 self-contradiction).** Promoted the ML-hazard timing result out of the
    contradictory §8.4 sentence into a new §7.9 subsection + table (`tab:mltiming`, from
    `ml_timing_summary.csv`): Pareto/GGG beats the ML survival model on every regular-purchasing cohort
    (Grocery 3.38 vs 4.21, Sim-k3 3.89 vs 6.07, CDNow 101.9 vs 107.6) — strengthens the timing
    contribution (GGG beats even a purpose-built ML competitor, not just the exponential baseline).
    Rewrote §8.4 to reference the reported result.
  - **Blocker A2 (companion study uncited).** Added a `phase1` working-paper self-citation to
    `refs_phase2.bib` and cited it at both Intro mentions.
  - **E2 (R-hat).** Ran `convergence.py`; added the honest diagnostic to Appendix A — rate params
    converge (R-hat ≤1.02), the dropout (s,β) mix slowly (CDNow R-hat ≤1.09, ESS ≈62, a known
    non-identifiability), but forecast scores are chain-reproducible to MC noise (CRPS 0.384±0.0004).
  - **E4 (Ta-Feng).** Added Ta-Feng to `run_topa_study.py` and `tab:topa` (BTYD 0.53 vs GBM 0.55 —
    within noise; honestly softened the "best on every cohort" prose); noted Olist's exclusion (1.6%
    active → degenerate top decile).
  - **Small catches:** abstract timing reduction rescoped to "a sixth to a quarter" (was "a fifth to a
    third"); Laplace "cheap" reconciled with its Table-14 cost; a BTYD-vs-Pareto/NBD terminology
    definition added to §Models; Table-4 real-cohort seed count noted; eq.-(3) vs posterior-predictive
    P(x*>0) clarified in the churn section.
  - Compiles clean (no undefined refs/citations); 40 tests pass; variants regenerated.
- **Paper — added the Valendin et al. (2022) citation (verified, not fabricated).** Web-verified the
  bibliographic details against two authoritative sources (WU Vienna institutional repository +
  ScienceDirect metadata): Valendin, Reutterer, Platzer & Kalcher, "Customer Base Analysis with
  Recurrent Neural Networks," *Int. J. Research in Marketing* 39(4):988–1018, 2022, DOI
  10.1016/j.ijresmar.2022.02.007. Added the entry to `paper/refs_phase2.bib` and cited it in three
  places: the ML paragraph of Related Work (positioned as the RNN-based CBA flagship reporting
  point-error accuracy gains over Pareto/NBD), the "first" contribution claim (so the prior ML-CBA
  work is named), and Limitations (a recurrent model on the raw event stream is the natural next
  comparator under the calibration lens). Closes the last referee-objection flag; the paper no longer
  omits the field's most prominent ML-for-CBA reference. Compiles clean (35 pp), citation resolves in
  the bibliography.
- **Paper — two new evidence pieces (35 pp): real-data seasonality + explicit Top-A%.** These add
  genuine new evidence with little/no new data, closing the two items previously left as the user's call.
  - **Real-data seasonality** (`src/run_seasonality_real.py`, `results/seasonality_real_summary.csv`,
    `fig_p2_seasonality_real.png`). Moves the headline limitation from simulation-only to demonstrated
    in the wild: rolling the calibration cut-point on Online Retail II (UK gift retailer, Christmas
    peak) so the forecast window sweeps the calendar, the model's forecast ratio (realised/predicted)
    tracks the window's seasonal intensity at **r=+0.93** — busy windows under-forecast (ratio 1.29 in
    the pre-Christmas quarter), quiet windows over-forecast, PIT-KS up to 0.17 in mismatched windows vs
    0.03 when aligned. Grocery (milder) shows r=+0.91. Added a paragraph + figure to §robust.
  - **Explicit Top-A% identification** (`src/run_topa_study.py`, `results/topa_study_summary.csv`).
    Restores Simon's task 3 as its own result (§topa, `tab:topa`). BTYD ranks best-or-tied on every
    cohort and beats the heuristic throughout — and, the useful nuance, **it does so even on the dense
    cohorts where its intervals miscalibrate** (Online Retail II hit 0.60/capture 0.82 despite PIT-KS
    0.21; Dunnhumby 0.71/0.90 despite 0.17). Identification depends on the *ordering*, which the count
    assumption leaves intact even where it corrupts the *intervals* — so a firm can trust BTYD to rank
    and target, and needs the conformal repair only for the intervals.
  - New figure `fig_seasonality_real` in `make_phase2_figures.py`; two smoke tests (40 pass); compiles
    clean; variants regenerated.
- **Referee-defence Tier 1 — TOST equivalence delivered (objection 1).** The methods section promised
  two-one-sided-tests for every "equivalent/immaterial" claim, but the results only showed
  non-significant Wilcoxon — a half-kept promise a careful referee would catch. Now delivered:
  - **`src/tost.py`** computes TOST against pre-declared margins (relative CRPS $\pm5\%$, absolute
    PIT-KS $\pm0.02$; equivalent iff the 90% CI of the paired difference lies inside the margin) for
    all three claims, from per-seed data (`main_results.csv`, `bgnbd_study_raw.csv`, and a new
    `amortized_heldout_raw.csv`). **All three come out EQUIVALENT** (`results/tost_summary.csv`):
    MLE≈MCMC (CRPS −0.33% [−0.65,−0.01]), Pareto/NBD≈BG/NBD (−0.23% [−0.37,−0.09]), Amortized≈MCMC
    (+0.46% [−0.13,+1.05]); PIT-KS within margin for all; every TOST p<0.001.
  - **`src/run_amortized_check.py`** now also saves per-cohort paired values (`amortized_heldout_raw.csv`)
    so the amortized equivalence is reproducible; re-run identically (4000-cohort training, 25 held-out).
  - **Manuscript:** added Table `tab:tost` to §estinv with a lead-in that the equivalences are positive
    (TOST), not absence-of-evidence; cross-referenced from the amortized paragraph and the variant
    section. Compiles clean (33 pp). Smoke test added (`tests/test_phase2.py`, 37 pass).
- **Referee-defence Tier 1/2 — objections 3, 4, 9 closed.** The remaining deferred items are done;
  the full objection list is now addressed except the two flagged as the user's call (real-data
  seasonality / explicit Top-A%, and the Valendin citation).
  - **Objection 3 (info-asymmetry).** Added a fairness paragraph to §ml: the supervised-ML vs
    unsupervised-BTYD asymmetry *favours ML*, yet structure still wins on sparse data (so the finding is
    conservative), and the like-for-like supervised comparison already exists (Conformalized BTYD uses a
    held-out label split too). Framing only — no new run.
  - **Objection 4 (cost implementation-dependence).** Added a single-start MLE route to
    `run_cost_benchmark.py` and re-ran. Result *strengthens* the claim: even single-start MLE (9.2 s at
    N=8000) is slower than MCMC (2.6 s) because Nelder-Mead on the hypergeometric likelihood is
    intrinsically costly — so both MLE variants and Laplace are dominated, not just the hardened one.
    Updated `tab:cost` (two MLE rows), the prose (18.8 s multistart / 9.2 s single-start), the caption,
    and the figure; kept the honest caveat that a compiled/gradient optimiser would be faster and the
    robust claim is only "MCMC is not the costly route."
  - **Objection 9 (ML under-tuning).** New `src/run_ml_tuning.py`: across shallow/default/deep/slow GBM
    settings the PIT-KS moves by ≤0.017, far less than the BTYD-vs-ML gap — on Online Retail II every
    Quantile-GBM setting is 0.030–0.045 vs BTYD 0.210; on Simulated every setting stays above BTYD 0.027.
    Verdict is tuning-invariant. Added a note to §mechanism (`results/ml_tuning_summary.csv`).
  - Manuscript 34 pp, compiles clean; two smoke tests added (`tests/test_phase2.py`, 38 pass); variants
    regenerated.
- **Paper — referee-objection review + low-effort defence pass (33 pp).** Reviewed the manuscript as a
  hostile-but-fair referee and catalogued the likely objections in three tiers (Tier 1, decisive:
  equivalence claims need TOST not non-significance; density confound across six heterogeneous cohorts;
  supervised-ML vs unsupervised-BTYD information asymmetry; cost result is implementation-dependent.
  Tier 2: multiple comparisons; novelty vs the Phase-1 companion + "first" claims; "variant immaterial"
  near-circular; conformal not algorithmically novel; ML under-tuned; single simulated DGP. Tier 3:
  PIT-KS threshold; window choice; Olist degeneracy; single spend model; scope/depth).
  - **Executed the low-effort defences** (framing that marshals existing results at the point of claim;
    no new experiments):
    - **Identification strategy made explicit** in §mechanism (objection 2): the causal claim rests on
      the simulation (varies the assumption, nothing else) and the mechanism test (holds data fixed,
      varies only the forecaster's distributional assumption); the six-cohort activity gradient
      *corroborates* rather than establishes.
    - **"First" claim rescoped** to attach the novelty to the *calibration lens* (vs point error), with
      prior ML-vs-BTYD point-error work cited (`chamberlain2017`, `wang2019`); the Phase-1 delineation
      was already strong (companion varied the estimator; this paper varies the model + adds dimensions).
    - **"Variant immaterial" reframed** (objection 7) as a falsifiable consistency check: variants
      *sharing* the count assumption calibrate alike, and Pareto/GGG (which changes it) is the predicted
      exception — not a near-tautology.
    - **Conformal contribution repositioned** (objection 8): the map is standard (`kuleshov2018`); the
      contribution is the diagnosis of *when* to recalibrate + the finding it repairs BTYD and ML alike.
    - **Pointers added at point of claim**: the simulated control is one draw of a broader grid
      (objection 10); the calibrated/broken split uses the bootstrap-adjusted PIT-KS null (objection 11);
      Holm-Bonferroni leaves the headline effects significant while equivalence claims don't rely on it
      (objection 5); window choice is robust per the rolling walk-forward (objection 12).
  - **Deferred (Tier 1/2, need new work):** port TOST to the equivalence tables (the methods already
    promise it — results must show it); an info-asymmetry robustness check; a standard-tool cost
    benchmark; an ML hyperparameter-sensitivity check. **Flagged for the user:** Valendin et al. (2022,
    IJRM) — the RNN customer-base paper — is missing from Related Work; its absence is itself a likely
    objection, but I did not add a bib entry unilaterally (verify details first).
  - Recompiles clean (no undefined refs/citations); variants regenerated.
- **Paper — folded the reconciliation findings into the Phase-2 manuscript** (`paper/manuscript_phase2.tex`;
  the `paper/` tree is git-ignored, so this is noted here but not bundled). Compiles clean via `latexmk`
  (**29 pp**, up from 27; no undefined refs/citations; the four new labels resolve). Additions, all with
  exact numbers from `results/*_summary.csv`:
  - **New §"The cost of a calibrated forecast"** (gap V3): the cost–accuracy frontier
    (`fig_p2_cost.png` + a Pareto table). Headline: at N=8000 the Gibbs MCMC (2.6s) is ~6× faster than
    the hardened multistart MLE (16.4s) and wins CRPS, so MLE-plug-in and Laplace are *dominated* —
    refutes Simon's "MCMC is expensive." Honestly caveated as implementation wall-clock.
  - **New §"Robustness of the diagnosis"** (gaps D1, G4, D3, F1, D2): a four-axis stress table
    converting the old "non-stationarity/dependence remain open" limitation into results — robust to
    high frequency / N→50k, to λ–μ dependence, to 30% transaction loss, and across rolling cut-points;
    **breaks only under seasonality** (PIT-KS 0.02→0.12), now stated as the one axis the count
    assumption can't absorb.
  - **Strengthened §"…invariant to the estimation method"** (gaps E1, E4, E5, T3, F2): extended from
    3 to **five estimation routes** (added HMC + Laplace) plus a prior-sensitivity table (E5) and the
    noise-floor argument (T3: the estimable share of error is ≈0) and the aggregation result (F2).
  - **Managerial** gained the profit result (V2: 88% vs 66% of oracle on-turf); **abstract**,
    **conclusion**, and **limitations** updated for the cost frontier and the seasonality boundary;
    the ML-hazard timing result (M2: GGG still wins) added to future work.
  - `src/make_phase2_variants.py` re-run so `phase2_body_std.tex` + the elegant/modern wrappers stay
    in sync with the updated body.
  - **Second folding pass (31 pp).** Softened the cost-frontier claim to the robust version —
    lead with "MCMC is on the frontier / not the expensive option," with the "MLE/Laplace dominated"
    observation demoted to an implementation-specific parenthetical (abstract, §cost, conclusion,
    table caption). Folded the remaining gaps: **new Appendix "The zero-inflation asymmetry and the
    estimation noise floor"** (T1 median-vs-mean derivation + T3 decomposition table, cross-linked
    from §estinv); **F3** segment-tenure into Managerial (top-decile tenure ≈2 quarters); **F4**
    active-customer definition sensitivity into the churn section (P(alive) over-counts by ~12 pts);
    **G5** CLV discounting into the monetary section (rescales value, doesn't reshuffle Top-A%);
    **M3** conformal-on-ML into Repair I (same recalibration repairs the parametric ML forecaster).
    Recompiles clean; variants regenerated. Every catalogued finding is now represented in the paper.
  - **Third pass — figures + consistency (32 pp).** Added two figures to `src/make_phase2_figures.py`
    and the manuscript: `fig_p2_robustness.png` (PIT-KS vs normalised stress intensity — seasonality
    breaks out of the well-calibrated band while dependence stays flat and censoring degrades
    gracefully) and `fig_p2_noisefloor.png` (stacked CRPS decomposition showing the estimation-fixable
    share is ~0). **Consistency pass:** verified every manuscript table and prose number against the
    current `results/*_summary.csv` (conformal, CLV, churn, timing, amortized, BG/NBD, count-map all
    match exactly — the Step 1–11 tables were never stale because Tier 1–3 only *added* CSVs); fixed
    the now-stale "three estimation routes" phrasings to five (intro, §estinv, discussion, conclusion,
    abstract) and corrected the Laplace-agreement figures to the exact three-route spread. No undefined
    refs; no severe overfull boxes.
- **Tier 3 gap-closure — the five frontier gaps + the three previously-parked gaps are now complete**
  (`F1, F2, F3, M2, E1` and, un-parked at the user's request, `G4, D2, D3`). **This closes the entire
  reconciliation: 30 of 30 gaps done** (26 original + 4 surfaced; the 3 parked ones are now un-parked
  and done). Each ships code + a result + a smoke test (`tests/test_phase2.py`, 36 pass).
  - **E1 — HMC/NUTS sampler.** `src/hmc.py`: a self-contained Hamiltonian Monte Carlo sampler on the
    4-D *marginal* Pareto/NBD log-posterior (closed-form likelihood + numerical gradient), a genuinely
    different kernel from Abe's Gibbs. **Gibbs ≈ HMC** on population posterior and calibration
    (Simulated CRPS 0.406/0.404, CDNow 0.385/0.385; acceptance 0.72–0.84) — the estimation-agnostic
    result is not specific to one sampler. Fourth estimation route after MLE, amortized, Laplace.
  - **F1 — rolling / walk-forward.** `src/run_rolling_study.py` (`results/rolling_summary.csv`).
    Refitting at multiple calibration cut-points: CRPS improves with more data, but the **MCMC-vs-MLE
    CRPS gap is ±0.001 and PIT-KS is stable at every cut-point** (CDNow 0.025±0.006, Grocery
    0.036±0.016) — the estimator-null and calibration are stable over time, not an artefact of one split.
  - **F2 — individual-vs-cohort decomposition.** `src/run_aggregation_study.py`
    (`results/aggregation_summary.csv`). Group-total nMAE vs random-group size k: **MCMC ≈ MLE at every
    aggregation level** (within 0.004 from k=1 to k=100), while **model ≫ heuristic persists at all
    scales** because the heuristic carries a bias floor that does not average out (Simulated: parametric
    0.58→0.12 as k:1→100; heuristic stuck at ~0.81). Answers "how much pooling before method choice
    stops mattering": MCMC-vs-MLE never mattered; model-vs-heuristic always does.
  - **F3 — segment-transition / tenure.** `src/run_rolling_study.py`
    (`results/segment_tenure_summary.csv`). Top-10% membership framed as a tenure process over
    consecutive 13-week windows: retention 0.43 (CDNow) / 0.60 (Grocery) → expected tenure **1.8 / 2.5
    quarters** (≈23 / 33 weeks) — a segment-tenure forecast the classical pipeline never produces.
  - **M2 — ML survival/hazard for timing.** `src/run_ml_timing_study.py`
    (`results/ml_timing_summary.csv`). A discrete-time hazard model (pooled classifier on time-expanded
    person-period data) vs Pareto/NBD vs Pareto/GGG on the timing task, common split. **Pareto/GGG still
    wins timing** on the regular-purchasing regimes (Sim-k3 MdAE 3.89 vs ML 6.07; Grocery 3.38 vs 4.21;
    CDNow 101.9 vs 107.6); PNBD wins only when the DGP is truly memoryless (Sim-k1); the ML hazard leads
    only at moderate regularity (Sim-k2). Structure beats ML on timing — reinforces the Extension-B fix.
  - **G4 — independence stress test (un-parked).** `src/run_dependence_stress.py`
    (`results/dependence_stress_summary.csv`). Fit the independence-assuming classical model to data
    with correlated (log λ, log μ): **robust** — PIT-KS 0.022–0.029 and cov95 ~0.98 across ρ ∈ [−0.6,+0.6]
    (control ρ=0: 0.022). λ–μ dependence, when wrongly ignored, does not harm calibration.
  - **D2 — non-stationarity / seasonality (un-parked).** `src/run_seasonality_stress.py`
    (`results/seasonality_stress_summary.csv`). Inject a seasonal multiplier (1+A·sin(2πt/52)), fit the
    stationary model: **this one bites** — PIT-KS 0.024→0.118 and cov95 0.98→0.92 as A:0→1. **The one
    misspecification axis that breaks calibration**, sharpening "remarkably robust" into: robust to
    heterogeneity misspecification (dependence, regularity, mixtures), *not* to temporal non-stationarity.
  - **D3 — censoring / data-quality (un-parked).** `src/run_censoring_stress.py`
    (`results/censoring_stress_summary.csv`). Drop a fraction of repeat calibration transactions
    (acquisitions kept): **graceful degradation** — a predictable downward rate bias (CDNow E[λ]
    0.052→0.037 at 30% drop) and only mild calibration loss (PIT-KS 0.053→0.095, cov95 stays ≥0.95).
    The model tolerates realistic missingness.
- **Tier 2 gap-closure — the six cheap-open gaps are now complete** (`V3, V2, F4, E5, G5, U3`; see
  `deep_research/pareto_nbd_extension_gap_analysis.md` §3.0). Each ships code + a result + a smoke
  test (`tests/test_phase2.py`, 29 pass). Two of the results are genuinely new contributions; the
  rest reinforce the thesis.
  - **V3 — compute-cost table + Pareto frontier.** `src/run_cost_benchmark.py`
    (`results/cost_benchmark_summary.csv`, `results/figures/fig_cost_frontier.png`). Fit+predict
    wall-clock across N=500–8000 for every route, paired with CRPS. **Overturns Simon's "MCMC is
    expensive" assumption:** at N=8000 the vectorised Gibbs MCMC (2.6s) is ~6× *faster* than the
    robustness-hardened multistart MLE plug-in (16.4s) **and** wins on CRPS — MLE-plugin and Laplace
    are Pareto-**dominated**; the frontier is heuristic → PoissonGBM → Amortized → MCMC. The
    analysis's Contribution #1, delivered.
  - **V2 — profit-linked decision layer.** `src/run_profit_study.py`
    (`results/profit_study_summary.csv`). A contact policy (target customers whose M·E[x*] ≥ c) and
    a Top-10% policy, scored as % of oracle profit. Model-based targeting beats the heuristic on
    BTYD's home turf and standard retail (Simulated 88% vs 66% at c=1.0; CDNow 57% vs 49%), while on
    the miscalibrated Online Retail II the heuristic/GBM catch up or win (72–76% vs BTYD 60%) — the
    profit-space analog of the calibration finding. Top-10% value capture: BTYD best or tied on 3/4.
  - **F4 — active-customer definition sensitivity.** `src/run_active_def_study.py`
    (`results/active_def_summary.csv`). Quantifies Simon's own redefinition argument on simulated
    data where both definitions are observable: the classical P(alive) labels 27% "active", but
    **~12 points of those (at a 13-week horizon) never purchase in the window** — the customers
    P(alive) mislabels. The gap shrinks with horizon (11.9%→7.6% as h: 13→52) as the two definitions
    converge; both are well-calibrated by the model (ECE ~0.02).
  - **E5 — prior sensitivity.** `src/run_prior_sensitivity.py`
    (`results/prior_sensitivity_summary.csv`). Re-fit under vague / informative / very-diffuse
    priors: the population posterior and forecast calibration are **essentially invariant** (across
    priors, E[λ] range ≤0.001, CRPS range ≤0.001, PIT-KS range ≤0.003 on both Simulated and CDNow).
    The MCMC ≈ MLE null is **not** a convenient-prior artefact — the likelihood dominates at
    realistic N. Closes the standard Bayesian-reviewer objection.
  - **G5 — CLV discounting.** `src/run_clv_discount.py` (`results/clv_discount_summary.csv`). Proper
    *per-customer* discounting (expected factor (1−e^{−δL})/(δL) over each customer's alive-overlap L,
    vs the old flat exp(−δ) that cannot reshuffle anything): discounting **rescales** CLV (2–28%
    shrinkage over the rate/horizon sweep) but **barely reorders** it — Top-10% overlap 99.8–100%,
    Spearman rank corr 1.0000 everywhere. Discounting reshuffles the Top-A% only for long/multi-period
    horizons, not within a single finite window; the flat-factor simplification was harmless for
    ranking.
  - **U3 — PIT-KL vs PIT-KS reconciliation.** Documented in `docs/theory_variance_decomposition.md`:
    the shipped KS statistic is deliberate — binning-free, has a known testable null (pairs with the
    Lilliefors bootstrap in `run_pit_bootstrap.py`), and is the field-standard PIT diagnostic; KL of a
    smoothed histogram can be a secondary score but adds no inferential power.
- **Tier 1 gap-closure — the six partially-done gaps from the reconciliation are now complete**
  (`M3, T1, T3, D1, G2, E4`; see `deep_research/pareto_nbd_extension_gap_analysis.md` §3.0). Every
  item ships code + a result + a smoke test (`tests/test_phase2.py`, 24 pass). Highlights, all
  reinforcing the project thesis (calibration governed by the shared count assumption + correct
  evaluation, invariant to estimator/variant/covariate):
  - **M3 — conformal intervals for the ML forecasters.** `conformal.compare_conformal_ml` +
    `src/run_conformal_ml_study.py` (`results/conformal_ml_study_summary.csv`). A 3-way split
    (train ML / learn warp / test) wraps every forecaster in the same distribution-free
    recalibration as Conformalized BTYD. Recalibration **repairs the parametric PoissonGBM's
    coverage** where its Poisson assumption is too rigid (Dunnhumby PIT-KS 0.241→0.115, cov95
    0.606→0.789, ** paired Wilcoxon; Simulated 0.062→0.049 **); the distribution-free QuantileGBM
    is already calibrated so the warp is ~identity and does no harm (OnlineRetailII 0.037→0.039).
    Closes the interval-comparison asymmetry — ML now competes on honest intervals, not points.
  - **T1 — zero-inflation asymmetry formalized** (`docs/theory_variance_decomposition.md`). The
    MLE closed form is a *mean* (strictly positive); the MCMC point forecast is a *median of draws*
    (admits exact zeros iff >½ the predictive mass is at 0). The asymmetry is median-vs-mean of a
    zero-inflated law, **not** Bayesian-vs-frequentist — MLE-median also zeros, MCMC-mean is
    positive — reconciling Simon's "MCMC assigns exact zeros" footnote with the MCMC ≈ MLE null.
  - **T3 — empirical noise-floor decomposition.** `src/run_noise_floor.py`
    (`results/noise_floor_summary.csv`) + theory-doc section. Scoring the same target at the MLE
    estimate vs the true hyperparameters vs the true individual params shows the **fixable
    (estimation) share of CRPS is ≈0% even at N=500**; error is ~56% counting-noise floor + ~44%
    individual-posterior, none of it hyperparameter estimation. The empirical face of MCMC ≈ MLE,
    and it bounds the achievable gain from any estimation-side extension (E1/E4).
  - **D1 — extended simulation grid.** `run_study.py` parameterised (`--elo/--ehi` for the
    E(λ) range) with new `highfreq` and `largeN` grids. High-frequency (E(λ)≈0.61, 2× Simon's
    ceiling): BTYD stays well-calibrated (MCMC PIT-KS 0.016, cov95 0.98). Large-N scalability
    (`largeN_results.csv`): MCMC ≈ MLE remain calibrated (PIT-KS 0.004–0.014, cov95 ~0.98) **up to
    50,000 customers**, model ≫ heuristic throughout — the null is N-robust and the vectorised
    Gibbs scales.
  - **G2 — time-varying covariate.** `src/covariate_timevarying.py`: a thinned time-varying-rate
    Poisson DGP with a chain-wide promo calendar (2w/8w) + heterogeneous responsiveness, scored via
    the RFM-vs-RFM+promo GBM lens. The promo covariate adds **nothing** (CRPS 0.648 vs 0.650,
    p=0.95) and covariate-blind BTYD is best (0.479): a regular calendar's uplift is absorbed into
    the calibration-estimated baseline rate. **Extends the static-demographics null to the
    time-varying case.** (Scope caveat: a forecast window with *anomalous* promo intensity — the
    parked D2 non-stationarity regime — is where such a covariate would start to matter.)
  - **E4 — Laplace approximate-Bayes tier.** `src/laplace.py`: Gaussian posterior over the log
    hyperparameters from the MLE mode + finite-difference Hessian (eigen-repaired to PD), propagated
    by an augmentation pass identical to the MLE plug-in except θ is redrawn from the Laplace
    Gaussian each step. **Laplace ≈ MLE ≈ MCMC** on all calibration metrics (Simulated CRPS
    0.403/0.404/0.407, PIT-KS ~0.019) — a third analytic route to the estimation-agnostic result,
    alongside amortized inference. (Honest nuance: no wall-clock saving over our already-cheap
    vectorised Gibbs at these N; the middle-tier cost advantage appears only where MCMC is
    genuinely expensive.)
- **Docs — gap-analysis reconciliation:** cross-checked the fresh deep-research gap analysis
  (`deep_research/pareto_nbd_extension_gap_analysis.md`) against the actual codebase and reconciled
  three planning docs. The analysis had been written as if from a cold start against Simon (2025),
  but Phases 1–2 already execute most of it.
  - **`deep_research/pareto_nbd_extension_gap_analysis.md`:** replaced the flat inventory table with a
    **status-aware master table** (✅ done / ◑ partial / ○ open / ⏸ parked, each row carrying the
    module/evidence and what remains); added **§3.0 prioritized remaining sequence** (partials → cheap
    opens → frontier → parked); added **four newly-identified gaps** — `G5` (CLV discounting), `E5`
    (prior sensitivity), `F4` (active-customer definition/horizon sensitivity), `U3` (PIT-KL-vs-KS
    reconciliation) — as §3.9; annotated the original Phase 1/2/3 roadmap with per-item status and a
    banner pointing to §3.0. Score: **30 gaps — 10 done, 6 partial, 14 open (3 parked).** The
    analysis's flagship item (`T2`, timing via Pareto/GGG) is already done.
  - **`ROADMAP.md`:** new "Gap-analysis reconciliation" section with the tiered remaining sequence
    (close partials before opening new work) and a pointer to the master table.
  - **`TIMELINE.md`:** re-ordered the "Still open" roadmap into the same partials-first tiers and
    folded in the four new gaps.
- **Note:** the three raw-notes text files in `deep_research/` (`key_terms.txt`,
  `section_questions.txt`, `goals_and_gaps.txt`) are a separate glossary/explanation workstream and
  were **intentionally left untouched** this session.

### 2026-07-30
- **Docs — Phase 2 overhaul (README + Sphinx site, all tiers):** the docs described only Phase 1;
  brought them current with the whole statistical-vs-ML body of work. **README:** broadened intro,
  a "statistical vs. machine-learned" Key-Features block, refreshed repository-structure tree (all
  Phase 2 modules, six datasets, `results/`, `Makefile`; dropped the now-ignored `paper/`), Phase 2
  runner quickstart + `make reproduce`, and a Documentation-Directory pointing at the selection
  guide. **`docs/api_reference.md`:** added every Phase 2 module (`datasets`, `ml_benchmark`,
  `conformal`, `amortized`, `estimate_bgnbd`, `clv_data`, `clv_benchmark`, `covariate_benchmark`,
  `churn`). **`docs/ARCHITECTURE.md`:** broadened §1 framing, added the statistical-vs-ML section and
  an updated module map. **New topic pages** (`ml_benchmark`, `conformal`, `amortized`, `bgnbd`,
  `clv_benchmark`, `churn`) plus a `selection.md` decision guide, wired into a restructured
  `index.rst`. **`TIMELINE.md`:** added the M7 milestone and corrected the roadmap (several "planned"
  items are done). Sphinx build succeeds (only the two pre-existing `_static`/`mermaid` warnings; no
  broken refs from the new pages).
- **Added — Phase 2 manuscript (expanded full draft):** `paper/manuscript_phase2.tex`, a
  self-contained Springer `sn-jnl` paper titled *"Non-contractual churn: statistical or
  machine-learned? A calibration benchmark of purchase, value, and timing forecasts"* (**25 pp**,
  compiles clean via `latexmk`; 24 references resolved, zero undefined). One combined paper folding
  in all Phase 2 dimensions — counts, monetary CLV, churn, and timing — around the unifying thesis
  that the shared parametric count assumption governs calibration, invariant to estimator
  (MLE≈MCMC≈amortized) and variant (Pareto/NBD≈BG/NBD), and is repairable model-agnostically
  (Conformalized BTYD) or structurally (Pareto/GGG timing). Expanded from the initial 18 pp draft
  with a formal problem-setup/notation section, full model likelihoods and predictive construction,
  formal CRPS/PIT/coverage/ECE definitions, per-dataset descriptions, three algorithm boxes (Gibbs,
  conformal recalibration, amortized net), a managerial decision-rule table, and extended-results
  appendices (accuracy/sharpness, 95% coverage, forecast-time `x>0` conditioning).
- **Added — reproducible paper assets:** `src/make_phase2_figures.py` (six figures →
  `paper/figures/fig_p2_*.png`) and `src/make_phase2_tables.py` (ten LaTeX tables emitted from
  `results/*_summary.csv`, matching the Phase 1 traceable-tables convention); `paper/refs_phase2.bib`
  for the ML/conformal/ECE references (Kuleshov 2018, Wang 2019, Friedman 2001, Koenker 1978, Guo
  2017, Lilliefors 1967, etc.), passed alongside `refs.bib`.
- **Added — planning:** `paper/phase2_outline.md`, the section-by-section scaffold (thesis, arc,
  results→asset map) the manuscript was drafted from.
- **Changed — `.gitignore`:** the `paper/` directory is now ignored — the research manuscript is a
  separate deliverable, kept out of the code repo. Already-tracked Phase 1 paper files are
  undisturbed; the new Phase 2 paper and future paper files are excluded going forward. The
  `src/make_phase2_*` reproducibility scripts stay tracked (they are code, not the paper).
- **Added — alternative typesettings (style experiment):** `src/make_phase2_variants.py` extracts the
  shared body of `manuscript_phase2.tex` into `paper/phase2_body_std.tex` and wraps it in two
  standard-`article` styles — `manuscript_phase2_modern.tex` (Times + New TX math, blue sans section
  headings, coloured links; 21 pp) and `manuscript_phase2_elegant.tex` (Palatino/newpx, centred
  small-caps headings, classic rules; 23 pp). Both compile clean (0 undefined citations) via natbib +
  `plainnat`. The Springer `sn-jnl` original is left untouched as the baseline.

### 2026-07-29
- **Planning:** added the **Phase 2** expansion plan to `ROADMAP.md` — a calibration benchmark
  of *statistical vs. machine-learning* customer forecasting (12 sequenced items: ML comparators,
  new public/Kaggle datasets, conformal recalibration, amortized neural inference, covariates,
  churn scoring, more BTYD variants, engineering maturity).
- **Added — Phase 2 Step 1:** `src/ml_benchmark.py` — a Poisson gradient-boosted RFM forecaster
  (`HistGradientBoostingRegressor(loss="poisson")`) whose Poisson predictive is scored under the
  existing CRPS / randomized-PIT / coverage engine, with a fair train/test customer split against
  Pareto/NBD (`compare_btyd_vs_gbm`).
- **Added — Phase 2 Step 3 (dataset loaders):** `src/datasets.py` — ingestion for four public
  benchmarks (Online Retail II, Olist, Dunnhumby, Ta-Feng) → the standard cohort summary via
  `elog_to_summary`; smoke-tested. Active rates span 1.6% (Olist, extreme zero-inflation) → 96%
  (Dunnhumby, extreme density), far wider than CDNow/Grocery alone.
- **Added — Phase 2 Step 4 (cross-dataset benchmark):** `src/run_ml_benchmark.py` +
  `results/ml_benchmark.csv`/`.log`. First pass (single seed, all customers): BTYD sharper on the
  classic sparse sets (CDNow, Grocery); on **Online Retail II, BTYD miscalibrates badly (PIT-KS
  0.20) and the GBM wins on both accuracy and calibration**; on extreme zero-inflation (Olist) the
  two are indistinguishable; on extreme density (Dunnhumby) BTYD wins but *both* are poorly
  calibrated. No universal winner — the calibration lens localizes where BTYD's assumptions break.
  Needs multi-seed confirmation before it becomes a paper claim.
- **Confirmed — Phase 2 Step 4 (multi-seed: 15 seeds × 7 datasets, paired Wilcoxon):**
  `src/run_ml_study.py` + `results/ml_study_summary.csv`. The map holds with tight sd and
  significance. Control passes (BTYD wins both axes on Simulated). BTYD wins-or-ties on 5/7 real
  datasets; **on Online Retail II BTYD's calibration collapses (PIT-KS 0.211±0.01 vs GBM 0.054)
  and it is also less accurate — ML wins both**, a confirmed counterexample to "structure always
  wins." On dense Dunnhumby *neither* model is well-calibrated (0.17–0.23). Multi-seed corrected
  a single-seed over-read (CDNow calibration is a tie, not a GBM win).
- **Added — Phase 2 Step 2 (stronger ML comparators):** `ml_benchmark.py` gains
  `hurdle_gbm_forecast` (zero-inflated hurdle — a P(active) classifier × shifted-Poisson positive
  count; the count analog of ZILN) and `quantile_gbm_forecast` (distribution-free multi-quantile
  GBM), plus `compare_all` scoring BTYD against all three ML models. Smoke test on the datasets
  where the Poisson assumption fails: the **distribution-free QuantileGBM is best on both accuracy
  and calibration** — Online Retail II PIT-KS **0.040** (vs BTYD 0.231, Poisson-GBM 0.072) and
  dense Dunnhumby **0.070** (vs BTYD 0.154, Poisson-GBM 0.253). Localizes BTYD's miscalibration to
  the parametric count assumption. **Confirmed by the full four-method multi-seed study (15 seeds ×
  7 datasets; all headline differences p≤6.1e-5 — every seed agrees):** BTYD wins accuracy AND
  calibration on Simulated/Grocery and stays sharpest on sparse CDNow; the distribution-free
  QuantileGBM wins both axes on Online Retail II, Dunnhumby and Ta-Feng (Dunnhumby PIT-KS 0.058 vs
  BTYD 0.169); the HurdleGBM is best-calibrated on the zero-heavy sets (CDNow/Online Retail/Olist).
  Conclusion: BTYD's miscalibration is the parametric-Poisson count assumption; distribution-free
  ML repairs it in the regimes where that assumption breaks.
- **Added — Phase 2 Step 5 (Conformalized BTYD):** `src/conformal.py` — distributional
  recalibration (Kuleshov, Fenner & Ermon 2018) of the BTYD predictive via an isotonic
  quantile-warp learned on a held-out calibration split (`recalibrate_samples`,
  `compare_conformal`). Smoke test: repairs BTYD's worst failure — Online Retail II PIT-KS
  **0.196→0.026** (CRPS 0.776→0.660, now beating the best ML), Dunnhumby 0.177→0.105 — while
  leaving already-calibrated Grocery untouched (0.037→0.042). Keeps BTYD's cheap fit +
  interpretability while fixing coverage. **Confirmed by the multi-seed before/after study (15
  seeds × 7 datasets, paired Wilcoxon):** significantly repairs every miscalibrated set — Online
  Retail II PIT-KS 0.212→0.044, Dunnhumby 0.164→0.097, Ta-Feng 0.072→0.027, CDNow 0.056→0.034
  (all p<0.001) — with accuracy preserved or improved (Online Retail CRPS 0.78→0.65), and no
  meaningful harm where already calibrated (Grocery unchanged). Recalibrated BTYD on Online Retail
  now matches the best ML on calibration and beats it on accuracy.
- **Added — Phase 2 Step 6 (amortized neural inference):** `src/amortized.py` +
  `run_amortized_check.py`. An MLP maps cohort summary statistics → Pareto/NBD parameters (trained
  once on 4000 simulated cohorts), so inference for any new cohort is a single forward pass — no
  sampler, no per-cohort optimisation. Confirmed: on 25 held-out simulated cohorts amortized ≈ MCMC
  (CRPS p=0.51; PIT-KS 0.032 vs 0.037, amortized marginally better), and it matches-or-beats MCMC
  calibration on every real dataset (Online Retail 0.121 vs 0.207). A third, *instant* estimation
  route confirming forecast calibration is estimation-method-agnostic.
- **Added — Phase 2 Step 7 (probabilistic CLV, first pass):** `src/clv_data.py` (monetary loaders
  + CLV summary for Online Retail II / Ta-Feng / Dunnhumby) and `src/clv_benchmark.py` comparing
  Pareto/NBD + Gamma-Gamma vs. a deep zero-inflated-lognormal MLP (ZILN, Wang et al. 2019, torch)
  on the monetary CLV target under CRPS/PIT/coverage. Smoke test shows a calibration-vs-sharpness
  tradeoff: BTYD+GG far more accurate but miscalibrated on Online Retail (CRPS 418, PIT-KS 0.215);
  ZILN well-calibrated (0.027) but imprecise (heavy lognormal tail); on dense Dunnhumby ZILN wins
  both (PIT-KS 0.048 vs 0.127, equal CRPS). ZILN then tuned (validation early-stop + heavy-tail cap
  fixed the over-dispersion: Online Retail CRPS 1744→519). **Confirmed by the multi-seed study (15
  seeds × 3 monetary datasets, paired Wilcoxon, `run_clv_study.py`):** the deep ZILN is
  significantly better calibrated than BTYD+Gamma-Gamma on every dataset (Online Retail PIT-KS
  0.212→0.031, Ta-Feng 0.082→0.020, Dunnhumby 0.143→0.073; all p<0.001) at comparable accuracy
  (CRPS tied on Ta-Feng/Dunnhumby, BTYD+GG a bit sharper on Online Retail). Extends the count
  finding to money: structural CLV inherits the Poisson miscalibration; the distribution-learning
  ZILN stays calibrated.
- **Added — Phase 2 Step 7 (covariate value):** `src/covariate_benchmark.py`. On the 801
  demographics-carrying Dunnhumby households, adding demographics (age/income/marital/home/kids) to
  the ML count model does NOT improve calibration (PIT-KS 0.206→0.205, paired Wilcoxon p=0.77) or
  sharpness — RFM already captures what matters; the dense-data miscalibration is about the count
  distribution, not missing covariates.
- **Building — Phase 2 Steps 8–12:** (a) **Step 8 timing** — added `t_next`/`litt` to the data
  pipeline and `run_timing_study.py`; smoke test shows Pareto/GGG beats Pareto/NBD on next-purchase
  timing for regular data (MdAE 2.68 vs 4.37 at k=3), addressing Simon's stated timing failure.
  (b) **Step 9 churn** — `churn.py` + `run_churn_study.py` score P(active) calibration (Brier +
  ECE) for BTYD vs an ML classifier. (c) **Step 10 BG/NBD** — `estimate_bgnbd.py` (MLE + vectorised
  `min(Geometric(p), Poisson(λT*))` predictive; recovers E(λ), competitive calibration) +
  `run_bgnbd_study.py`. (d) **Step 11 rigor** — `run_pit_bootstrap.py`, a parametric-bootstrap
  parameter-adjusted PIT-KS null. (e) **Step 12 tests** — `tests/test_phase2.py` (6 numerical
  tests for the new modules, all passing). **All confirmed by multi-seed studies:** Step 8 timing —
  Pareto/GGG beats Pareto/NBD on next-purchase median error where regular (Sim k=3 3.23 vs 4.49,
  Grocery 2.98 vs 3.89, p<0.001). Step 9 churn — BTYD's P(active) well-calibrated where its
  assumptions hold, badly miscalibrated on misspecified/dense data (Online Retail ECE 0.185 vs ML
  0.051), matching the count/CLV story. Step 10 — Pareto/NBD and BG/NBD essentially interchangeable
  (CRPS within 0.5%, calibration close, both broken on misspecified data): model variant is
  immaterial within the family. Step 11 — the naive 1.36/√n PIT-KS critical value is ~10% too small
  (Lilliefors); CDNow's mild departure survives the parameter-adjusted bootstrap null, Grocery is
  calibrated.
- **Docs:** added `docs/datasets.md` — why data age is irrelevant to a calibration study and why we
  avoid newer synthetic / cross-sectional datasets; wired into the Sphinx toctree.
- **Engineering (Phase 2 Step 12, partial):** added GitHub Actions CI
  (`.github/workflows/ci.yml` — pytest on py3.9/3.11/3.12 + flake8), `CITATION.cff`, and a
  `Makefile` (`make reproduce` / test / lint / format / docs / paper); `pyproject.toml` now
  declares `black`/`flake8` in `[dev]` and a `[ml]` extra (`scikit-learn`).
- **Process:** started keeping this dated development log in the changelog.

### 2026-07-28
- **Fixed — CLV posterior (`clv.py`):** `sample_posterior_nu` now samples the mean transaction
  value from the correct **Inverse-Gamma** posterior instead of a Gamma. The previous code
  returned per-customer mean spend ~1/observed (orders of magnitude too small and anti-correlated
  with the data); posterior spend now tracks observed spend with proper shrinkage.
- **Fixed — `timing.py`:** the empty-input branch of `score_timing_forecast` now returns the
  `timing_MAE` key (was `timing_nAE`), so cross-cohort aggregation no longer breaks.
- **Added:** numerical regression tests `test_clv_posterior_spend_is_realistic` (posterior spend
  tracks observed, correlation > 0.9) and `test_parameter_recovery` (MLE/MCMC recover `E(λ)` and
  agree); documentation suite `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `CONTRIBUTING.md`,
  `TIMELINE.md`, `CHANGELOG.md`, `SECURITY.md`, and a Documentation Directory in the README.
- **Changed:** removed the unused `seaborn` dependency from `pyproject.toml`; clarified the README
  (Pyodide app is "no-server-required", CDN-loaded, not "standalone"; softened "proves" to "shows …
  via a law-of-total-variance scaling argument").

## [1.0.0] — 2026-07-28

First public release.

### Added
- **Estimation:** robust bounded multi-start MLE and a pure-`numpy` Abe (2009)/BTYDplus
  data-augmentation MCMC Gibbs sampler (`estimate.py`); common-`k` Pareto/GGG augmented
  sampler (`estimate_ggg.py`).
- **Scoring:** sample CRPS, Laplace-floored discrete log score, Czado et al. (2009)
  randomized PIT, interval coverage, and sharpness (`score.py`, `logscore_check.py`).
- **Study:** simulation runners and analysis producing the paired Wilcoxon /
  Benjamini–Hochberg and TOST equivalence results, tables, and figures.
- **Extensions:** purchase-timing forecasting `t_{x+1}` (`timing.py`, Extension B) and
  Gamma-Gamma probabilistic CLV (`clv.py`, Extension E).
- **Empirical validation** on the CDNow and Grocery public benchmarks (`empirical.py`).
- **Convergence diagnostics:** split-R-hat, ESS, and forecast-score reproducibility
  across overdispersed chains (`convergence.py`).
- **Paper:** Springer Nature `sn-jnl` manuscript, *"Non-contractual churn with MCMC: are
  Pareto/NBD purchase forecasts calibrated?"*
- **Tooling:** PEP 621 packaging, MIT license, pytest suite, Sphinx/ReadTheDocs docs, and
  a Pyodide interactive web application.

[Unreleased]: https://github.com/pranava-baascaran/pareto-nbd-extension/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/pranava-baascaran/pareto-nbd-extension/releases/tag/v1.0.0
