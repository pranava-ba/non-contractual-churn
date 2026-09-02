---
title: "Simon (2025), *A generalised comparison of Pareto/NBD-based forecasts* — deep-dive"
type: deep-read
created: 2026-08-11
source: "Lena Simon (Univ. Duisburg-Essen), A generalised comparison of Pareto/NBD based forecasts using
         MCMC, maximum likelihood, and heuristics. Journal of Business Economics (2025) 95:1079–1104.
         DOI 10.1007/s11573-025-01237-8. Local: references/phase1/14_simon_2025_generalised_comparison.pdf"
role: "OUR SOURCE PAPER — the paper Phase 2 extends. Its four tasks, its gaps, and its verdicts define
       what we replicate, replace, and overturn."
math: LaTeX. companion: deep_dive.md · corpus_critique.md §1b · LITERATURE_MATRIX.md
---

# Simon (2025) — deep-dive (our source paper)

**Thesis.** The first *generalised* comparison of Pareto/NBD-based forecasts: three estimators
(MCMC, MLE, heuristic) across four managerial tasks (counts, active-customer identification, top-$A\%$
ranking, next-purchase timing), on simulated + proprietary empirical data, graded by point error and
classification accuracy. Verdict: model-based beats heuristics on the first three tasks; MCMC is
marginally better than MLE and adds confidence intervals; **the timing forecast's deviations are "too
large to be used in practice."**

---

## 0. TL;DR — Simon vs. our paper

