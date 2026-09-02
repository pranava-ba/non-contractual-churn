---
title: "Manzoor, Qureshi, Kidney & Longo (2024), *A Review on ML Methods for Customer Churn Prediction* — deep-dive"
type: deep-read
created: 2026-08-11
source: "Awais Manzoor, M. Atif Qureshi, Etain Kidney, Luca Longo. A Review on Machine Learning Methods for
         Customer Churn Prediction and Recommendations for Business Practitioners. IEEE Access 12 (2024)
         70434–70463. DOI 10.1109/ACCESS.2024.3402092. Local: references/candidates/tudublin_2024_ml_churn_review.pdf"
role: "Field survey #1. Its five gaps let us show our extension answers what the whole churn-ML literature
       complains about — and, more tellingly, fills a gap the review itself omits (calibration)."
math: LaTeX. companion: gap_crosswalk_manzoor2024.md (the full 5-gap synced table) · deep_dive.md
---

# Manzoor et al. (2024) — deep-dive (field review #1)

**Thesis.** A field-level review of machine-learning customer-churn prediction (212 articles; 185 primary,
2015–Jan 2024, + 27 supportive) that distils the literature into **five critical gaps** with matched
recommendations and a **profit-metric apparatus** (MPC/EMP, Verbraken et al.). It is a *field-level* gap
analysis; our paper is a *paper-level* extension — and the comparison shows our work answers 4 of the 5.

*(The exhaustive gap-by-gap synced table lives in [`gap_crosswalk_manzoor2024.md`](gap_crosswalk_manzoor2024.md);
this file is the deep-dive framing.)*

---

## 0. TL;DR — Manzoor vs. our paper

| Axis | **Manzoor (2024)** | **Our paper** |
|---|---|---|
| **Type** | field-level systematic review (212 studies) | a specific BTYD-vs-ML calibration extension |
| **Scope** | ML churn-classification literature | structural + ML, four targets, calibration |
| **BTYD coverage** | **zero** (0 mentions of Pareto/NBD, BTYD, Schmittlein, Fader) | BTYD is half the comparison |
| **Metric frontier** | reaches **profit** (MPC/EMP), stops before calibration | **calibration** is the whole lens |
| **XAI** | pushes harder (their Gap 5) | answered structurally, not via SHAP |
| **Relationship** | **field validation + a reverse gap.** We patch 4 of their 5 gaps, and fill the calibration gap their metric complaint (Gap 4) never reaches. |

---

## 1. What the review does
Surveys ML churn-prediction end-to-end (data, features, classifiers, metrics, deployment) and, in its §VI
Gap Analysis, names five critical gaps with recommendations:
- **G1 — datasets old or private** (stale features; non-replicable; no cross-study comparison). *Fix:*
  build up-to-date, high-quality, anonymised **public** datasets with governance.
- **G2 — no consensus on the feature set** (behavioural vs demographic vs network vs feedback). *Fix:*
  integrate feature families.
- **G3 — no consensus on classifiers** (simple vs ensembles/DL; poor cross-domain generalisation). *Fix:*
  select by data size/shape; prioritise generalisability.
- **G4 — traditional metrics inadequate** (accuracy/precision/recall/ROC ignore individual profitability).
  *Fix:* **profit-based metrics** (MPC, EMP; Verbraken et al. 2013).
- **G5 — performance–explainability tradeoff** (ensembles/DL opaque). *Fix:* adopt **XAI**.

Plus a Conflict-of-Interest/disclaimer block and a Table-6 abbreviations appendix (both borrowed as
"remember to include" items for our own paper).

## 2. Novelty / value
A practitioner-facing consolidation of a fragmented field, with an explicit, actionable gap list and a
profit-metric lineage — the kind of authoritative "what the field lacks" statement that a specific paper
can position against. Its independence and scale make it a strong external sanity check on our scope.

## 3. How it differs from our paper
- **Altitude.** It is a *field* gap analysis (what the churn-ML *literature* lacks); ours is a *paper*
  extension (what Simon 2025 leaves open). They sit at different levels — which is exactly why the
  comparison is useful.
- **The reverse gap — calibration.** Manzoor's sharpest metric complaint (Gap 4) reaches *profit-awareness*
  (MPC/EMP) but **never reaches probability calibration**. A 2024 review centred on evaluation metrics
  flags profit but not calibration — the clearest evidence that our lens is still open. We fill a gap the
  review itself does not name.
- **BTYD blind spot.** Full-text search returns **0** mentions of Pareto/NBD, BTYD, Schmittlein, or Fader:
  the churn-ML literature the review maps and the BTYD/CBA tradition are siloed — a point we fold into
  Related Work.

## 4. How we use it to improve our paper
- **Cited as field survey #1** (Related Work), and as the source of the **profit-metric lineage**
  (Verbraken 2013 EMP/MPC) in our §profit motivation.
- **Gap 4 as the calibration springboard:** "the field sees the metric problem, reaches profit, and stops
  before calibration."
- **Gap 5 (XAI) → our Limitations paragraph:** we position structural interpretability + Conformalized
  BTYD as our answer to the performance–interpretability tradeoff and name SHAP-style attribution as
  future work (with De Caigny 2024, Boukrouh 2025).
- **Gap 1 (datasets) → our reproducibility posture:** seven *public* cohorts answer the replicability half;
  F8 (an Indian cohort) remains the recency half.
- **Structural furniture borrowed:** the abbreviations appendix (their Table 6) and the disclaimer block.

## 5. Verdict
**A field-scale external validation, plus a reverse gap.** Manzoor confirms our specific extension targets
what the whole literature complains about (we patch 4/5), and — because its own metric frontier stops at
profit — it is the strongest single piece of evidence that the calibration lens is novel. Fully
complementary; no tension.

---
*Part of the deep-dive series. The exhaustive 5-gap table is in
[`gap_crosswalk_manzoor2024.md`](gap_crosswalk_manzoor2024.md); the calibration reverse-gap is corroborated
independently by [`ulrich_deep_dive.md`](ulrich_deep_dive.md) from the theory side.*
