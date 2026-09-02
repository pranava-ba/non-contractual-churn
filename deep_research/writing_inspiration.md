---
title: "Writing inspiration & cross-reference — figures, tables, and structure to borrow"
type: writing-aid
created: 2026-08-10
purpose: A curated checklist of specific figures/tables/structure from the reference library to
         consult (for design inspiration and honest cross-reference / citation) when drafting the
         Phase-2 manuscript. Not things to copy — things to look at, learn from, and cite.
---

# Writing inspiration & cross-reference

Each row is a **specific element** in a paper we hold, worth looking at while drafting. "Use" = how it
might help our paper. All files are under [`../references/`](../references/); bib keys are in
`paper/refs_phase2.bib` (Phase 2) or `paper/refs.bib` (Phase 1). **Design inspiration only — reproduce
nothing; cite where we build on an idea, and redraw any figure in our own uniform theme (see
[[uniform-figure-theme]]).**

## A. Figures / diagrams to study

| Want | Paper | File | Bib | Use in our paper |
|---|---|---|---|---|
| **Color diagrams explaining the churn window** | Ganeson, Lew & Razak (2022), *A Proposed Churn Window for Non-Contractual Purchases* | [`phase1/04_ganeson_2022_churn_window.pdf`](../references/phase1/04_ganeson_2022_churn_window.pdf) | *(phase1)* | Explaining our finite-horizon active/churn definition (the `P(x*>0)` window) — pairs with the Ulrich `R_H` framing. |
| **Transaction-timing plots — weekly charity contributions, ~20 example individuals** | Valendin et al. (2022), *Customer Base Analysis with RNNs* | [`phase2/09_valendin_2022_rnn_customer_base.pdf`](../references/phase2/09_valendin_2022_rnn_customer_base.pdf) | `valendin2022` | A per-customer event-timeline strip to illustrate sparsity / regularity across our 7 cohorts. |
| **Network scheme diagram (LSTM architecture)** | Valendin et al. (2022) | *(same)* | `valendin2022` | Schematic style for our amortized-inference MLP and the ML forecasters (§models). |
| **Relative predictive-performance lift: LSTM vs benchmarks** | Valendin et al. (2022) | *(same)* | `valendin2022` | A "lift vs baseline" panel — analog for our BTYD-vs-ML calibration deltas per cohort. |
| **The colored per-dataset tag scheme (black / pink / green)** | Valendin et al. (2022) | *(same)* | `valendin2022` | **Strong adoption candidate.** Their tags summarize each dataset's *regularity/randomness/irregularity, cohort size, churn rate, calibration-period length, mean transaction frequency, clumpiness, and seasonal-pattern prominence*. We have 7 cohorts spanning a 50× activity range — a tag row per cohort in the Data section (§data) would visually justify *why* calibration breaks where it does (dense/seasonal). |
| **"Overview of different approaches to simulation-based inference"** | Cranmer, Brehmer & Louppe (2020), *The Frontier of SBI* | [`phase2/07_cranmer_2020_simulation_based_inference.pdf`](../references/phase2/07_cranmer_2020_simulation_based_inference.pdf) | `cranmer2020` | Positioning our amortized estimator within the SBI landscape (§amortized). |
| **All diagrams / charts / graphs** | Chamberlain et al. (2017), *CLV Prediction Using Embeddings* | [`phase2/06_chamberlain_2017_clv_embeddings.pdf`](../references/phase2/06_chamberlain_2017_clv_embeddings.pdf) | `chamberlain2017` | ML-CLV counterpoint figures; reliability/lift presentation for the value dimension (§clv). |
| **All figures / graphs (calibration plots)** | Kuleshov, Fenner & Ermon (2018), *Accurate Uncertainties … Calibrated Regression* | [`phase2/17_kuleshov_2018_calibrated_regression.pdf`](../references/phase2/17_kuleshov_2018_calibrated_regression.pdf) | `kuleshov2018` | **Direct template** for our PIT / reliability-diagram / before-after-recalibration figures (Conformalized BTYD). Their calibration-plot idiom is the one to match. |

## B. Tables to study