| Axis | **Simon (2025)** | **Our paper** |
|---|---|---|
| **What varies** | the **estimator** (MCMC / MLE / heuristic) | the **model** (structural BTYD vs. ML) |
| **What is fixed** | the model (Pareto/NBD) | the lens (calibration) |
| **Evaluation** | **point error** (nMAE, nRMSE, nMdAE) + classification (sensitivity/precision/accuracy) | **calibration** — proper scoring (CRPS), randomized PIT, coverage, ECE |
| **Targets** | counts, active, top-$A\%$, timing (four tasks) | the *same four*, adopted directly |
| **Timing verdict** | "too large to be used in practice" | **overturned** — Pareto/GGG cuts timing error a sixth–quarter where buying is regular |
| **Cost stance** | MCMC "slightly better," implicitly the premium option | MCMC sits on the accuracy–cost frontier — *not* the costly option |
| **Data** | simulated + **proprietary** empirical (Gusto, Homeshopping) | **7 public** cohorts (replicable) |
| **Active definition** | the **validatable** one (purchases in the window), which she argues is the practically correct one | inherited directly ($P(x^{*}>0)$ = her validatable definition = Ulrich's $R_H$) |
| **Relationship** | **the paper we extend.** We adopt her tasks, replace her evaluation with calibration, add the model axis she holds fixed, and refute two of her verdicts (timing, cost). |

---

## 1. What the paper does

### 1.1 The four tasks (§2) and the estimators
For each customer she forecasts, over prediction windows $T^{*}\in\{13,26,52\}$ weeks:
1. **Purchase forecast** (§2.1): the future number of repeat purchases $x^{*}$, via four routines —
   **SPP** (summed posterior predictive, the MCMC point estimate = median of forward-simulated draws),
   **ICE** (individual conditional expectation, the closed-form $E[x^{*}\mid\cdot]$), **MLE** (with a
   bootstrap sample to give a distribution), and a **heuristic** (frequency scaled by lifetime).
2. **Active-customer identification** (§2.2): classify who makes $\ge 1$ purchase in $T^{*}$, choosing a
   cut-off on the predicted count.
3. **Future top-$A\%$ customers** (§2.3): rank by predicted purchasing and take the top decile/segment.
4. **Timing of the next purchase** (§2.4): forecast $t_{x+1}$, the time of the next transaction, by
   plugging the median of the (assumed exponential) inter-purchase time.

### 1.2 Data and estimation (§3)
Simulated cohorts over a behavioural parameter grid (Table 2) plus a set of **proprietary empirical
data sets** (Table 3). Parameter estimation by a data-augmentation **MCMC (Gibbs) sampler** (slice
updates for $\{r,\alpha\}$ and $\{s,\beta\}$; the algorithm is given in her appendix), **MLE** with
bootstrap, and heuristics.

### 1.3 Findings (§4–5)
- **Counts (§4.1):** graded by normalised MAE / RMSE / median-APE. Model-based beats the heuristic;
  MCMC $\ge$ MLE; MCMC additionally supplies confidence intervals.
- **Active (§4.2):** MCMC *underestimates* $x^{*}$, so SPP/ICE have low **sensitivity** (they classify
  active customers as inactive) but high **precision**; net, MCMC gives the highest fraction correctly
  assigned. CDNow's poor sensitivity (SPP 29.4%, ICE 42.8%) is explained by 12.6% of customers making
  *exactly one* purchase in the window — a very high single-purchaser share.
- **Top-$A\%$ (§4.3):** model-based ranking identifies the future best customers well.
- **Timing (§4.4):** deviations "too large to be used in practice."
- **The active-customer definition (§5)** — her sharpest methodological point: prior studies (Simon &
  Adler 2022; Batislam 2007; Wübben & Wangenheim 2008; Schmittlein 1987) define "active" *solely on the
  dropout process* (i.e. $P(\text{alive})$), which is "misleading in practice"; she scores the
  **validatable** definition instead — whether the customer actually purchases within the window.

### 1.4 The research gaps she names (§1, Table 1)
Prior work used the future-purchase count mainly for goodness-of-fit comparison of models (Fader 2005;
Bachmann 2021; Bemmaor–Glady 2012; Platzer 2021; Valendin 2022); Simon & Adler (2022) gave point
deviations but no empirical validation and no confidence intervals. *"The magnitude of the expected
deviation is of major interest for practitioners but has not yet been subject of research."* Her paper
fills the estimator-comparison + empirical-validation gap.

## 2. Novelty
The **first generalised** head-to-head of the three estimation routes across all four managerial tasks,
with empirical validation and confidence intervals — where prior work compared models on a single task
(usually counts) for goodness-of-fit. She also foregrounds the *validatable* active-customer definition
over the latent-dropout one — the same distinction Fader-Hardie-Shang (2010) and, later and formally,
Ulrich (2026) make.

## 3. How it differs from our paper

She and we ask **orthogonal questions on the same tasks**:
- **She fixes the model, varies the estimator.** Her headline is "does the Bayesian estimator earn its
  cost?" (answer: marginally, plus intervals). **We fix the lens (calibration) and vary the model** —
  structural BTYD vs. ML — asking whether flexibility buys better-*calibrated* forecasts.
- **She grades point error and classification accuracy.** These are, by construction, blind to the
  predictive distribution — the exact gap our paper is built on. Her active-customer study reports
  sensitivity/precision at a chosen cut-off; ours reports the *calibration* of $P(x^{*}>0)$ (ECE, Brier,
  reliability diagrams) with no cut-off.
- **She declares timing hopeless; we overturn it.** Her timing forecast plugs the median of an *assumed
  exponential* inter-purchase time; replacing that with the Gamma inter-purchase time of Pareto/GGG
  (Platzer 2016) cuts median timing error by a sixth to a quarter wherever buying is regular — exactly
  the pattern our count-assumption mechanism predicts. Her "too inaccurate to use" becomes "too
  inaccurate *for the exponential assumption*."
- **She frames MCMC as the premium option; we show it is not.** Our cost study puts the vectorised
  sampler on the accuracy–cost frontier: because every estimation route calibrates alike, the choice
  among them is cost, and full Bayesian inference need not be traded away.
- **Her empirical data are proprietary (Gusto, Homeshopping); ours are seven public cohorts** — directly
  answering the replicability half of the field's dataset gap (cf. Manzoor 2024 Gap 1).

## 4. How we use it to improve our paper
- **The motivating spine.** She *is* our Related Work anchor: "the most recent and most directly relevant
  benchmark… we adopt her four tasks but replace her boxplot-and-point-error evaluation with a
  probabilistic one, and add the model axis she holds fixed."
- **Two refutations we cite her for:** timing (§timing overturns her "too inaccurate" verdict) and cost
  (§cost overturns the received "MCMC is the expensive option to avoid" she voices).
- **The validatable active definition.** We inherit it wholesale ("Following Simon we score the
  validatable definition… rather than the classical, unobservable $P(\text{alive at }T)$"), and it is the
  bridge to Ulrich's $R_H$.
- **Her single-purchaser observation** (CDNow's 12.6% one-and-done) prefigures our zero-inflation /
  sparse-regime findings; worth a one-line nod if we expand the churn discussion.

## 5. Verdict
**Foundational, fully engaged, no tension.** Simon defines the arena; we change the lens and the axis.
Every one of her four tasks is a target in our paper; two of her verdicts (timing, cost) we overturn and
cite; her one methodological reform (the validatable active definition) we adopt. She is the reason the
paper exists, and nothing in her results competes with ours — they are complementary by construction.

---
*Part of the deep-dive series. Companion to [`deep_dive.md`](deep_dive.md),
[`corpus_critique.md`](corpus_critique.md) §1b, and [`ulrich_deep_dive.md`](ulrich_deep_dive.md) (the
validatable-active definition is the bridge between the two).*
