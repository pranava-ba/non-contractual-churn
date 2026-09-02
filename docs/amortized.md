# Amortized neural inference

**Plain English:** fitting a Pareto/NBD usually means running an optimiser or an MCMC sampler
for every new customer cohort. Instead we train one small neural network *once* that reads a
cohort's summary statistics and outputs the model parameters instantly — a single forward
pass, no sampler.

## What it does

`amortized.py` trains a multilayer perceptron on 4000 cohorts simulated from the Pareto/NBD
data-generating process to learn the map

$$\text{cohort summary statistics} \;\longrightarrow\; (r,\alpha,s,\beta).$$

At inference time a new cohort's parameters are one forward pass; the downstream predictive
simulation is identical to the MLE/MCMC routes, so the estimator is a drop-in replacement.
Its purpose is scientific as much as practical: it is a *third* estimation route, used to
test whether forecast calibration depends on **how** you fit the model.

## How to call it

```python
from src import amortized, datasets

X, Y = amortized.generate_training_data(n_cohorts=4000, seed=0)
am   = amortized.fit_amortizer(X, Y, seed=0)          # train once
theta = amortized.amortized_params(am, datasets.load_summary("CDNow"))  # instant fit
```

## What we find

Amortized inference is **statistically indistinguishable from MCMC**. On 25 held-out
simulated cohorts the CRPS difference is not significant (0.560 vs 0.555, paired
$p=0.51$; PIT–KS 0.037 vs 0.032), and on real data it matches or slightly beats MCMC
calibration — e.g. Online Retail II PIT–KS **0.121 vs 0.207**, by regularising toward the
simulation prior. Together with the [companion result that MLE ≈ MCMC](theory_variance_decomposition.md),
this shows forecast calibration is **estimation-method-agnostic**: what is fitted, not how,
determines whether the forecast can be trusted.

## When *not* to use it

The amortized network still fits a *Pareto/NBD*, so it inherits the same count-assumption
miscalibration on dense data (Dunnhumby PIT–KS 0.161, still broken). It is a faster route to
the same model, not a better model.

**Reproduce:** `python src/run_amortized_check.py` → `results/amortized_summary.csv`.
