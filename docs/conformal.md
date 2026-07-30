# Conformalized BTYD

**Plain English:** the Pareto/NBD model's intervals go wrong on dense data — but instead of
throwing the model away, we *correct* its intervals with one extra data split. Same model,
same interpretable parameters, trustworthy intervals.

## What it does

`conformal.py` applies a single-pass **distributional recalibration** (an isotonic warp of
the predictive quantiles, in the spirit of Kuleshov, Fenner & Ermon 2018) to the BTYD
predictive:

1. hold out a calibration split of customers;
2. compute the PIT values of the BTYD forecast on that split (these reveal *how* the
   intervals are wrong — too wide, too narrow, shifted);
3. fit an isotonic map from nominal to empirical coverage;
4. warp every other customer's predictive quantiles through that map.

It changes only the *shape* of the predictive distribution — never the point forecast, the
fitted parameters, or $P(\text{alive})$.

## How to call it

```python
from src import datasets, conformal

df  = datasets.load_summary("OnlineRetailII")
res = conformal.compare_conformal(df, horizon=26, recal_frac=0.5, seed=0)
# res reports PIT-KS before ("raw") and after ("recalibrated")
```

To recalibrate raw predictive samples directly:

```python
recal = conformal.recalibrate_samples(pred_cal, y_cal, pred_test, n_out=500, seed=0)
```

## What we find

One held-out split **repairs every miscalibrated cohort**, and does **no harm** where the
model was already calibrated:

| Dataset | PIT–KS raw | PIT–KS conformalized | $p$ |
| --- | --- | --- | --- |
| Online Retail II | 0.212 | **0.044** | <0.001 |
| Dunnhumby | 0.164 | **0.097** | <0.001 |
| Ta-Feng | 0.072 | **0.027** | <0.001 |
| CDNow | 0.056 | **0.034** | <0.001 |
| Grocery (already calibrated) | 0.036 | 0.036 | 0.98 |

The recalibrated model matches the best distribution-free ML on calibration while keeping
the Pareto/NBD's cheap closed-form fit and interpretability.

## When *not* to use it

If the model is already calibrated (sparse data), recalibration is a no-op — it costs a data
split for no gain. It also cannot invent information: it fixes interval *width and location*,
not a fundamentally wrong point forecast.

**Reproduce:** `python src/run_conformal_study.py` → `results/conformal_study_summary.csv`.
