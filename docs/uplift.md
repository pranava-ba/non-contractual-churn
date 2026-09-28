# Prescriptive BTYD: causal uplift on the buy-till-you-die state (Gear 2)

**Plain English:** a churn/CLV forecast tells you who is *likely* to leave or spend — it does not
tell you who a retention action would actually *save*. This module turns the calibrated BTYD
state into that second, decision-relevant quantity: the **conditional average treatment effect**
(CATE / uplift) of an intervention, with calibrated confidence in the estimate itself.

> **Scope note:** this is **Gear 2** — a distinct research track and a **separate future paper**
> from the Phase 2 manuscript in `paper/` (which is in pre-submission). Nothing here is folded
> into that manuscript. See `deep_research/GEAR2_ROADMAP.md` for the full plan and
> `deep_research/GEAR2_STAGE_A_RESULTS.md` for the detailed Stage-A findings this page summarizes.

## Why prediction isn't enough

A churn-risk or predicted-value model ranks customers by what happens **under the status quo**.
It cannot say what a retention offer, email, or discount would *change* — that is a causal
question. Four customer types make the gap concrete:

| Customer type | Churn risk | Uplift (what actually matters) | A propensity/value model... |
|---|---|---|---|
| Persuadable | high | **positive** — action saves them | targets correctly, by luck |
| Lost cause | high | ~0 — churns regardless | wastes budget |
| Sure thing | low | ~0 — stays regardless | correctly skips |
| Sleeping dog | low/mixed | **negative** — action annoys them | may target and backfire |

## What it does

1. **`simulate_intervention.py`** — extends the validated Pareto/NBD simulator with a treatment
   `T` that shifts a customer's latent dropout rate (`mu`) and/or purchase rate (`lambda`) at the
   calibration boundary. Because both potential outcomes are simulated, every customer has a known
   **ground-truth CATE** for three outcomes at once (repeat-purchase count, retention, residual
   CLV) — the oracle every estimator below is scored against. Parameterised over target
   (`mu`/`lambda`/`both`), effect structure (`homogeneous`/`heterogeneous`/`sleeping_dogs`), and
   assignment (`randomized`/`confounded`).
2. **`run_uplift_study.py`** — fits a panel of CATE estimators (econml + causalml meta-learners,
   causal-forest DML) and predict-then-target baselines (value-targeting, risk-targeting, random)
   over a 12-family DGP factorial, and scores each on PEHE, rank correlation, 90% interval
   coverage, and realised policy value as a % of the oracle.
3. **`uplift_estimators_ext.py`** — the two novelty-bearing estimators:
   - `structural_btyd_cate` — a **model-based** uplift: method-of-moments dropout rate per
     (arm, RFM-bucket), differenced through the Pareto/NBD closed form. The causal analogue of the
     Phase 2 structural forecaster.
   - `conformal_ite` — split-conformal prediction intervals for the individual treatment effect
     (Lei & Candès 2021 style): the calibration **repair** for overconfident causal-forest
     intervals.
4. **`run_uplift_dunnhumby.py`** / **`run_uplift_hillstrom.py`** — Stage B, external validity on
   real data: Dunnhumby's household campaign treatment (observational, scored by doubly-robust
   policy value) and the Hillstrom email trial (randomized, scored by Qini AUC).

## How to call it

**Simulate an intervention with ground-truth CATE** (semi-synthetic validation, Stage A):

```python
from simulate import DatasetParams
from simulate_intervention import InterventionConfig, simulate_intervention

df = simulate_intervention(
    DatasetParams(E_lambda=0.5, CV_lambda=1.2, E_mu=0.08, CV_mu=1.2, N=6000, T=72),
    InterventionConfig(target="mu", structure="sleeping_dogs", delta=0.4,
                       assignment="confounded", horizon=52),
)
# df has the factual outcome an estimator sees (y_clv, y_count, y_active, T) AND the oracle
# (cate_clv, cate_count, cate_active) for validation.
```

**The `paretonbd` prescriptive API** (`prescriptive.py`) — estimate uplift, turn it into a
targeting decision, and score the policy:

