---
title: "Imani, Joudaki, Beikmohammadi & Arabnia (2025), *Customer Churn Prediction: A Systematic Review* — deep-dive"
type: deep-read
created: 2026-08-11
source: "Mehdi Imani, Majid Joudaki, Ali Beikmohammadi, Hamid Reza Arabnia. Customer Churn Prediction: A
         Systematic Review of Recent Advances, Trends, and Challenges in Machine Learning and Deep Learning.
         Machine Learning and Knowledge Extraction 7(3) (2025) 105. DOI 10.3390/make7030105.
         Local: references/candidates/imani_2025_churn_systematic_review.pdf"
role: "Field survey #2 — a PRISMA-registered systematic review. Corroborates that the churn-ML literature
       omits both BTYD and calibration; its funnel/taxonomy figures are structural models for our own."
math: LaTeX. companion: deep_dive.md · corpus_critique.md · LITERATURE_MATRIX.md §2f
---

# Imani et al. (2025) — deep-dive (field review #2)

**Thesis.** A **PRISMA-2020 systematic review** of machine- and deep-learning churn prediction (2020–2024;
six databases searched via Lens.org; a two-phase screen of **240 studies** for bibliometric analysis and
**61** for deep qualitative synthesis). It maps the field's trends and challenges and — for our purposes —
does so without ever mentioning BTYD or probability calibration.

---

## 0. TL;DR — Imani vs. our paper

| Axis | **Imani (2025)** | **Our paper** |
|---|---|---|
| **Type** | PRISMA systematic review (240 / 61 studies) | a specific BTYD-vs-ML calibration extension |
| **Method rigor** | registered protocol, two-phase screen, taxonomy | multi-seed experiments, calibration lens |
| **Named challenges** | class imbalance, interpretability, **concept drift**, limited profit metrics | our repairs target exactly the non-stationarity + calibration axes |
| **BTYD coverage** | **zero** | half the comparison |
| **Calibration** | **zero mentions** | the whole lens |
| **Relationship** | **independent corroboration + structural templates.** The field's own 2025 synthesis reaches profit and drift but not calibration, and never touches the structural BTYD tradition. |

---

## 1. What the review does
- **Protocol.** PRISMA 2020; six databases (Springer, IEEE, Elsevier, MDPI, ACM, Wiley) via Lens.org;
  peer-reviewed original ML/DL churn studies only (reviews, preprints, non-peer-reviewed excluded);
  **two-phase** design — 240 studies for bibliometric/shallow analysis, 61 for deep synthesis; registered
  retrospectively in OSF.
- **Findings.** Ensemble methods (XGBoost, LightGBM) remain dominant in ML; DL (LSTM, CNN) increasingly
  applied to complex data. **Named challenges: class imbalance, interpretability, concept drift, and
  *limited use of profit-oriented metrics*.** Explainable AI and adaptive learning show potential but
  limited real-world adoption. Study heterogeneity prevented meta-analysis; no formal risk-of-bias
  assessment.
- **Structural furniture.** A **PRISMA sourcing funnel** (Fig. 1: identified → screened → included), a
  **taxonomy of churn-prediction approaches** (Fig. 12), and a per-method comparison table (Table 1) — all
  models for how a good Related Work / appendix is built.

## 2. Novelty / value
A current (2025), protocol-driven map of the churn-ML field with a defensible sourcing funnel and taxonomy
— the authoritative "state of the field" a specific paper can cite to establish what is and is not being
done. Its recency makes it the strongest single evidence of what the field, *as of 2025*, still omits.

## 3. How it differs from our paper
- **Survey vs. experiment.** It synthesises the literature; we run a controlled multi-cohort experiment.
- **Its challenge list stops short of our lens.** It reaches *concept drift* (our non-stationarity axis)
  and *limited profit metrics* (our §profit) and *interpretability* (our XAI paragraph) — but **never
  reaches probability calibration**. The field's own 2025 systematic review does not raise the metric our
  paper is built on.
- **No BTYD.** Full-text search returns 0 mentions of Pareto/NBD, BTYD, Schmittlein, or Fader — the same
  silo Manzoor (2024) exhibits, confirming it is a field property, not one review's oversight.
- **Its "India" hits are conference locations, not datasets** — relevant to our open F8 dataset gap: the
  field is telecom/UCI-dominated, with no India non-contractual transaction dataset surfacing.

## 4. How we use it to improve our paper
- **Cited as field survey #2** (Related Work), paired with Manzoor as the capstone that "the field's own
  recent syntheses stop short of [calibration]."
- **Its Figure 1 (PRISMA funnel) and Figure 12 (taxonomy) are the templates** for our own `fig:prisma`
  (literature-sourcing funnel) and `fig:taxonomy` (forecasting-landscape map) — reproduced in our palette.
- **Corroborates the reverse gap** (profit, drift, interpretability — but not calibration) and the
  siloed-literatures point folded into Related Work.
- **F8 check:** confirms no India non-contractual transaction dataset in a 240-study 2025 sweep.

## 5. Verdict
**Independent, current corroboration + design templates.** Imani strengthens the novelty defense (a
2025 PRISMA review that names drift and profit but not calibration, and never mentions BTYD) and supplies
the two figure archetypes we reproduced. Complementary; no tension.

---
*Part of the deep-dive series. Pairs with [`manzoor2024_deep_dive.md`](manzoor2024_deep_dive.md) as the two
field-survey anchors; both omit BTYD and calibration, the double silo our paper joins.*
