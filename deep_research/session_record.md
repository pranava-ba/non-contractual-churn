---
title: "Session record — gap-analysis reconciliation & Phase-2 manuscript hardening"
type: session-log
created: 2026-08-10
covers: reconciliation of the 30-gap inventory to 30/30, construction of the Phase-2 manuscript
        (25 pp -> 40 pp), and a full referee-response cycle. Companion to
        `pareto_nbd_extension_gap_analysis.md` (the master gap table) and
        `referee_review_response.md` (the review tracker).
---

# Session record

A complete, self-contained record of the working session, collapsed for reference. Nothing here is
new work; it consolidates what was done so the reasoning and results survive outside the chat. The
three living documents remain authoritative: the gap table (`pareto_nbd_extension_gap_analysis.md`),
the review tracker (`referee_review_response.md`), and the dated dev log (`CHANGELOG.md`).

---

## 0. Executive summary

The session had three phases:

1. **Reconciliation.** A fresh deep-research gap analysis of Simon (2025) had been generated as if
   from a cold start, but the project's Phase 1–2 work had already executed most of it. We
   cross-checked all **26 original gaps** against the codebase, surfaced **4 new gaps** (G5, E5, F4,
   U3 → 30 total), rewrote the analysis into a status-aware master table + a prioritized tier system,
   and updated ROADMAP / TIMELINE / CHANGELOG.

