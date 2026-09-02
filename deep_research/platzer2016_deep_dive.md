---
title: "Platzer & Reutterer (2016), *Ticking Away the Moments* (Pareto/GGG) — deep-dive"
type: deep-read
created: 2026-08-11
source: "Michael Platzer, Thomas Reutterer. Ticking Away the Moments: Timing Regularity Helps to Better
         Predict Customer Activity. Marketing Science 35(5) (2016) 779–799. DOI 10.1287/mksc.2015.0963.
         Local: references/phase1/17_platzer_reutterer_2016_pareto_ggg.pdf"
role: "The structural model behind our TIMING repair (Repair II). Its regularity parameter k is exactly
       what our next-purchase-timing forecast exploits to overturn Simon's 'timing is hopeless' verdict."
math: LaTeX. companion: deep_dive.md · corpus_critique.md · LITERATURE_MATRIX.md §2a
---

# Platzer & Reutterer (2016), Pareto/GGG — deep-dive

**Thesis.** The Pareto/NBD assumes memoryless (exponential) inter-purchase times, which throws away
*timing regularity*. Replacing the NBD count component with a **Gamma mixture of Gamma inter-purchase
times** (the "GGG") lets each customer have a regularity level $k$; using that regularity sharply improves
inferences about latent activity — especially for valuable, previously-frequent customers now in a
purchase hiatus.

---

## 0. TL;DR — Platzer/GGG vs. our paper

| Axis | **Platzer (2016)** | **Our paper** |
|---|---|---|
| **Contribution** | a richer *structural* BTYD: adds inter-purchase **regularity $k$** | uses Pareto/GGG as the structural *timing* repair |
| **Their target** | **activity / aliveness** prediction (P(alive)) | next-purchase **timing** (and counts/value/churn) |
| **Evaluation** | out-of-sample activity accuracy, tracking | **calibration** (PIT, CRPS, coverage) + timing error |
| **Key knob** | $k$: $k{=}1$ recovers Pareto/NBD (memoryless), $k{>}1$ = regular buying | the same $k$ is what our timing forecast exploits |
| **Relationship** | **the structural model we repurpose for timing.** They use regularity to sharpen *activity*; we use it to *overturn* the received verdict that BTYD timing is useless. |

---

## 1. What the paper does
- **The model.** Pareto/GGG generalises the Pareto/NBD by **replacing the NBD count component with a
  mixture of Gamma distributions** for the inter-purchase time. Concretely the inter-purchase time is
  $\Delta t \sim \Gamma(k,\,k\lambda)$ with a customer regularity $k$ (mixed over Gamma heterogeneity):
  $k{=}1$ is the memoryless exponential (recovering Pareto/NBD), $k{>}1$ means purchases are *more evenly
  spaced* than Poisson — regular buying.
- **Why regularity helps.** For a regular buyer, a longer-than-usual gap is *strong* evidence of dropout;
  for a memoryless buyer it is not. Modelling regularity therefore "improves inferences about customers'
  latent activity status … especially those valuable customers who were previously very frequently active
  but have recently exhibited a longer purchase hiatus."
- **Estimation.** A data-augmentation **MCMC** sampler (the basis of the widely-used `BTYDplus` R package),
  building on Abe's (2009) hierarchical-Bayes machinery.
- **Descriptive apparatus.** Ties the model to two summary statistics later reused across the field: the
  **Wheat–Morrison regularity $r_{\text{WM}}$** and the **clumpiness $C$** measure (Zhang et al. 2015).
  Empirical findings include that *clumpy customers tend to be more active than regular ones in future
  periods*, and that the model extrapolates beyond the calibration period.

## 2. Novelty
Brings **timing regularity** — long noted descriptively (clumpiness) — into the generative BTYD framework
as an estimable customer-level parameter, and shows it materially improves activity prediction. It is the
canonical "richer purchase process" member of the BTYD family and the reference implementation
(`BTYDplus`) for regularity-aware customer-base analysis.

## 3. How it differs from our paper
- **Their target is activity; ours (for this model) is timing.** They deploy regularity to sharpen
  $P(\text{alive})$; we deploy the *same* $k$ to forecast the *time of the next purchase*, which is the
  task Simon (2025) declared "too inaccurate to use." Same model, different managerial target.
- **They grade point/activity accuracy; we grade calibration.** Platzer evaluates out-of-sample activity
  and aggregate tracking; we bring the model under proper scoring and calibration, and additionally
  measure median timing error.
- **We use it to make a mechanism point, not just a modelling point.** In our framework Pareto/GGG is
  *Repair II*: where the data-generating process is richer than Poisson (regular buying), a richer
  structural model recovers what a misfit assumption loses. It cuts median timing error by roughly a
  sixth to a quarter where buying is regular and ties where buying is memoryless — exactly the pattern the
  count-assumption mechanism predicts, and a direct refutation of Simon's verdict.

## 4. How we use it to improve our paper
- **The timing repair (§timing).** "Replacing the exponential inter-purchase-time assumption with the
  Gamma inter-purchase-time of the Pareto/GGG model cuts median timing error … wherever purchasing is
  regular, and ties where buying is genuinely memoryless."
- **The `k` knob is the decision-rule row** "Timing, regular buying → Pareto/GGG" — matching the process
  beats treating the forecast as hopeless.
- **Implementation + data lineage:** we cite Platzer for the `BTYDplus` package (which ships the Grocery
  cohort) and the Abe (2009) MCMC sampler, and for the regularity/clumpiness statistics that underlie our
  Data-table descriptor chips (with Valendin 2022).
- **Grocery cohort:** one of our seven, drawn from `BTYDplus`.

## 5. Verdict
**A structural building block, fully complementary.** Platzer/GGG is not a competitor but a component: the
richer structural model our paper uses to demonstrate that BTYD timing is not hopeless once the process is
matched. Their regularity insight is the generative reason our timing repair works, and their descriptive
statistics feed our cohort characterisation.

---
*Part of the deep-dive series. Companion to [`deep_dive.md`](deep_dive.md) and
[`corpus_critique.md`](corpus_critique.md); the structural half of our two-repair story (the model-agnostic
half is Conformalized BTYD).*
