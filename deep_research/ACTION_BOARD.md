---
title: "ACTION BOARD — the one doc: what to do and how it's progressing"
type: action-board
updated: 2026-08-10
role: Single entry point / live dashboard. Status + tasks live here; the *content* (evidence,
      reasoning, numbers) lives in the linked detail docs. Open this first.
---

# 🧭 Action Board — Pareto/NBD Extension (Phase 2 paper)

**The one doc.** Open this to see what's left and how it's going. Rows link to the authoritative
detail docs. Update the Status column as work lands (keep detail in the linked docs, not here).

**Project in one line:** experiments are **done**, the manuscript is **drafted, refereed, and revised
to v2.0.12** (Ulrich + field surveys + the 9-paper genealogy sweep folded in); the live work is the
**pre-submission checklist → submission**, blocked only on **one** author decision now (**venue**) —
**F8 is closed** (Indian dataset unobtainable; logged as a manuscript limitation, 2026-09-20).

**Legend:** ✅ done · 🔄 in progress · ⬜ to do · 🟡 needs your decision · ⏸ deferred · 🤖 I can do · 🧑 you

---

## 1. At a glance

| Phase | State | Detail |
|---|---|---|
| **1. Experiments (30-gap closure)** | ✅ **Complete** — 30/30 gaps, 42 tests | [gap analysis](pareto_nbd_extension_gap_analysis.md) · [session record](session_record.md) |
| **2. Manuscript draft + referee** | ✅ **Complete** — v2.0.2, ~40–41 pp, refereed | [referee tracker](referee_review_response.md) |
| **3. Literature deep-read & monitor** | ✅ **Done (2026-08-11)** — deep-read + [corpus critique](corpus_critique.md) + OpenAlex live monitor all complete; novelty confirmed vs **local + live** literature. Only tracker-73 GUI mining (🧑) + a pre-submission re-sweep remain | [deep dive](deep_dive.md) · [lit matrix](LITERATURE_MATRIX.md) |
| **4. Manuscript v2.0.3 edits** | ✅ **Complete (2026-08-10)** — Ulrich + field surveys folded in; one optional figure item left | this doc §3 |
| **5. Pre-submission / author-side** | 🟡 **Blocked on 1 decision** (venue); **F8 closed** (unobtainable, logged as limitation) | this doc §3 |
| **6. Optional engineering** | ⏸ **Deferred to the end** | [ROADMAP](../ROADMAP.md) |

**One thing only you can decide** now: **venue** (default JBE / Springer `sn-jnl`). **F8 (India
dataset) is closed** — resolved 2026-09-20 as *unobtainable*; the manuscript now documents it as a
data limitation (Data § + Limitations §, v2.0.12). See §4.

---

## 2. What's done (so you don't re-open it)

| ✔ | Milestone | Evidence |
|:--:|---|---|
| ✅ | All **30/30** gaps closed (G/E/M/U/V/D/F/T series) | [gap analysis §3](pareto_nbd_extension_gap_analysis.md) |
| ✅ | Manuscript **v2.0.2**, ~40–41 pp, compiles clean (0 undefined refs) | `paper/manuscript_phase2.tex` |
| ✅ | Self-referee pass + full **external referee cycle** (all closed but F8) | [referee tracker](referee_review_response.md) |
| ✅ | Test suite **42 passing** | `tests/test_phase2.py` |
| ✅ | **Ulrich (2026)** read + verdict (complement, not competitor) | [deep_dive §8](deep_dive.md) · [[ulrich-dead-reckoning]] |
| ✅ | **Manzoor (2024) §VI** cross-walked (we patch 4/5 field gaps) | [crosswalk](gap_crosswalk_manzoor2024.md) |
| ✅ | Writing exemplars (figures/tables/structure) collected | [writing inspiration](writing_inspiration.md) |

---

## 3. The board — what to do, and how it's progressing

### Phase 3 — Literature deep-read & monitor 🔄

