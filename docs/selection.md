# Which forecaster should I use?

This page is the decision aid. The project's central finding is that **one property of your
data — whether purchases follow a roughly Poisson count law — decides which forecaster is
trustworthy.** It is not "statistics vs. machine learning"; it is "does the count assumption
fit, and if not, how do you repair it."

## The one diagnostic that matters

Every Buy-Till-You-Die (BTYD) forecast — of counts, of value, of churn, of timing — is a
functional of the same conditional count law. When your data are (mixed) Poisson, the
structural model is calibrated and sharp. When they are **over-dispersed** relative to Poisson
— dense, bulk-buying, basket-structured transactions — every BTYD forecast miscalibrates at
once. Diagnose it with the PIT–KS statistic from `score.py`: near zero means calibrated;
large (≳ 0.1) means the count assumption is failing.

## Decision table

| Your situation | Use | Why | Page |
| --- | --- | --- | --- |
| Sparse, roughly memoryless buying (classic CBA) | **Structural BTYD** | best-calibrated *and* sharpest; interpretable rate/dropout parameters | [Architecture](ARCHITECTURE.md) |
| Dense / bulk-buying, want to keep the model | **Conformalized BTYD** | one held-out split restores coverage, keeps interpretability | [Conformal](conformal.md) |
| Dense, accuracy-only, interpretability optional | **Distribution-free ML** (Quantile-GBM) | best-calibrated where the Poisson assumption breaks | [ML benchmark](ml_benchmark.md) |
| You need *when*, not *how many*, and buying is regular | **Pareto/GGG** | matches the process; beats the "timing is hopeless" verdict | [Architecture §2.2](ARCHITECTURE.md) |
| Monetary value on dense data | **Deep ZILN** | better-calibrated than structural CLV where counts are over-dispersed | [Probabilistic CLV](clv_benchmark.md) |
| You were about to buy demographic covariates | **RFM-only ML** | demographics add nothing over RFM ($p=0.77$) | [Probabilistic CLV](clv_benchmark.md) |

## What does *not* matter

Two long-running debates turn out to be immaterial to forecast calibration:

- **Estimation method** — maximum likelihood, MCMC, and a one-pass
  [amortized neural estimator](amortized.md) all give the same calibration.
- **Model variant** — [Pareto/NBD and BG/NBD](bgnbd.md) are interchangeable; both break
  identically on dense data.

So spend your effort on the count assumption, not on the sampler or the family member.

## A note on measuring calibration correctly

Two natural but wrong ways to measure calibration in this setting will mislead you: interval
*coverage* is degenerate on zero-inflated counts, and conditioning the PIT on *realised*
activity fabricates the appearance of miscalibration. Use the randomized PIT with
forecast-time conditioning, and correct the PIT–KS null for estimated parameters
(`run_pit_bootstrap.py`). See the [Architecture](ARCHITECTURE.md) evaluation section.
