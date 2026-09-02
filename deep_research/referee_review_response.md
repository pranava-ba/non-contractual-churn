---
title: "Referee-style review response tracker (Phase-2 manuscript)"
type: review-response
status: in-progress
created: 2026-08-01
source: internal referee-style read of paper/manuscript_phase2.tex
---

# Referee-review response tracker

Captures the detailed referee-style review of the Phase-2 manuscript and tracks the fix for each
item. Status: ✅ done · 🔧 in progress · ○ planned · 💬 needs a decision.

## A. Fix before submission (blockers)

| # | Item | Status | Resolution |
|---|---|:--:|---|
| A1 | **M2 sentence self-contradicts** (§8.4 says the ML survival model is both "left to future work" and "we found competitive but not superior") | ✅ | Promoted the ML-hazard result into a new §7.9 table (data already in `ml_timing_summary.csv`); rewrote the §8.4 clause so it references the reported result, not future work. Strengthens the timing contribution: Pareto/GGG beats the ML survival model on the regular cohorts. |
| A2 | **"Companion calibration study" never cited** (Intro leans on it twice) | ✅ | Added a self-citation `phase1` ("working paper") to `refs_phase2.bib` and cited it at both Intro mentions. |

## B. Numbers to reconcile

| # | Item | Status | Resolution |
|---|---|:--:|---|
| B1 | **Table 2 PIT-KS systematically higher** than the same cohort's value in Tables 4/5/7/8/F4 | ✅ | Root cause found: Table 2 scores the **30% held-out test split** (to match the supervised ML setup) while e.g. the amortized table scores the full cohort. The KS statistic's floor scales as 1/√n, so a smaller sample reads systematically higher under identical calibration — not a stale pipeline. Added a footnote to Table 2 explaining this and directing cross-table comparisons to a fixed sample. |
| B2 | Abstract "a fifth to a third" overstates the top end (actual Table 12: 17.6% / 23.4% / 28.1%) | ✅ | Changed to "a sixth to a quarter." |

## C. Move from Discussion (§8) into Results (§7) with a table + method

| # | Item | Status | Resolution |
|---|---|:--:|---|
| C1 | **Profit (V2)** — 88% vs 66% of oracle, no stated cost/margin | ✅ | Promoted to §7 (`sec:profit`, `tab:profit`) with the economics stated (margin M=1, break-even c/M) and a **sensitivity sweep over three contact costs**; §8.2 now references it. |
| C2 | **Segment tenure (F3)** — 1.8/2.5 quarters, no estimator/CI/seeds | ✅ | Promoted to §7 (`sec:tenure`) with the geometric estimator named and **95% customer-bootstrap CIs** (CDNow 1.76 [1.64,1.82]; Grocery 2.52 [2.34,2.80]); §8.2 references it. |

## D. Sharpest follow-up test — seasonal-conformal