2. **Closing every gap.** We then implemented the remaining work tier by tier — 6 partials, 6 cheap
   opens, 5 frontier items, and (at the user's request) the 3 originally-parked items — reaching
   **30/30 gaps done**. Every item shipped code + a result + a smoke test.

3. **Writing and hardening the paper.** We folded the findings into the Phase-2 manuscript
   (`paper/manuscript_phase2.tex`), grew it from ~25 pp to **40 pp**, ran a self-generated
   referee-objection pass, then executed a detailed external referee review in four batches. The
   test suite grew **20 → 42**; the manuscript compiles clean with zero undefined references.

**Only open item: F8** (source a genuinely Indian customer-level non-contractual dataset) plus
standard author-side steps (replace the `phase1` placeholder citation when Phase 1 is public, confirm
venue, cover-to-cover proofread).

The source paper being extended: **Simon, L. (2025)**, *A generalised comparison of Pareto/NBD based
forecasts using MCMC, maximum likelihood, and heuristics*, J. Business Economics 95:1079–1105. The
manuscript: *"Non-contractual churn: statistical or machine-learned? A calibration benchmark of
purchase, value, and timing forecasts."*

---

## 1. The 30-gap inventory and its resolution

30 gaps across 8 categories (26 original + 4 surfaced 2026-08-01). Final score: **30 done, 0 open**
(the 3 formerly-parked items were un-parked and completed at the user's request).

| ID | Gap | Result | Module |
|----|-----|--------|--------|
| G1 | BG/NBD + Pareto/GGG in the pipeline | done pre-session | `estimate_bgnbd.py`, `estimate_ggg.py` |
| G2 | Covariate specification | static demographics **and** a new time-varying promo covariate — both immaterial over RFM | `covariate_benchmark.py`, `covariate_timevarying.py` |
| G3 | Monetary/CLV layer | Gamma-Gamma + deep ZILN | `clv.py`, `clv_benchmark.py` |
| G4 | Independence stress-test *(un-parked)* | **robust**: PIT-KS 0.022–0.029, cov95 ~0.98 across ρ∈[−0.6,+0.6] | `run_dependence_stress.py` |
| G5 | CLV discounting *(new)* | per-customer discounting rescales CLV (2–28%) but Top-10% overlap ≥99.8%, rank corr 1.00 | `run_clv_discount.py` |
| E1 | Alternative MCMC sampler (HMC/NUTS) | **HMC ≈ Gibbs** (Sim CRPS 0.406/0.404), acceptance 0.72–0.84 | `hmc.py` |
| E2 | MCMC convergence diagnostics | rate params R-hat ≤1.02; dropout (s,β) mix slowly (CDNow R-hat ≤1.09, ESS ≈62 — known non-identifiability); forecasts chain-reproducible to MC noise | `convergence.py` |
| E3 | Interval/coverage quality | coverage@50/80/95 + Lilliefors bootstrap null | `run_pit_bootstrap.py` |
| E4 | Approximate-Bayes tier (Laplace) | **Laplace ≈ MLE ≈ MCMC** (Sim CRPS 0.403/0.404/0.407) | `laplace.py`, `amortized.py` |
| M1 | ML in-framework | 3 GBM variants + ZILN + classifier | `ml_benchmark.py` |
| M2 | ML survival/hazard for timing | discrete-time hazard; **Pareto/GGG still wins** on regular data | `run_ml_timing_study.py` |
| M3 | Conformal for the ML forecasters | recalibration repairs the parametric Poisson-GBM (Dunnhumby 0.241→0.115), leaves Quantile-GBM untouched | `run_conformal_ml_study.py` |
| U1/U2 | Unified calibration study (PIT) | this is the paper | `score.py` |
| U3 | PIT-KL (planned) vs PIT-KS (shipped) *(new)* | KS justified (binning-free, testable null, field-standard) | `docs/theory_variance_decomposition.md` |
| V1 | Formal hypothesis testing | Wilcoxon + Holm-Bonferroni + **TOST equivalence** | `tost.py` |
| V2 | Cost/profit-linked metric | contact-policy profit as % of oracle, cost sweep | `run_profit_study.py` |
| V3 | Compute-cost table + Pareto frontier | **overturns "MCMC is expensive"** — MCMC on frontier, MLE dominated | `run_cost_benchmark.py` |
| D1 | Extended simulation grid | calibrated at E(λ)≈0.6 and up to **N=50,000** | `run_study.py` (highfreq/largeN grids) |
| D2 | Non-stationarity / seasonality *(un-parked)* | **breaks calibration** (PIT-KS 0.024→0.118) — the one axis that bites; confirmed on real data (r=+0.93) | `run_seasonality_stress.py`, `run_seasonality_real.py` |
| D3 | Censoring / data-quality *(un-parked)* | graceful degradation; downward rate bias | `run_censoring_stress.py` |
| D4 | More empirical datasets | 6 real cohorts (CDNow, Grocery, Online Retail II, Olist, Dunnhumby, Ta-Feng) | `datasets.py` |
| F1 | Rolling / walk-forward | MCMC≈MLE gap ±0.001, calibration stable across cut-points | `run_rolling_study.py` |
| F2 | Individual-vs-cohort decomposition | MCMC≈MLE at every k; heuristic bias floor doesn't average out | `run_aggregation_study.py` |
| F3 | Segment-transition / tenure *(new)* | Top-10% tenure 1.76 [1.64,1.82] (CDNow) / 2.52 [2.34,2.80] (Grocery) quarters | `run_rolling_study.py` |
| F4 | Active-customer definition sensitivity *(new)* | classical P(alive) over-counts active by ~12 pts at 13-wk horizon | `run_active_def_study.py` |
| T1 | Zero-inflation formalization | median-of-draws vs closed-form-mean derivation | `docs/theory_variance_decomposition.md` |
| T2 | Timing fix via Pareto/GGG ⭐ | done pre-session (the analysis's flagship) | `run_timing_study.py` |
| T3 | Bias–variance / noise-floor decomposition | **fixable (estimation) share of CRPS ≈0% even at N=500** | `run_noise_floor.py` |

The 4 newly-surfaced gaps (from cross-checking Simon's own notes against the repo): **G5** (CLV
discounting), **E5** (prior sensitivity), **F4** (active-customer definition sensitivity), **U3**
(PIT-KL vs PIT-KS). E5's result: posterior + calibration **invariant** across vague/informative/
very-diffuse priors — the MCMC≈MLE null is not a prior artefact (`run_prior_sensitivity.py`).

---

## 2. Implementation tiers (how the closing was sequenced)

The reconciliation reprioritized the remaining work into tiers — **finish the partials before opening
anything new** — all completed 2026-08-01.

- **Tier 1 — partials:** `M3 → T1 → T3 → D1 → G2 → E4`. Every result reinforced the thesis
  (calibration governed by the shared count assumption, invariant to estimator/variant).
- **Tier 2 — cheap opens:** `V3 → V2 → F4 → E5 → G5 → U3`. Two new contributions here (V3 cost
  frontier, V2 profit layer); the rest reinforce.
- **Tier 3 — frontier:** `E1 → F1 → F3 → D3 → F2 → M2`. Genuinely new tasks/models.
- **Tier 4 — un-parked:** `G4, D2, D3`. The earlier "stop stress-testing" instinct held for the
  heterogeneity axes (dependence robust), but **D2 (seasonality) is the honest exception** that
  breaks calibration.

**The meta-finding:** widening the aperture across estimators (5 routes), samplers, scale (N→50k),
covariates (static + time-varying), aggregation levels, and misspecification axes did not dent the
core story. The one lever that reliably moves calibration is recalibration (conformal), which now
works for ML too.

---

## 3. The manuscript (25 pp → 40 pp)

The Phase-2 manuscript was written / extended from the findings. Its arc: **diagnosis** (the count
assumption governs calibration) → **invariance** (5 estimation routes + prior + noise-floor theory,
variant) → **two repairs** (model-agnostic conformal — for ML too; structural Pareto/GGG timing) →
**every managerial dimension** (counts, value, churn, timing, Top-A%) → **robustness** (with the
seasonality boundary) → **cost frontier** → **decision layer** (profit, tenure).

### New sections added this session
`sec:robust` (robustness), `sec:cost` (cost frontier), `sec:mltiming` (ML survival competitor),
`sec:stack` (stacking the two repairs), `sec:topa` (Top-A% identification), `sec:profit` (profit),
`sec:tenure` (segment tenure); plus an Appendix on the zero-inflation asymmetry + noise-floor (T1/T3),
and the strengthened estimation-invariance section (E1/E4/E5).

### New tables added this session
`tab:tost` (equivalence), `tab:prior` (prior sensitivity), `tab:robust` (4-axis stress),
`tab:cost` (cost–accuracy), `tab:noisefloor` (CRPS decomposition), `tab:mltiming` (ML hazard timing),
`tab:stack` (repair stacking), `tab:seasconf` (seasonal-conformal), `tab:topa` (Top-A%),
`tab:profit` (profit sweep), `tab:conformalml` (conformal-on-ML).

### New figures added this session
`fig_p2_cost.png` (frontier), `fig_p2_robustness.png` (only seasonality breaks),
`fig_p2_noisefloor.png` (estimation-fixable share ≈0), `fig_p2_seasonality_real.png` (real-data
seasonality r=+0.93). Generator: `src/make_phase2_figures.py`.

### New citations added this session (all web-verified, not fabricated)
- **`valendin2022`** — Valendin, Reutterer, Platzer & Kalcher (2022), *Customer Base Analysis with
  Recurrent Neural Networks*, IJRM 39(4):988–1018 — the RNN-CBA flagship; cited in Related Work, the
  "first" claim, and Limitations.
- **`cranmer2020`** — Cranmer, Brehmer & Louppe (2020), *The Frontier of Simulation-Based Inference*,
  PNAS 117(48):30055–30062 — situates the amortized estimator in the SBI literature.
- **`phase1`** — self-citation to the companion Phase-1 calibration study (working-paper placeholder,
  to be replaced when Phase 1 is public).

### The cost claim, stated at the robust level
V3 found MCMC on the cost–accuracy frontier and the MLE plug-in dominated. Even a **single-start** MLE
(9.2 s at N=8000) is slower than the vectorised Gibbs MCMC (2.6 s) — the Nelder–Mead optimisation of
the hypergeometric likelihood is intrinsically costly, so it is not merely the multistart hardening.
The paper states the **robust** claim ("MCMC is not the costly route") and keeps the honest caveat
that a compiled/gradient optimiser would be faster.

---

## 4. Reviewer-objection hardening (self-generated pass)

Before the external review, a self-generated referee-objection list (3 tiers, ~15 items) was
produced and addressed:

- **Tier 1 (decisive):** equivalence needs TOST (→ `tab:tost`, all 3 claims EQUIVALENT); density
  confound (→ identification strategy made explicit in §mechanism: causality carried by simulation +
  the ML mechanism test, the 6-cohort gradient only corroborates); supervised-ML vs unsupervised-BTYD
  info asymmetry (→ fairness paragraph: the asymmetry favours ML yet structure still wins sparse, and
  Conformalized BTYD is the like-for-like); cost implementation-dependence (→ single-start MLE added;
  strengthened the claim).
- **Tier 2:** multiple comparisons (Holm-Bonferroni statement); novelty vs Phase 1 + "first" claim
  (rescoped to the calibration lens); "variant immaterial" near-circular (reframed as a falsifiable
  consistency check); conformal not novel (repositioned as the diagnosis, not the algorithm); ML
  under-tuning (→ `run_ml_tuning.py`: PIT-KS spread ≤0.017 ≪ the gap, verdict tuning-invariant);
  single sim DGP (cite the broader grid).
- **Tier 3:** PIT-KS threshold (bootstrap null referenced); windows cherry-picked (rolling stability).

---

## 5. Detailed external referee review — response (4 batches)

The user provided a close, referee-style read (scorecard 22/26 + specific fixes). All items closed
except F8. Tracker: `referee_review_response.md`.

### Batch 1 — blockers + small catches (→ 36 pp)
- **M2 self-contradiction (blocker):** the ML survival model was described as both "future work" and
  "already tested." Promoted the result into **§7.9 `tab:mltiming`** (using existing data), showing
  Pareto/GGG beats the ML hazard on every regular cohort (Grocery 3.38 vs 4.21, Sim-k3 3.89 vs 6.07,
  CDNow 101.9 vs 107.6). Rewrote §8.4.
- **Companion study uncited (blocker):** added the `phase1` self-citation at both Intro mentions.
- **R-hat:** ran `convergence.py`, reported the honest result in Appendix A (rate params converge;
  dropout (s,β) mix slowly — CDNow R-hat ≤1.09 — but forecasts are chain-reproducible to MC noise,
  CRPS 0.384±0.0004).
- **Ta-Feng added to Top-A%** (`tab:topa`; 64.7% active, so its omission needed fixing not excusing);
  Olist exclusion justified (1.6% active → degenerate top decile).
- **Small catches:** abstract "a fifth to a third" → "a sixth to a quarter"; Laplace "cheap"
  reconciled with its Table-14 cost; BTYD-vs-Pareto/NBD terminology defined; Table-4 seed count noted;
  eq.-(3)-vs-posterior-predictive-P(x*>0) clarified in the churn section.

### Batch 2 — the sharpest test + §8→§7 promotions (→ 38 pp)
- **Seasonal-conformal test (the referee's sharpest follow-up):** does a static conformal warp fix
  the calendar-conditional seasonal bias? Result validates **both** readings: **per-window** conformal
  (the paper's procedure, learned on same-season held-out data) flattens the bias (r 0.94→0.43, ratios
  → 0.88–1.05), but a **frozen, calendar-blind** warp does nothing (r stays 0.94). Lesson: recalibrate
  each period; the residual (r=0.43≠0) motivates a time-aware model as the clean long-run fix.
  (`run_seasonal_conformal.py`, `tab:seasconf`.)
- **Profit (V2) promoted §8→§7** (`sec:profit`, `tab:profit`): economics stated (margin M=1,
  break-even c/M) + a contact-cost sensitivity sweep. Pattern mirrors the calibration map.
- **Tenure (F3) promoted §8→§7** (`sec:tenure`): geometric estimator named + 95% customer-bootstrap
  CIs.
- **Table-2 discrepancy resolved:** root cause is that Table 2 scores the 30% held-out split (KS floor
  ~1/√n reads higher on smaller n), not a stale pipeline — footnoted.

### Batch 3 — follow-up experiments F1, F2, F7 (→ 39 pp)
- **F1 (extend timing to dense cohorts): NEGATIVE, reported honestly.** Pareto/GGG ties/loses on
  Dunnhumby, Online Retail II, Ta-Feng — estimated regularity is only mild (k̂≈1.5; "dense" ≠
  "regular"), and Ta-Feng is pathological (likely a short-horizon artefact). Did **not** force a table;
  added a one-line qualifier to §timing that the advantage is regularity-dependent — sharpens the
  claim and pre-empts the exact test.
- **F2 (stack the repairs): STRONG POSITIVE.** Conformal recalibration of the Pareto/GGG wait-time
  predictive improves MdAE + CRPS on all three cohorts and **rescues CDNow's archetypal "too
  inaccurate to use" case (median error 104 → 10 weeks)**. Added as §"Stacking the two repairs"
  (`tab:stack`). Together F1+F2 tell a coherent story: the structural fix is limited to regular
  processes; the model-agnostic fix is general and stacks on top.
- **F7 (Cranmer citation):** verified + added.

### Batch 4 — remaining follow-ups F3–F6 (→ 40 pp)
- **F3 amortized break-even** (§cost): training 98 s; per-fit saving over MCMC ~0.6 s at N=8000, so
  break-even ≈150 fits — worthwhile at scale/frequency, not for a one-off. Stated honestly.
- **F4 covariate null → counts & churn** (`run_covariate_targets.py`): on the count target,
  demographics add nothing over RFM (PIT-KS 0.207 vs 0.205, p=0.38) — the null generalises; churn is
  degenerate on the demo subset (100% active), reported as such.
- **F5 full conformal-on-ML table** (`tab:conformalml`): promoted the M3 spot-check.
- **F6 amortized held-out set 25 → 50**: TOST still EQUIVALENT (CRPS +0.35% [−0.12,+0.82]); refreshed
  Table 4, the TOST table, §estinv prose, and the amortized figure.

---

## 6. Key numerical results (the ones the paper turns on)

- **Calibration map (counts, PIT-KS, 30% test split):** structure best on sparse (Simulated 0.042,
  Grocery 0.045); breaks on dense (Dunnhumby 0.169, Online Retail II 0.211); distribution-free
  Quantile-GBM wins where BTYD breaks (0.058, 0.042).
- **Estimation invariance (TOST, ±5% CRPS / ±0.02 PIT-KS margins):** MLE≈MCMC (−0.33% [−0.65,−0.01]),
  Pareto/NBD≈BG/NBD (−0.23% [−0.37,−0.09]), Amortized≈MCMC (+0.35% [−0.12,+0.82], n=50) — all EQUIVALENT.
- **Noise floor (T3):** fixable (estimation) share of CRPS ≈0% even at N=500.
- **Conformal repair (BTYD):** Online Retail II 0.212→0.044, Dunnhumby 0.164→0.097 (p<0.001); no harm
  where already calibrated (Grocery 0.036→0.036).
- **CLV:** deep ZILN better calibrated than BTYD+GG (Online Retail II 0.212→0.031); demographics add
  nothing over RFM (p=0.77 value; 0.38 counts).
- **Churn ECE:** BTYD wins where assumptions hold (Simulated 0.027 vs ML 0.047), ML wins on dense
  (Online Retail II 0.185 vs 0.051).
- **Timing (structural):** Pareto/GGG cuts MdAE ~a sixth to a quarter where regular (Grocery 3.89→2.98,
  Sim-k3 4.49→3.23); regularity-dependent (no gain on dense k̂≈1.5 cohorts).
- **Timing (stacked):** GGG + conformal rescues CDNow 104 → 10 weeks.
- **Robustness:** robust to dependence (ρ∈[−0.6,0.6]), censoring (0–30%), scale (N→50k), frequency
  (E(λ)≈0.6); **breaks only under seasonality** (PIT-KS 0.024→0.118; real-data r=+0.93).
- **Cost frontier (N=8000):** heuristic 0.001 s / CRPS 1.285; Poisson-GBM 0.72 / 0.441; Amortized
  2.00 / 0.400; MCMC 2.62 / 0.397 (on frontier); MLE 1-start 9.16 / 0.398 and multistart 18.81 /
  0.399 and Laplace 18.55 / 0.398 (dominated).
- **Profit (% of oracle, c=1.0):** Simulated BTYD 88 vs heuristic 66; Online Retail II heuristic/GBM
  72/76 > BTYD 60 (dense, miscalibrated).
- **Top-10% identification (hit rate):** BTYD best-or-tied everywhere, incl. dense cohorts where its
  intervals miscalibrate (ranking robust where calibration is not).
- **Segment tenure:** CDNow 1.76 [1.64,1.82], Grocery 2.52 [2.34,2.80] quarters.

---

## 7. Artifacts produced this session

### New `src/` modules (23)
`covariate_timevarying.py` (G2), `laplace.py` (E4), `run_noise_floor.py` (T3),
`run_conformal_ml_study.py` (M3), `run_cost_benchmark.py` (V3), `run_profit_study.py` (V2),
`run_active_def_study.py` (F4), `run_prior_sensitivity.py` (E5), `run_clv_discount.py` (G5),
`hmc.py` (E1), `run_dependence_stress.py` (G4), `run_seasonality_stress.py` (D2),
`run_rolling_study.py` (F1+F3), `run_censoring_stress.py` (D3), `run_aggregation_study.py` (F2),
`run_ml_timing_study.py` (M2), `tost.py`, `run_ml_tuning.py`, `run_topa_study.py`,
`run_seasonality_real.py`, `run_seasonal_conformal.py`, `run_timing_dense.py`, `run_timing_stack.py`,
`run_covariate_targets.py`. **Modified:** `run_study.py` (highfreq/largeN grids),
`run_amortized_check.py` (raw output + N_HELDOUT 25→50), `make_phase2_figures.py` (+3 figures).

### New `results/*_summary.csv`
active_def, aggregation, censoring_stress, clv_discount, conformal_ml_study, cost_benchmark,
covariate_targets, dependence_stress, ml_timing, ml_tuning, noise_floor, prior_sensitivity, profit,
rolling, seasonal_conformal, seasonality_real, segment_tenure, timing_dense, timing_stack, topa, tost.

### Tests
`tests/test_phase2.py`: **20 → 42** passing (added smoke tests for every new capability).

### Docs / logs
`docs/theory_variance_decomposition.md` (T1 derivation, T3 decomposition, U3 note);
`deep_research/pareto_nbd_extension_gap_analysis.md` (status-aware master table, §3.0 tiers, §3.9 new
gaps); `deep_research/referee_review_response.md` (review tracker); `CHANGELOG.md` (full dated log);
`ROADMAP.md` / `TIMELINE.md` (reconciled). `github_upload_bundle/` + zip re-synced after root edits.

---

## 8. Interlude — dataset & scope assessment

When asked whether the datasets (7 cohorts: 1 simulated + 6 real, active rates 1.6%–96%) and the four
forecast dimensions were sufficient:

- **Datasets:** the panel is strong (Simon used 4; the field often uses 1–2) and the 50× activity
  range is its key strength. Real gaps: all retail/e-commerce; seasonality then only in simulation
  (since addressed on real data — Online Retail II); monetary on 3 cohorts. Recommended: real-data
  seasonality (done) and a non-retail vertical (open).
- **Four dimensions (counts/value/churn/timing):** the canonical complete set for non-contractual CBA;
  we exceed Simon's four by adding value/CLV. Recommended surfacing Top-A% explicitly (done) and
  multi-period CLV as future work.

---

## 9. Final state & open items

**Manuscript:** `paper/manuscript_phase2.tex`, **40 pp**, compiles clean via `latexmk`, zero undefined
references; every new table verified against its source CSV; two style variants regenerated. The
`paper/` tree is git-ignored (a separate deliverable), so its contents are not in the bundle.

**Everything in the gap analysis and the referee review is addressed except:**

- **F8** — source a genuinely Indian customer-level non-contractual dataset (a real-world data hunt),
  or present the current US/UK/Brazil/Taiwan spread as-is. *(User decision.)*

**Author-side pre-submission steps (cannot be completed without the author):**

- Replace the **`phase1`** working-paper placeholder with the real Phase-1 reference once it is public
  (and anonymize for review).
- Confirm the **venue** (scaffold defaults to JBE / Springer `sn-jnl`).
- A **cover-to-cover proofread** for flow/tone across the ~50 incremental additions.

**Optional (offered, not required):** refresh the **abstract / contributions** to name the newest
headline results — the seasonality boundary (the one honest caveat of the central claim) and the
repair-stacking rescue — which currently live in the body but not the abstract.