```python
from prescriptive import estimate_uplift, target_policy, dr_policy_value, fit_dr_nuisances

cate_hat, ci = estimate_uplift(Xtr, Ttr, Ytr, Xte, method="causal_forest")
pi = target_policy(cate_hat, margin=50.0, cost=5.0)              # M*tau_hat - c > 0
# or: pi = target_policy(cate_hat, budget=0.30)                  # top-30% by uplift

# on real (observational) data, score the policy by doubly-robust value:
ehat, m1hat, m0hat = fit_dr_nuisances(Xtr, Ttr, Ytr, Xte)
value = dr_policy_value(pi, Tte, Yte, ehat, m1hat, m0hat)
```

`structural_btyd_cate` and `conformal_ite` (the two novelty estimators) are re-exported from
`prescriptive` for convenience, but keep their own data contracts:

```python
from prescriptive import structural_btyd_cate, conformal_ite

cate_hat, _ = structural_btyd_cate(df_train, df_test, horizon=52, outcome="clv")
cate_hat, (lo, hi) = conformal_ite(Xtr, Ttr, Ytr, Xte, base_reg=_rf_reg, alpha=0.10)
```

## What we find (Stage A + B, 2026-09-20)

- **Prediction ≠ decision.** Value-targeting captures ~0.99 of the oracle policy value when the
  treatment effect aligns with predicted value, but **−58× the oracle under sleeping dogs** — it
  actively targets the customers an action will annoy. Causal uplift (causal forest,
  structural-BTYD) degrades far more gracefully in the same regime.
- **The library choice doesn't matter; the estimator does.** econml and causalml agree *exactly*
  on a matched base learner (rank-corr 1.000, identical top-20% targets); the gap between
  meta-learners and causal-forest DML (~3× on PEHE) dwarfs any library difference.
- **Calibration lens works.** Causal-forest intervals are genuinely overconfident (coverage 0.80
  at 1,200 trees — not a few-tree artefact, and worse under confounding); conformal-ITE restores
  ~0.96 coverage, at a sharpness cost (~5× wider than the causal forest's own, invalid, intervals).
- **BTYD state is immaterial as a *feature*.** Raw RFM already gives the causal model everything
  it needs — echoing the Phase 2 result that structure doesn't help distribution-free ML once RFM
  is in the feature set. The BTYD state still matters as the *structural estimator itself*
  (`structural_btyd_cate`), just not as an input to the black-box learners.
- **External validity confirmed on two real datasets.** Dunnhumby (observational, doubly-robust
  policy value): uplift-targeting beats value-targeting **~4×** on incremental value. Hillstrom
  (randomized, Qini-valid): uplift-targeting beats value-targeting **~2×** on Qini AUC. Both
  reproduce the synthetic ordering **uplift > value > random**. X5/RetailHero is login-walled and
  needs a manual download — the auto-fetchable portion of Stage B is otherwise complete.

Full tables, the 12-family factorial design, and the coverage/ablation follow-ups are in
[`GEAR2_STAGE_A_RESULTS.md`](../deep_research/GEAR2_STAGE_A_RESULTS.md).

## Reproduce

```bash
python src/run_uplift_study.py --full         # results/gear2_uplift_summary.csv
python src/run_uplift_extras.py coverage       # results/gear2_coverage_summary.csv
python src/run_uplift_extras.py ablation       # results/gear2_ablation_summary.csv
python src/run_uplift_dunnhumby.py             # results/gear2_dunnhumby_summary.csv
python src/run_uplift_hillstrom.py             # results/gear2_hillstrom_summary.csv
python src/make_gear2_figures.py               # results/figures_gear2/*.png
```

Requires the `causal` optional dependency group (`pip install -e .[causal]`): econml, causalml,
lightgbm, xgboost, shap, scikit-uplift.

## When *not* to use it

The ground-truth CATE only exists in the semi-synthetic Stage-A simulator — real data (Stage B)
has no oracle, so evaluation there leans on doubly-robust policy value (observational) or Qini
(when assignment happens to be randomized), not PEHE. Don't read a real-data Qini/DR number as
"recovering the true effect" the way the synthetic PEHE numbers can be; it's a targeting-quality
metric, not a recovery metric. A live deployment or partner pilot (Stage C) remains open —
capstone / future-work, not a blocker.
