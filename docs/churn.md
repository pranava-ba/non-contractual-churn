# Churn probability calibration

**Plain English:** the Pareto/NBD gives each customer a probability of being "still alive."
Managers act on that number to size retention budgets — so is it *calibrated*? When the model
says 70% alive, are 70% actually alive?

## What it does

`churn.py` scores the calibration of the active-customer probability $P(\text{active})$ — a
binary-classification target — for BTYD against a gradient-boosted classifier, using the
**expected calibration error** (ECE) and the **Brier score**.

| Function | Plain English |
| --- | --- |
| `ece(p, outcome)` | average gap between predicted probability and observed frequency |
| `churn_scores(p_active, outcome)` | ECE + Brier for a probability vector |
| `compare_churn(df, horizon)` | BTYD $P(\text{active})$ vs an ML classifier |

## How to call it

```python
from src import datasets, churn

df  = datasets.load_summary("OnlineRetailII")
res = churn.compare_churn(df, horizon=26, seed=0)   # ECE + Brier, BTYD vs ML
```

## What we find

The churn dimension tells the **same assumption-driven story** as counts and value. BTYD's
$P(\text{active})$ is well calibrated where its assumptions hold and badly miscalibrated where
they fail:

| Dataset | ECE: BTYD | ECE: ML | winner |
| --- | --- | --- | --- |
| Simulated | **0.027** | 0.047 | BTYD |
| Grocery | **0.043** | 0.063 | BTYD |
| Online Retail II | 0.185 | **0.051** | ML |
| Ta-Feng | 0.085 | **0.013** | ML |

Because $P(\text{active})$ is a deterministic function of the same fitted rates, it inherits
their misfit on dense data.

## When *not* to use it

On sparse data BTYD's churn probabilities are the better-calibrated choice and come with an
interpretable dropout process; the ML classifier only pulls ahead in the dense regime.

**Reproduce:** `python src/run_churn_study.py` → `results/churn_study_summary.csv`.