| Status | Who | Task | Detail |
|:--:|:--:|---|---|
| ✅ | 🤖 | Read **Ulrich (2026) "Dead Reckoning"**; verdict recorded | [deep_dive §8](deep_dive.md) |
| ✅ | 🤖 | Cross-walk **Manzoor (2024) §VI** vs our gap analysis | [crosswalk](gap_crosswalk_manzoor2024.md) |
| ✅ | 🤖 | **Curate the paper tracker** — 185 identified → **73 kept** (funnel for the PRISMA figure); fixed the `clv_rfm` scope leak; snapshot + audit CSVs; desktop shortcut refreshed | `../research-paper-tracker/` (`tools/curate.py`, `data/out/funnel_counts.csv`) |
| 🔄 | 🧑 | **Daily:** open the app → Refresh → `python tools/curate.py --apply` → skim/star (manual cadence) | tracker `README.md` |
| ✅ | 🤖 | Read remaining candidates: **Imani (2025)** (full), **Leoni-Perego (2022)**, **Sci Reports (2024)** + 6 appendix churn papers | [triage table](deep_dive.md) |
| ✅ | 🤖 | Confirm the **Calib?** column across the matrix (novelty defense **finalised** — no ML paper calibrates; reviews omit BTYD+calibration) | [lit matrix §1](LITERATURE_MATRIX.md) |
| ✅ | 🤖 | Mine the tracker's **73 kept** for any new must-cite — **done 2026-08-11: 0 must-cites.** Only Ulrich calibrates (already cited); the other 70 are recent applications/low-tier reviews. 1 optional parallel-work cite added (Lin et al. 2026 two-stage Hurdle-GBM, `lin2026`). Novelty confirmed vs the tracker too. | tracker DB |
| ✅ | 🤖 | **Gap-fill synthesis (2026-08-21):** one long table of *how our paper patches/fills each prior paper's gap* — 18 papers across foundations, ML competitors, churn classification, field reviews, Ulrich + tools | [gap-fill matrix](GAP_FILL_MATRIX.md) |
| ✅ | 🤖 | **Field genealogy + historical citation tree (2026-09-20):** origins→present. Built the field's history (Ehrenberg 1959 → Schmittlein 1987 → today), the industries map, a **3,043-paper / 20,457-edge citation tree** (Crossref+OpenCitations) ingested into `tracker.db` as one corpus (floor 2023→1959), and a **triage funnel** sifting it to **127 core / 694 scan / 230 ref / 1,992 archive**. | [genealogy](FIELD_GENEALOGY.md) · [industries](INDUSTRIES_NONCONTRACTUAL.md) · [core reading](CORE_READING_LIST.md) · [progression](HISTORICAL_PROGRESSION.md) |
| ✅ | 🤖 | **Screen the genealogy's new Tier-A/B finds** into Related Work — esp. **Xie (2020) Pareto/NBD-vs-NN** (verify calibration vs estimation-window), Dew (2018), Bachmann (2021), Jasek (2018/19). Screened 2026-09-20 → none calibrate, novelty safe. **Folded in 2026-09-20 (manuscript v2.0.12):** 9 DOI-verified comparators (xiehuang2020, xie2022, bauer2021, jasek2018, jasek2019, chou2022, zhou2024, bogaert2023, kiyakoglu2024) now cited in body + `tab:related`; Bachmann/Dew were already cited. **Nothing left here.** | `manuscript_phase2.tex` §RW + `tab:related`, l.283–394 |

### Phase 4 — Manuscript **v2.0.3** revision ✅ (landed 2026-08-10; recompiles clean, 42 pp, 0 undefined refs — one optional figure item left)