| # | Item | Status | Resolution |
|---|---|:--:|---|
| D1 | Does the *static* conformal warp actually fix the *calendar-conditional* seasonal bias (Fig 8, r=+0.93)? | ✅ | `run_seasonal_conformal.py` (§robust, `tab:seasconf`). Nuanced result confirming **both** readings: **per-window** conformal (the paper's procedure, learned on same-season data) largely flattens it (r 0.94→0.43, ratios→0.88–1.05); a **frozen** warp (calendar-blind) does nothing (r stays 0.94). So the single-mechanism story holds for the procedure used, and your concern is exactly right for a static warp — recalibration must be refreshed each period; a residual (r=0.43≠0) motivates a time-aware model as the clean long-run fix. |

## E. Smaller catches

| # | Item | Status | Resolution |
|---|---|:--:|---|
| E1 | Laplace called "cheap middle tier" but is the slowest route in Table 14 | ✅ | Scoped the wording to "cheap in principle" and noted this implementation inherits the optimiser + Hessian cost. |
| E2 | R-hat/ESS claimed monitored (App A) but never reported | ✅ | Ran `convergence.py`; added the honest result to Appendix A. Purchase-rate params + behavioural means converge cleanly (R-hat ≤1.02); the dropout shape/scale (s,β) mix slowly (CDNow R-hat ≤1.09, ESS ≈62) — the known Pareto/NBD dropout near-non-identifiability — **but the forecast scores are reproducible across chains to Monte-Carlo error** (CDNow CRPS 0.384±0.0004), so no reported number is affected. Stronger than a bare "max R-hat" claim. |
| E3 | Table 4 real-cohort rows omit a seed count | ✅ | Added "single evaluation per real cohort" note. |
| E4 | Table 11 (Top-10%) omits Ta-Feng (64.7% active) with no reason | ✅ | Added a one-line note (short span / window mismatch). |
| E5 | eq. (3) vs §7.7: Table 10 "BTYD P(active)" is the posterior-predictive P(x*>0), not eq. (3) directly | ✅ | Added a clarifying sentence. |
| E6 | "BTYD" overloaded (family vs "Pareto/NBD via MCMC" column) | ✅ | Relabelled the count/variant table columns to "Pareto/NBD." |

## F. Follow-up effort (value-per-hour order)

| # | Item | Status |
|---|---|:--:|
| F1 | Extend the timing repair (Table 12) to Dunnhumby, Online Retail II, Ta-Feng | ✅ (negative) | `run_timing_dense.py`. **Result contradicted the hypothesis:** GGG ties/loses on all three (k̂≈1.5 — mild regularity; "dense"≠"regular"); Ta-Feng pathological (likely short-horizon artifact). Did **not** add a table; instead added an honest one-line qualifier to §timing (advantage is regularity-dependent) — makes the claim more precise and pre-empts the test. |
| F2 | Stack the two repairs: conformal recalibration on top of Pareto/GGG timing | ✅ (positive) | `run_timing_stack.py`. **Strong positive:** conformal on the GGG wait predictive improves MdAE+CRPS on all three (Sim-k3 3.26→2.68, Grocery 2.77→2.50) and **rescues CDNow's "too inaccurate" case (104→10 weeks)**. Added as §"Stacking the two repairs" (`tab:stack`) — the model-agnostic repair generalises to timing; the two repairs are complementary. |
| F3 | Report amortized training cost + a break-even N | ✅ | Added to §cost: training 98s; per-fit saving over MCMC ~0.6s at N=8000 (the individual augmentation, needed by both, dominates), so break-even ≈150 fits — worthwhile at scale/frequency, not for a one-off. Honest, not oversold. |
| F4 | Extend the covariate-null test (value-only) to counts and churn | ✅ | `run_covariate_targets.py`. Count target: demographics add nothing over RFM (PIT-KS 0.207 vs 0.205, p=0.38) — null generalises. Churn target degenerate on the demo subset (100% active), reported honestly. Added to §clv. |
| F5 | Full conformal-on-ML table (not just the Poisson-GBM spot-check) | ✅ | Promoted the M3 spot-check into `tab:conformalml` (Poisson-GBM + Quantile-GBM raw→recal across 4 cohorts): recalibration repairs the parametric ML, leaves the distribution-free one untouched. (Conformal-on-timing is covered by the F2 stacking table.) |
| F6 | Expand amortized-vs-MCMC held-out set (n=25 → 50) | ✅ | Re-ran with N_HELDOUT=50; TOST still EQUIVALENT (CRPS +0.35% [−0.12,+0.82]); updated Table 4, the TOST table, the prose, and the figure. The surprising "forward pass ≈ full MCMC" claim now rests on 50 cohorts. |
| F7 | Cite the simulation-based-inference literature (Cranmer et al.) for the amortized estimator | ✅ | Verified `cranmer2020` (PNAS 117(48):30055–30062); added to `refs_phase2.bib` and cited in §amortized. |
| F8 | Source a genuinely Indian non-contractual retail dataset if one exists at customer granularity | ○ | Needs sourcing — a real decision, deferred to the user. |