| Want | Paper | File | Bib | Use |
|---|---|---|---|---|
| **"Predictors used in this study" + variable-importance chart** | Buckinx & Van den Poel (2005), *Partial defection … non-contractual FMCG retail* | [`phase2/03_buckinx_vandenpoel_2005_partial_defection.pdf`](../references/phase2/03_buckinx_vandenpoel_2005_partial_defection.pdf) | `buckinx2005` | Feature-table + importance layout for our RFM/covariate section (esp. the "demographics add nothing over RFM" result). |
| **Table 1 — literature review of hybrid segmented learners in CCP** | De Caigny, De Bock & Verboven (2024), *Hybrid Black-Box Classification … Segmented Interpretability* | [`phase2/appendix/decaigny_2024_hybrid_blackbox_churn.pdf`](../references/phase2/appendix/decaigny_2024_hybrid_blackbox_churn.pdf) | *(added ✅)* | A model-comparison / related-work table format for our Related Work (§related). |
| **Table 4 — Model Hyperparameters** | Saif, Maggiore & Distante (2026), *ChurnNet* (arXiv:2606.00169) | [`phase2/appendix/churnnet_2026_saif_distante.pdf`](../references/phase2/appendix/churnnet_2026_saif_distante.pdf) | *(added ✅)* | Reproducibility hyperparameter-table format for our ML forecasters (appendix). |

## C. Structure / prose to study

