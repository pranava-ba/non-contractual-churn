# Probabilistic customer lifetime value

**Plain English:** forecasting *how much money* a customer is worth, not just how many times
they buy. We compare the classic structural recipe (Pareto/NBD counts × Gamma-Gamma spend)
against a deep model that learns the whole spend distribution directly.

## What it does

`clv_benchmark.py` scores two probabilistic value forecasters on the monetary target under
CRPS / PIT / coverage:

- **Structural CLV** (`btyd_gg_clv_predict`): Pareto/NBD purchase counts multiplied by a
  Gamma-Gamma spend-per-transaction model — interpretable, closed-form.
- **Deep ZILN** (`ziln_clv_predict`): a zero-inflated-lognormal neural network (Wang et al.
  2019) that outputs $P(\text{spend}=0)$ and the lognormal parameters of the positive spend.
  *(Requires the optional `torch` dependency.)*

Monetary cohorts are built by `clv_data.py` (`load_clv_summary("OnlineRetailII" | "Ta-Feng"
| "Dunnhumby")`).

## How to call it

```python
from src import clv_data, clv_benchmark

df  = clv_data.load_clv_summary("OnlineRetailII")
res = clv_benchmark.compare_clv(df, horizon=26, seed=0)   # BTYD+GG vs ZILN
```

## What we find

The deep ZILN is **significantly better calibrated on every monetary dataset** at comparable
point accuracy:

| Dataset | PIT–KS: BTYD+GG | PIT–KS: ZILN | $p$ |
| --- | --- | --- | --- |
| Online Retail II | 0.212 | **0.031** | <0.001 |
| Ta-Feng | 0.082 | **0.020** | <0.001 |
| Dunnhumby | 0.143 | **0.073** | <0.001 |

The reason is the same as for counts: **structural CLV inherits the Poisson miscalibration**
from its count component. We also tested whether the gap is about missing covariates rather
than the count assumption — adding demographics (age, income, household) to the ML value
model changes nothing (`covariate_benchmark.py`; PIT–KS 0.206→0.205, $p=0.77$). RFM already
carries the signal.

## When *not* to use it

Structural CLV remains the right tool when interpretability of the count and spend processes
matters, on sparse data where its assumptions hold, or when a `torch` dependency is
unwelcome. The ZILN wins on calibration specifically in the dense regime.

**Reproduce:** `python src/run_clv_study.py` → `results/clv_study_summary.csv`.
