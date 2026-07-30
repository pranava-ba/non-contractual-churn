# ML vs. BTYD: the calibration benchmark

**Plain English:** we take the same forecasting job the Pareto/NBD model does — *how many
times will this customer buy next?* — and hand it to off-the-shelf machine learning
instead, then ask a question nobody in this literature asks: are the ML forecasts'
*intervals* actually trustworthy, or just their point predictions?

## What it does

`ml_benchmark.py` builds probabilistic machine-learning forecasters on
recency–frequency–monetary (RFM) features and scores them with the *same* proper-scoring
engine (`score.py`) used for BTYD, on a fair out-of-sample **customer** split. Three
forecasters, in increasing order of distributional flexibility:

| Forecaster | Plain English | Predictive law |
| --- | --- | --- |
| `poisson_gbm_forecast` | boosted trees for the mean, Poisson around it | $\mathrm{Poisson}(\hat g(\text{RFM}))$ |
| `hurdle_gbm_forecast` | a "will they buy at all?" classifier × a positive-count model | zero-inflated Poisson |
| `quantile_gbm_forecast` | learn the quantiles directly, assume **no** count law | distribution-free |

The first shares BTYD's Poisson assumption; the last makes none. The contrast between them
is the whole point (see *What we find*).

## How to call it

```python
from src import datasets, ml_benchmark

df  = datasets.load_summary("OnlineRetailII")      # cohort summary (x, t_x, T_cal, x_star)
res = ml_benchmark.compare_all(df, horizon=26, seed=0)
# res holds CRPS, PIT-KS, coverage and nMAE for BTYD and all three ML forecasters
```

## What we find

There is **no universal winner** — and that is the result. Ordered by where the structural
model's Poisson assumption holds:

- **Sparse, memoryless data** (Simulated, Grocery, CDNow): BTYD is best-calibrated *and*
  sharpest. Structure wins.
- **Dense, bulk-buying data** (Dunnhumby, Online Retail II): BTYD's calibration collapses
  (PIT–KS **0.169** and **0.211**) and the distribution-free Quantile-GBM is far better
  (**0.058**, **0.042**). The Poisson-GBM, which *shares* BTYD's count assumption,
  miscalibrates alongside it — so the failure is the **parametric count assumption**, not
  the model class.

## When *not* to use it

On classic sparse customer-base data, the ML models are both worse-calibrated and less
sharp than BTYD, and they throw away the interpretable rate/dropout parameters. Reach for
ML (or for [Conformalized BTYD](conformal.md)) only when the count assumption breaks —
dense, over-dispersed, basket-structured transactions.

**Reproduce:** `python src/run_ml_study.py` → `results/ml_study_summary.csv`
(15 seeds × 7 datasets, paired Wilcoxon).