| Want | Paper | File | Use |
|---|---|---|---|
| **Cohesive, natural section & subsection flow** | Boukrouh & Azmani (2025), *Explainable ML … customer churn for e-commerce* (IJ-AI 14(1):286–297) | [`phase2/appendix/boukrouh_azmani_2025_explainable_ecommerce_churn.pdf`](../references/phase2/appendix/boukrouh_azmani_2025_explainable_ecommerce_churn.pdf) | Model for how our sections/subsections should read as one narrative (supports [[docs-monograph-goal]] for the paper's prose). |

## D. Author bio

| Want | Paper | File | Bib | Use |
|---|---|---|---|---|
| **"About the author"** | Gupta et al. (2006), *Modeling Customer Lifetime Value* (Sunil Gupta) | [`phase2/05_gupta_2006_modeling_clv.pdf`](../references/phase2/05_gupta_2006_modeling_clv.pdf) | `gupta2006` | Context on the CLV-terrain author we lean on for the value framing. |

## E. Review-paper scaffolding (Related Work, taxonomy, PRISMA, appendix)

Two survey/review papers we hold model the **structural furniture** of a good literature section and
appendix — the literature-filtering flowchart, the field taxonomy, the review-of-reviews table, and the
abbreviations list. Study these when building our Related Work (§related) and appendix.

**Review 1 — Manzoor, Qureshi, Kidney & Longo (2024)**, *A Review on ML Methods for Customer Churn
Prediction and Recommendations for Business Practitioners* (ARROW@TU Dublin, Articles 241) →
[`candidates/tudublin_2024_ml_churn_review.pdf`](../references/candidates/tudublin_2024_ml_churn_review.pdf) · bib *(added ✅)*

| Element | What it is | Use |
|---|---|---|
| **Figure 3** | Literature-filtering flowchart — article count + inclusion/exclusion criteria | Template for a PRISMA-style sourcing figure if we add one to Related Work. |
| **Table 6** | List of abbreviations used in the article | Model for an **abbreviations/notation appendix** (pairs with our Notation Reference). |
| **Table 7** | Summary of relevant literature reviews and their contributions to CCP | Format for a compact "review-of-reviews" / prior-surveys table in §related. |

**Review 2 — Imani et al. (2025)**, *Customer Churn Prediction: A Systematic Review of Recent
Advances, Trends, and Challenges in Machine Learning and Deep Learning* (Mach. Learn. Knowl. Extr.
2025, 7, 105) → [`candidates/imani_2025_churn_systematic_review.pdf`](../references/candidates/imani_2025_churn_systematic_review.pdf) · bib *(added ✅)*

| Element | What it is | Use |
|---|---|---|
| **Figure 1 — PRISMA Flowchart** (p. 6) | `837 identified → 679 (journal/conf) → 368 (original + high-quality) → 240 (ML/DL churn) → 61 (deep-review subset)`, two-phase (240 shallow / 61 deep), with an "Excluded" cylinder | **This is the "how many papers did they screen / pick top-N" diagram** you were thinking of. Template + citation for a sourcing funnel. |
| **Figure 12** | Taxonomy of Churn Prediction Approaches | Model for a **taxonomy figure** situating BTYD (structural) vs ML/DL vs conformal in one map — a strong opener for §related. |
| **Table 1** | Summary of studies in the domain of conventional ML | Format for our per-method comparison table (structural vs ML forecasters). |

## F. For our own paper — remember to include (2026-08-10 note)

Prompted by the review papers above (which do these well), our manuscript should carry:

- **A disclaimer** — data-availability + AI-use + conflict-of-interest / funding + a scope/limitations
  caveat, as the venue requires. (The Ulrich paper's acknowledgments/disclosure block is a clean model:
  data provenance + funding + thanks.)
- **Good references** — complete, verified `refs_phase2.bib` (every entry web-confirmed, no fabrications;
  clear the `(to add)` items — Manzoor 2024, Imani 2025, De Caigny 2024, ChurnNet 2026 — before citing).
- **An appendix** — collect the formal derivations (T1/T3), MCMC diagnostics, full parameter grids, an
  **abbreviations/notation list** (à la Manzoor Table 6), and any supporting tables kept out of the body.

---

## G. Carry-through audit — is each element in the paper? (2026-08-11)

Checked against `paper/manuscript_phase2.tex` (v2.0.4, the canonical build; the `_modern`/`_elegant`
builds share its body). **Legend:** ✅ in the paper · ◑ addressed differently / partial · ⬜ not in the
paper (all ⬜ here are *optional* design candidates, not requirements) · N/A not used at this venue.

> **UPDATE — v2.0.5 (2026-08-11): the design candidates below were reproduced into the paper.** The
> rows originally marked ◑/⬜ in §A/§B/§E are now ✅, built in our own Tol palette via
> `src/make_phase2_inspiration_figures.py`:
> **A1** `fig:churnwindow` · **A2** `fig:timeline` · **A3** `fig:architecture` · **A4** `fig:lift` ·
> **B1** `tab:covariate` · **B2/E3/E5** `tab:related` (per-study comparison) · **E2** `fig:prisma` ·
> **E4** `fig:taxonomy`. Still open by choice: **A5** (SBI landscape — folded into the taxonomy) and
> the one requirement gap **F1** (an explicit AI-use statement). The per-row table below is the
> as-of-audit snapshot; this banner is the current state.

### A. Figures / diagrams
| # | Element | Status | Where / note |
|---|---|:--:|---|
| A1 | Churn-window color diagram (Ganeson) | ◑ | Finite-horizon active/churn definition is in prose (§\ref{sec:churn}) and now tied to Ulrich's $R_H$; **no dedicated diagram**. Candidate: a small window schematic. |
| A2 | Per-customer timeline strip for sparsity/regularity (Valendin) | ◑ | Its *goal* ("show why calibration breaks where it does") is met by the **new colored regime-tag table** (`tab:data`, FITS/BREAKS) rather than a timeline strip. |
| A3 | Architecture schematic for amortized MLP / ML (Valendin) | ⬜ | Amortized estimator described in text (App.~`secA:amort`); `fig_p2_amortized` is a bar chart, not a schematic. |
| A4 | Lift-vs-benchmark panel per cohort (Valendin) | ◑ | The **calibration map** (`fig_p2_calibration_map`) is the per-cohort BTYD-vs-ML comparison; not framed as a delta/lift panel. |
| A5 | SBI-landscape positioning (Cranmer) | ◑ | `cranmer2020` cited in §\ref{sec:amortized}; no landscape figure. |
| A6 | ML-CLV reliability/value figure (Chamberlain) | ✅ | `fig_p2_clv` — value calibration, ZILN vs structural CLV. |
| A7 | PIT / reliability / before–after recal plots (Kuleshov) | ✅ | `fig3_pit_histograms` (PIT), `fig_p2_conformal` (before/after), `fig_p2_calibration_map`. Template met. |

### B. Tables
| # | Element | Status | Where / note |
|---|---|:--:|---|
| B1 | Predictors + variable-importance table (Buckinx) | ◑ | Covariate-null result ("demographics add nothing over RFM") stated in text (§\ref{sec:clv}, Discussion); **no predictors/importance table**. |
| B2 | Related-work comparison table (De Caigny) | ⬜ | Related Work is narrative prose; no per-method comparison table. (`decaigny2024` bib entry **added** ✅.) |

### C. Structure / prose
| # | Element | Status | Where / note |
|---|---|:--:|---|
| C1 | Cohesive one-narrative flow (Boukrouh) | ✅ | Paper is written as a single "arc of the mechanism"; matches the monograph-style goal. |

### D. Author bio
| # | Element | Status | Where / note |
|---|---|:--:|---|
| D1 | "About the author" (Gupta) | N/A | Springer `sn-jnl` research articles do not carry author bios. |

### E. Review-paper scaffolding
| # | Element | Status | Where / note |
|---|---|:--:|---|
| E1 | Abbreviations list (Manzoor Table 6) | ✅ | **Appendix `secA:abbrev`** — `tab:abbrev` + `tab:notation` (added v2.0.4). |
| E2 | PRISMA / literature-filtering funnel (Manzoor Fig 3 / Imani Fig 1) | ⬜ | Not in the manuscript. A 185→73 funnel exists in `research-paper-tracker/` but is not drawn in the paper. Optional. |
| E3 | Review-of-reviews table (Manzoor Table 7) | ⬜ | Manzoor + Imani cited as surveys in prose (§\ref{sec:related}); no table. |
| E4 | Taxonomy-of-approaches figure (Imani Fig 12) | ⬜ | No taxonomy figure situating BTYD vs ML/DL vs conformal. Strongest optional addition — would open Related Work well. |
| E5 | Per-method comparison table (Imani Table 1) | ⬜ | Same gap as B2. |

### F. "Remember to include" (the requirement list)
| # | Element | Status | Where / note |
|---|---|:--:|---|
| F1 | Disclaimer block (data + AI-use + COI/funding + scope) | ◑ | Declarations has Funding, COI, Ethics, Consent, **Data availability**, Code availability, Author contributions; §Limitations covers scope. **Missing: an explicit AI-use / generative-AI statement** — the one concrete requirement gap. |
| F2 | Complete verified references, `(to add)` cleared | ✅ | All `(to add)` items **verified + added** (v2.0.3): Manzoor, Imani, Verbraken, De Caigny, ChurnNet, Boukrouh, Ulrich. No fabrications. |
| F3 | Appendix (derivations, MCMC diagnostics, grids, abbreviations, extra tables) | ✅ | Appendices A–G: Gibbs sampler, zero-inflation/noise-floor derivation, conformal recalibration, amortized estimator, **Extended results**, PIT–KS bootstrap null, **Abbreviations+Notation**. MCMC diagnostics present (split-$\hat R\le1.01$, ESS reported; slower $(s,\beta)$ mixing noted, $\hat R$ up to 1.09, ESS $\approx60$; cites Vehtari 2021). |

### Tally & the one real gap
- **Requirements (F): 2 ✅, 1 ◑.** Everything mandatory is done **except an explicit AI-use statement** (F1) —
  author-side content I won't invent; add one line to Declarations (even "No generative AI was used in
  producing the results; [tool] assisted with drafting/editing" per the truth). This is the only
  must-fix.
- **Design candidates (A/B/E): 2 ✅, 5 ◑, 6 ⬜.** Adopted so far: value/PIT/reliability figures (A6–A7),
  the colored regime-tag table (A2 goal), and the abbreviations appendix (E1). Highest-value *optional*
  additions still open: a **taxonomy figure** (E4) and/or a **PRISMA sourcing funnel** (E2) to open
  Related Work; a **related-work comparison table** (B2/E3/E5); a churn-window schematic (A1).

---
*Companion to [`deep_dive.md`](deep_dive.md) and [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md).
All `(to add)` bib items are now added and verified (see §F).*
