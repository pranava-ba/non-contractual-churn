---
title: "Tooling & Packages — Causal ML / Uplift (Gear 2)"
type: reference
created: 2026-09-20
role: Detailed inventory of the software for CATE / uplift / policy learning that Gear 2 will use or
      benchmark against. Companion to TOOLING_NONCONTRACTUAL.md (the BTYD side). Env status is live in
      GEAR2_ROADMAP.md §6.
---

# Causal-ML / uplift tooling

**Installed & smoke-tested on this machine (Py 3.13, 2026-09-20):** `econml 0.17.0`, `causalml 0.17.0`
(+ `lightgbm 4.7.0`, `xgboost 3.4.1`, `shap 0.52` as deps). On a matched base learner the two libraries
produced *identical* CATE (rank-corr 1.000); the lever is the estimator, not the library (GEAR2_ROADMAP §6).

## 1. CATE / uplift estimation libraries

| Package | Lang | Maintainer | What it gives | Estimators | Status / notes |
|---|---|---|---|---|---|
| **EconML** | Py | Microsoft Research | orthogonal / DML CATE, causal forests, policy trees, sensitivity, inference (CIs) | LinearDML, SparseLinearDML, CausalForestDML, DRLearner, DML-IV, metalearners (S/T/X), OrthoForest, PolicyTree/DRPolicyTree | **installed ✅**; richest for DML + policy + inference. **Primary.** |
| **CausalML** | Py | Uber | uplift trees/forests + meta-learners + eval | UpliftRandomForest, meta (Base S/T/X/R Regressor & Classifier), CEVAE, TMLE, Qini/AUUC plots, feature-selection | **installed ✅**; adds tree-based uplift + rich uplift plots. **Secondary / cross-check.** |
| **scikit-uplift (`sklift`)** | Py | community | sklearn-style uplift API + **built-in dataset fetchers** | SoloModel, TwoModels, ClassTransformation + `uplift_curve`, `qini_curve` | ⬜ add — its `datasets.fetch_*` (Hillstrom/Criteo/Lenta/X5/MegaFon) is the fastest path to Stage-B data. |
| **DoubleML** | Py / R | Bach, Chernozhukov et al. | rigorous DML with valid inference (the econometrics-grade reference) | PLR, IRM, IIVM | ⬜ optional — cite/compare for inference correctness. |
| **DoWhy** | Py | Microsoft (PyWhy) | identify → estimate → **refute** workflow; DAGs; refutation tests | wraps EconML/estimators | ⬜ optional — its *refutation* tests (placebo, random-common-cause) are a nice robustness section. |
| **grf** | R | Athey, Tibshirani, Wager | the reference causal forest / GRF implementation | causal_forest, instrumental_forest, policy tree | reference only — Python `CausalForestDML` is our route; cite grf as canonical. |
| **pylift** | Py | Wayfair | transformed-outcome uplift + Qini | TransformedOutcome | ⚪ legacy alternative; sklift preferred. |

## 2. Policy / evaluation utilities

| Tool | Where | Use |
|---|---|---|
| **Qini / uplift / AUUC curves** | causalml (`metrics`), sklift | headline targeting metric + plots |
| **RATE (rank-weighted ATE)** | grf (`rank_average_treatment_effect`); reimplement in Py | test our prioritization rule vs random |
| **PolicyTree / DRPolicyTree** | econml | interpretable budgeted targeting rule |
| **IPW / doubly-robust OPE** | econml, hand-rolled | policy value on real data w/o full truth |
| **Refutation tests** | DoWhy | placebo-treatment / subset / random-common-cause robustness |

## 3. Calibration of treatment effects (our differentiator — mostly build-it)

| Need | Tool | Notes |
|---|---|---|
| Conformal ITE intervals | **MAPIE**, **crepes** (already in the BTYD tooling), + conformal-meta-learner logic | reuse `src/conformal.py`; implement Lei-Candès / Alaa conformal-metalearner for τ̂ |
| Coverage / PIT / CRPS of τ̂ | **our own `src/score.py`** | the Gear 1 machinery, retargeted from y to τ |
| Reliability of uplift deciles | our `src/churn.py` ECE/reliability code | adapt to predicted-vs-realised uplift |
| Bayesian effect intervals | PyMC (Bayesian causal forest) | compare model-based vs conformal sharpness |

## 4. Benchmark harnesses to borrow from

- **uplift-bench** (GitHub `yablochnikovds/uplift-bench`) — 7 uplift methods × 5 public datasets +
  synthetic, bootstrap CIs, robustness, comparison plots. A ready template for our Stage-A/B tables.
- **UpliftBench** (arXiv 2608.00915, 2026) — multi-objective, outer-test-isolated protocol; documents
  that uplift benchmarks disagree by *metric* — motivates our "report several metrics" discipline.

## 5. What Gear 2 will actually use (decision)

- **Estimation:** EconML (DML + CausalForestDML + DRLearner + metalearners) as primary; CausalML for
  uplift-tree coverage and the cross-check; sklearn meta-learners as the dependency-free floor.
- **Data:** `sklift.datasets.fetch_*` for Stage-B public uplift sets.
- **Eval:** causalml/sklift for Qini/AUUC; our own `score.py`/`conformal.py` for the calibration angle.
- **Robustness:** DoWhy refutation + confounded-assignment sweeps in the simulator.
- **Add to env:** `scikit-uplift`, and (optional) `dowhy`, `doubleml`. Pin all in the env notes.