| Status | Who | Task | Source |
|:--:|:--:|---|---|
| ✅ | 🤖 | **Fold in Ulrich:** add `ulrich2026` to `refs_phase2.bib`; cite in Related Work | [[ulrich-dead-reckoning]] |
| ✅ | 🤖 | Add **one distinguishing clause** to the §1 "first" claim (scope to ML comparison) | manuscript l.169–173 |
| ✅ | 🤖 | Cite Ulrich on the **churn target** (§7.7: our `P(x*>0)` = his `R_H`) — pre-empts his "category error" | [deep_dive §8](deep_dive.md) |
| ✅ | 🤖 | Cite Ulrich in **robustness/seasonality** (our per-window conformal vs his dynamic layer) | [[seasonality-finding]] |
| ✅ | 🤖 | Add **profit-metric lineage**: `verbraken2013` (EMP/MPC) + `manzoor2024` → bib; cite in §profit (V2) | [crosswalk G4](gap_crosswalk_manzoor2024.md) |
| ✅ | 🤖 | Cite **field surveys** Manzoor (2024) + Imani (2025) in Related Work; Manzoor's G4 as the calibration-lens springboard | [crosswalk](gap_crosswalk_manzoor2024.md) |
| ✅ | 🤖 | Add **XAI Limitations paragraph** (Manzoor G5); cite Boukrouh & Azmani (2025) + De Caigny (2024) | [crosswalk G5](gap_crosswalk_manzoor2024.md) |
| ✅ | 🤖 | **Verify + add** all `(to add)` bib entries (Ulrich, Manzoor, Imani, Verbraken, De Caigny, ChurnNet, Boukrouh) — PDF/web-confirmed | [writing inspiration](writing_inspiration.md) |
| ⬜ | 🤖 | *Optional:* adopt Valendin's **colored per-dataset tag scheme** in the Data section (figure work, deferred) | [writing inspiration A](writing_inspiration.md) |
| ✅ | 🤖 | Recompile clean, bump **2.0.2 → 2.0.3**, log to `CHANGELOG.md` | [[manuscript-versioning]] |

### Phase 5 — Pre-submission / author-side ⬜🟡

| Status | Who | Task | Notes |
|:--:|:--:|---|---|
| ✅ | 🧑 | **F8 — CLOSED (2026-09-20): Indian dataset unobtainable.** Presenting the US/UK/Brazil/Taiwan spread as-is; logged as a data limitation in the manuscript (Data + Limitations, v2.0.12) for future revisiting. | resolved |
| 🟡 | 🧑 | **Venue** — confirm (scaffold defaults to JBE / Springer `sn-jnl`) | drives formatting + disclaimer style |
| ⬜ | 🧑 | Replace `phase1` placeholder citation once Phase 1 is public (+ anonymize for review) | blocked on Phase 1 |
| ⬜ | 🤖 | Ensure **disclaimer** (data-availability / AI-use / COI / funding), **complete verified references**, and an **appendix** (derivations, diagnostics, grids, abbreviations list) | [writing inspiration §F](writing_inspiration.md) |
| ⬜ | 🤖🧑 | **Cover-to-cover proofread** for flow/tone across the ~50 incremental additions | |
| ⬜ | 🤖 | *Optional* abstract refresh (name the seasonality boundary + repair-stacking rescue) | |
| ⬜ | 🤖 | Re-sync `github_upload_bundle/` + `.zip` before any GitHub push | [[bundle-is-a-build-artifact]] |

### Phase 6 — Optional engineering ⏸

| Status | Who | Task |
|:--:|:--:|---|
| ⏸ | 🤖 | Importable `import paretonbd` package API |
| ⏸ | 🧑 | PyPI / Zenodo release (needs accounts) |

---

## 4. Decisions I need from you

1. ~~**F8 — the India dataset.**~~ **CLOSED 2026-09-20** — determined unobtainable; the current
   US/UK/Brazil/Taiwan 7-cohort spread stands and geography is now documented as a data limitation in
   the manuscript (Data § + Limitations §, v2.0.12), flagged for future revisiting.
2. **Venue.** Keep the JBE / Springer `sn-jnl` default, or target elsewhere? *(Affects template,
   anonymization, and the disclaimer format.)* — **the one remaining author decision.**

Phase 4 (the v2.0.3 batch) is now **done**. The natural next move is the **Phase 5 pre-submission
checklist** I can execute without you — the disclaimer/declarations block, a complete verified
appendix (derivations, diagnostics, grids, abbreviations list), and a cover-to-cover proofread — plus
the remaining Phase 3 candidate reads (Imani full, Leoni–Perego, Sci Reports). Only **venue** now
stays open (F8 closed) and it blocks none of that.

---

## 5. Coverage verdict & Gear 2 groundwork  *(2026-09-20)*

### Is the paper ready? — **novelty is safe; a bounded citation sweep remains**
Re-checked the expanded corpus (3,043-paper genealogy + the new Tier-A/B finds). **No new paper
evaluates BTYD-vs-ML by probability calibration** — the headline novelty claim still holds against the
enlarged corpus and the live OpenAlex graph. Specifically, the flagged threats are *not* threats:

