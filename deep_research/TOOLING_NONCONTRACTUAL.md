---
title: "Tooling & Packages — Non-contractual churn / BTYD (Gear 1)"
type: reference
created: 2026-09-20
role: Detailed inventory of the software used across the BTYD / customer-base-analysis field and in
      THIS project (Gear 1). The prose companion to tooling_map.mmd. Causal-ML side in TOOLING_CAUSAL_ML.md.
---

# Non-contractual-churn / BTYD tooling

The field's tooling splits into **model estimation** (R + Python BTYD packages), the **canonical math**
(Hardie's notes), **evaluation/calibration** (which the BTYD packages *lack* — the gap Gear 1 fills),
and the **ML-for-CLV** stack. "Used here" marks what this repo actually depends on or reimplements.

## 1. BTYD model-estimation packages

| Package | Lang | Models | Estimation | Maturity | Used here |
|---|---|---|---|---|---|
| **BTYD** | R | Pareto/NBD, BG/NBD, BG/BB | MLE | original, **stale** | reference (McCarthy & Wadsworth walkthrough) |
| **BTYDplus** | R | Pareto/NBD, **Pareto/GGG**, MBG/NBD, (M)BG/CNBD-k, **HB Pareto/NBD (MCMC)** | MLE + MCMC | maintained-ish | reference for Pareto/GGG + HB; we reimplement in Python |
| **CLVTools** | R | Pareto/NBD, BG/NBD, GGompertz/NBD, Gamma-Gamma spend, **covariates** | MLE, closed-form | **actively maintained** | benchmark cross-check; `groceryElog` comes from here |
| **lifetimes** | Py | BG/NBD, Pareto/NBD, Gamma-Gamma | MLE | **archived (unmaintained)** | historical; superseded below |
| **PyMC-Marketing** | Py | BG/NBD, Pareto/NBD, Gamma-Gamma, **HB/MCMC** | Bayesian (PyMC) | **actively maintained** | the modern Bayesian route; conceptual peer to our `hmc.py`/`estimate.py` |
| **btyd (ColtAllen)** | Py | BG/NBD, Pareto/NBD, Gamma-Gamma | MLE + Bayesian | active successor to `lifetimes` | ⬜ note as the maintained pure-Python option |

**This repo's own estimators** (`src/`): `estimate.py` (MLE + MCMC Pareto/NBD), `estimate_bgnbd.py`,
`estimate_ggg.py` (Pareto/GGG), `hmc.py` (HMC), `laplace.py`, `amortized.py` (neural amortized
inference), `clv.py` (Gamma-Gamma spend) — i.e. we reimplement the field's stack in Python *and* add
tiers (amortized, Laplace) the packages above don't have.

## 2. Canonical math / references

| Resource | What |
|---|---|
| **brucehardie.com** (Fader & Hardie technical notes + Excel) | the canonical derivations for every BTYD quantity — the field's ground truth |
| Schmittlein, Morrison & Colombo (1987); Fader, Hardie & Lee (2005) | Pareto/NBD & BG/NBD source papers (see LITERATURE_MATRIX 2a) |

## 3. Evaluation / calibration (the BTYD packages do NOT provide this — Gear 1's gap)

| Package | Lang | Gives | Used here |
|---|---|---|---|
| **properscoring** / **scoringRules** (R) | Py / R | CRPS, log score | concept reimplemented in `src/score.py` |
| **MAPIE** | Py | conformal prediction intervals | conformal recalibration peer to `src/conformal.py` |
| **crepes** | Py | conformal regressors/predictive systems | ditto |
| **uncertainty-toolbox** | Py | calibration metrics, reliability, PIT | concept in `src/score.py` / `src/churn.py` (ECE) |
| **sklearn.calibration** | Py | isotonic / Platt recalibration | used in the conformal/churn work |

**This repo's own eval** (`src/`): `score.py` (CRPS/PIT/coverage), `conformal.py` (conformalized BTYD),
`churn.py` (Brier/ECE/reliability), `tost.py` (equivalence tests), `run_pit_bootstrap.py` (Lilliefors
null). This evaluation layer *is the Gear 1 contribution* — it does not exist in the BTYD packages.

## 4. ML-for-CLV / churn stack (the competitors and our ML tiers)

| Tool | Gives | Used here |
|---|---|---|
| **XGBoost / LightGBM** | gradient-boosted quantile / count forecasters | `ml_benchmark.py` (QuantileGBM, Poisson-GBM); now installed (came with econml/causalml) |
| **scikit-learn** | RF, quantile regressors, calibration | `ml_benchmark.py`, feature builders (`rfm_features`) |
| **TensorFlow Probability (ZILN loss)** | zero-inflated lognormal CLV head | reimplemented for the deep-ZILN value comparator (`clv_benchmark.py`) |
| **PyTorch** | RNN / seq2seq CBA, amortized inference nets | `amortized.py`; RNN comparator concept (Valendin 2022) |
| **sbi** (simulation-based inference) | neural posterior estimation | *not installed*; `amortized.py` is a hand-rolled analogue |

## 5. The picture in one line

BTYD packages **estimate** (R: BTYD/BTYDplus/CLVTools; Py: lifetimes→btyd/PyMC-Marketing) but **do not
evaluate distributional calibration**; the ML-CLV stack (GBM/RNN/ZILN) **forecasts** but is judged on
point error. Gear 1 bolts a **calibration evaluation layer** (CRPS/PIT/coverage/conformal) onto both.
Gear 2 (TOOLING_CAUSAL_ML.md) adds the **causal/decision layer** on top of that same state.
