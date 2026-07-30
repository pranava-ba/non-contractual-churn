# BG/NBD: does the model variant matter?

**Plain English:** the BG/NBD is the most popular alternative to the Pareto/NBD — it swaps the
"customer can churn at any time" story for "customer flips a coin to churn after each
purchase." Does that change the forecast calibration? Almost not at all — and that null is the
point.

## What it does

`estimate_bgnbd.py` fits the BG/NBD model by maximum likelihood and produces the same
predictive-count distribution the rest of the pipeline scores, so it can be compared to the
Pareto/NBD head-to-head under proper scoring.

| Object | Plain English |
| --- | --- |
| `fit_bgnbd(df)` | MLE of the BG/NBD population parameters → `BGNBDResult` |
| `bgnbd_predict(df, fit, horizon)` | predictive draws of future counts $x^*$ |

## How to call it

```python
from src import datasets, estimate_bgnbd

df   = datasets.load_summary("CDNow")
fit  = estimate_bgnbd.fit_bgnbd(df, seed=0)
pred = estimate_bgnbd.bgnbd_predict(df, fit, horizon=26, n_draws=400, seed=0)
```

## What we find

Pareto/NBD and BG/NBD are **essentially interchangeable**: CRPS agrees to within half a
percent on every cohort, calibration is close, and — decisively — **both break together** on
the dense cohorts (Dunnhumby PIT–KS 0.166 vs 0.159; Online Retail II 0.210 vs 0.215). The
variant barely matters because both share the parametric count assumption; changing the
*dropout* process cannot fix a misfit in the *count* process. This extends "the estimation
method is immaterial" to "the model variant is immaterial" within the BTYD family.

## When *not* to use it

Choose between Pareto/NBD and BG/NBD on grounds other than forecast calibration —
computational convenience, or whether you need a continuous-time dropout interpretation. For
the calibration of the forecast itself, the choice does not move the needle.

**Reproduce:** `python src/run_bgnbd_study.py` → `results/bgnbd_study_summary.csv`.