| New find | What it is | Threat? |
|---|---|---|
| **Xie (2020)** Pareto/NBD vs NN | comparison by **point accuracy**; NN used for **parameter estimation** | ❌ no calibration; its NN-estimation angle = our amortized-inference contribution |
| **Xie (2022)** NN extension for Pareto/NBD | NN **estimation** of Pareto/NBD | ❌ estimation, not calibration |
| **Bauer & Jannach (2021)** seq2seq CLV | ML-CLV point forecasts | ❌ point error |
| **Bachmann (2021)** time-varying latent attrition | covariate extension of BTYD | ❌ no calibration |
| **Dew (2018)** Bayesian nonparametric CBA | flexible BTYD | ❌ no calibration |
| **Jasek (2018/19)** probabilistic CLV comparison | BTYD/CLV model comparison | ❌ point/accuracy |
| Chou (2022), Zhou (2024), Yan (2023), Bogaert (2023), Kiyakoglu (2024) | applied CLV/ML/churn | ❌ point/classification |

**Verdict:** the paper does **not** need more *research* to defend novelty. It needs a **finite
Related-Work expansion** — cite ~8–10 of the above as additional comparators/context (they make the
survey look complete to a referee) — plus the two author decisions (F8, venue) and the pre-submission
checklist. This is a bounded sweep, not open-ended review. New candidates will now also be caught
automatically by the tracker's new `causal_ml_uplift` / `causal_ml_churn` categories.

### Gear 2 groundwork laid (2026-09-20)
| ✔ | Deliverable | Doc |
|:--:|---|---|
| ✅ | **Causal-ML literature pull** (methods, marketing/churn line, calibration-of-effects, reading path) | [CAUSAL_ML_LITERATURE.md](CAUSAL_ML_LITERATURE.md) |
| ✅ | **Tooling inventory — causal ML** (econml/causalml installed & smoke-tested; sklift/DoWhy/DoubleML) | [TOOLING_CAUSAL_ML.md](TOOLING_CAUSAL_ML.md) |
| ✅ | **Tooling inventory — non-contractual/BTYD** (R/Py packages, eval gap, ML-CLV stack) | [TOOLING_NONCONTRACTUAL.md](TOOLING_NONCONTRACTUAL.md) |
| ✅ | **Dataset hunt & log** — incl. ⭐ Dunnhumby already carries campaign/coupon **treatment** | [DATASETS_LOG.md](DATASETS_LOG.md) |
| ✅ | Tracker now monitors causal ML (`causal_ml_uplift`, `causal_ml_churn`) | `config/categories.yaml` |
| ✅ | Folded **9** DOI-verified genealogy finds into manuscript Related Work + `tab:related` (v2.0.12, recompiles clean) | manuscript §RW |
| ✅ | **F8 logged as unachievable** in the manuscript (Data + Limitations) + across the board | v2.0.12 |

---

## 6. Doc map — where the detail lives

| Doc | What it holds |
|---|---|
| **ACTION_BOARD.md** *(this)* | the live task dashboard — open first |
| [`../ROADMAP.md`](../ROADMAP.md) | narrative research plan + history + current-state handoff |
| [`pareto_nbd_extension_gap_analysis.md`](pareto_nbd_extension_gap_analysis.md) | the 30-gap master table (experiments) |
| [`gap_crosswalk_manzoor2024.md`](gap_crosswalk_manzoor2024.md) | our gaps vs the field review's 5 gaps |
| [`deep_dive.md`](deep_dive.md) | literature-monitor plan + Ulrich verdict + triage trackers |
| [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md) | per-paper matrix + novelty-defense scoreboard |
| [`GAP_FILL_MATRIX.md`](GAP_FILL_MATRIX.md) | long table: how our paper patches/fills each prior paper's gap |
| [`writing_inspiration.md`](writing_inspiration.md) | figures/tables/structure to borrow + "remember to include" |
| [`referee_review_response.md`](referee_review_response.md) | external referee items + resolutions |
| [`session_record.md`](session_record.md) | consolidated record of the gap-closure + drafting session |
| [`../CHANGELOG.md`](../CHANGELOG.md) | dated dev log (newest first) |

*Convention: this board is the status/task layer; the detail docs are the content layer. When a task
lands, tick it here and record the substance in the linked doc (see [[docs-directory-convention]]).*
