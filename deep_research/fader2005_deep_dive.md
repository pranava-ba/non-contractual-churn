---
title: "Fader, Hardie & Lee (2005), *Counting Your Customers the Easy Way* (BG/NBD) — deep-dive"
type: deep-read
created: 2026-08-11
source: "Peter S. Fader, Bruce G. S. Hardie, Ka Lok Lee. Counting Your Customers the Easy Way: An
         Alternative to the Pareto/NBD Model. Marketing Science 24(2) (2005) 275–284.
         DOI 10.1287/mksc.1040.0098. Local: references/phase1/09_fader_2005_bgnbd.pdf"
role: "The BG/NBD variant we show is immaterial to calibration (variant-invariance), and the source of
       the rate–dropout 'good or bad?' open question our dependence-stress test answers."
math: LaTeX. companion: deep_dive.md · corpus_critique.md · LITERATURE_MATRIX.md §2a
---

# Fader, Hardie & Lee (2005), BG/NBD — deep-dive

**Thesis.** The Pareto/NBD is powerful but hard to implement (a difficult likelihood, Gauss hypergeometric
functions). Swap its continuous exponential lifetime for a **beta-geometric dropout that fires after each
purchase**, and you get the BG/NBD — near-identical predictive performance with closed-form expressions
simple enough to estimate in a spreadsheet.

---

## 0. TL;DR — BG/NBD vs. our paper

| Axis | **Fader et al. (2005)** | **Our paper** |
|---|---|---|
| **Contribution** | an *estimation-friendly* Pareto/NBD alternative | uses BG/NBD as the family **variant** in our invariance test |
| **Dropout mechanism** | discrete beta-geometric, *after each purchase* | (we treat both mechanisms as interchangeable for calibration) |
| **Evaluation** | tracking plots, conditional expectations, individual-level correlations | **calibration** (PIT, CRPS, coverage, ECE) |
| **Key open question they pose** | is the purchase–dropout correlation "good or bad"? (left to future research) | **we answer it** — immaterial to calibration over $\rho\in[-0.6,0.6]$ |
| **Relationship** | **the variant we show is immaterial.** Calibration is invariant to Pareto/NBD vs. BG/NBD; and our dependence-stress test settles their explicitly-open question. |

---

## 1. What the paper does
- **The model.** Keep the Gamma–Poisson purchase process of the Pareto/NBD, but replace the continuously-
  running exponential lifetime with a **discrete dropout**: after each transaction the customer becomes
  inactive with probability $p \sim \mathrm{Beta}(a,b)$. Because dropout can only occur *at* a purchase,
  the likelihood collapses to elementary functions — no Gauss hypergeometric — making MLE trivial.
- **A structural quirk they flag.** In the plain BG/NBD a customer who never repeats cannot have dropped
  out (dropout requires a purchase), so **$P(\text{alive})=1$ for one-time buyers** — later repaired by
  the modified BG/NBD (MBG/NBD; Batislam 2007, Hoppe–Wagner 2007), which adds a dropout opportunity at
  time zero.
- **Validation.** They set the field's evaluation norms: aggregate **tracking plots**, **conditional
  expected transactions** by past frequency, and **individual-level correlations** of predicted with
  realized counts — every element grading the *transaction* process (a point Ulrich 2026 later makes about
  why P(alive) itself is never scored).
- **The Gamma–Gamma spend model** is introduced in this lineage to layer a monetary process on the count
  model.

## 2. Novelty
Democratised BTYD: a model with essentially the Pareto/NBD's accuracy but a closed form any analyst can
fit, which is why BG/NBD (and its `lifetimes`/`BTYD` implementations) became the field's workhorse. The
contribution is *tractability without loss*, empirically demonstrated on CDNOW.

## 3. How it differs from our paper
- **They introduce a variant; we use it to prove variants don't matter (for calibration).** Our
  variant-invariance result shows Pareto/NBD and BG/NBD are interchangeable *for forecast calibration* —
  the calibration failure does not depend on which family member is used. So the estimation convenience
  BG/NBD buys is real, and costs nothing in calibration terms, which reframes a long-running
  "which variant?" debate as immaterial.
- **They grade point/tracking accuracy; we grade the predictive distribution.** Same object, different
  lens.
- **We answer their open question.** Fader et al. explicitly write they cannot assess whether the
  rate–dropout correlation is "good or bad" and "hope future research will shed light." Our
  dependence-stress test injects a correlation between the log purchase and log dropout rates from
  $-0.6$ to $+0.6$ and finds calibration essentially unchanged (PIT–KS within 0.022–0.029): in the
  language of calibration, the correlation is *immaterial* — a direct, 20-year-later answer.

## 4. How we use it to improve our paper
- **The family-variant axis (§varinv):** "It does not depend on which member of the family is used:
  Pareto/NBD and BG/NBD are interchangeable" — one of the invariances that make the count assumption *the*
  axis.
- **Answering the open question (§robust):** we now state explicitly that our dependence result settles
  Fader (2005)'s admitted-open rate–dropout question.
- **Cited** for the BG/NBD variant and the Gamma–Gamma spend model; the CDNow cohort (via Fader & Hardie
  2001) is one of our seven, and its one-time-buyer quirk foreshadows our zero-inflation regime.

## 5. Verdict
**Foundational and fully complementary.** BG/NBD is a family member we exercise, not a rival: we show its
convenience is free of calibration cost, and we close a question its authors left open. Nothing about it
competes with our contribution; it strengthens the invariance story and hands us a clean "we answered a
standing question" note.

---
*Part of the deep-dive series. Companion to [`deep_dive.md`](deep_dive.md) and
[`corpus_critique.md`](corpus_critique.md); the MBG/NBD repair of its one-time-buyer quirk is central to
[`ulrich_deep_dive.md`](ulrich_deep_dive.md) §4.2 (BG/NBD's inverted AUC 0.32).*
