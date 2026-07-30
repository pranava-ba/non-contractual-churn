# Technical Architecture

A deep dive into the statistical machinery, data flow, and module layout of the
Pareto/NBD Extension. This document is the counterpart to the paper's Methods section:
it explains *how the code realises the math*.

## 1. Overview

The repository answers one question — *are Pareto/NBD purchase forecasts calibrated, and
does the estimation method matter?* — by turning every model into a **full predictive
distribution** for each customer's future purchase count `x*` and scoring that
distribution with proper scoring rules. The pipeline has four stages:

```mermaid
flowchart LR
    A[simulate / empirical<br/>cohort] --> B[estimate<br/>MLE · MCMC · GGG]
    B --> C[predictive draws<br/>x* via SPP]
    C --> D[score<br/>CRPS · LogS · PIT · coverage]
    D --> E[analyze<br/>Wilcoxon · TOST · tables · figures]
```

Every stage is a small pure-`numpy`/`scipy` module; there are no heavyweight framework
dependencies, and every result in the paper is reproducible from the scripts in `src/`.

## 2. The probabilistic models

### 2.1 Pareto/NBD (`simulate.py`, `estimate.py`)

While alive, customer *i* purchases as a Poisson process with rate `λ_i`; the latent
lifetime `τ_i` is exponential with churn rate `μ_i`. Heterogeneity is Gamma:
`λ_i ~ Γ(r, α)`, `μ_i ~ Γ(s, β)`. Each customer is summarised by the sufficient
statistics `(x_i, t_{x,i}, T_i)` — repeat count, recency, and calibration length. The
individual likelihood is closed form (Fader & Hardie 2005):

$$L(\theta \mid x_i, t_{x,i}, T_i) = \frac{\Gamma(r+x_i)\,\alpha^r \beta^s}{\Gamma(r)}\left[\frac{1}{(\alpha+T_i)^{r+x_i}(\beta+T_i)^s} + \frac{s}{r+s+x_i} A_i\right].$$

### 2.2 Pareto/GGG (`simulate_misspec.py`, `estimate_ggg.py`)

Relaxes the memoryless purchase timing: inter-purchase times are
`Γ(shape = k, rate = k·λ_i)`, so the mean gap is preserved (`1/λ_i`) but the coefficient
of variation is `1/√k`. `k = 1` recovers Pareto/NBD; larger `k` is more clock-like. The
extra per-customer sufficient statistic is `litt_i = Σ_j log g_{ij}` (sum of log
inter-purchase gaps), which identifies the common regularity `k`.

### 2.3 Gamma-Gamma spend / CLV (`clv.py`)

Transaction values `m_{ij} ~ Γ(p, p/ν_i)` with mean `ν_i`; the mean spend has an
**Inverse-Gamma** prior `ν_i ~ IG(q, v)`. Given `x_i` transactions of observed average
`m̄_i`, the posterior is `ν_i ~ IG(p·x_i + q, v + p·x_i·m̄_i)`. Combined with the
purchase-count predictive, `CLV_i = x*_i · ν_i` yields a probabilistic customer value.

## 3. Estimation

| Method | Module | Idea |
| --- | --- | --- |
| **MLE** | `estimate.fit_mle` | Bounded, method-of-moments-started, multi-start Nelder–Mead over the closed-form log-likelihood. Log-parameters are clamped to `[1e-5, 1e5]` and overflow solutions rejected — the fix for the divergence documented in the paper's fair-baseline caveat. |
| **MCMC (Abe/BTYDplus)** | `estimate.fit_mcmc` | Data-augmentation Gibbs sampler. Augmenting `τ_i` makes every full conditional closed form: `λ_i ~ Γ(x_i+r, α+min(τ_i,T_i))`, `μ_i ~ Γ(s+1, β+τ_i)`, an alive-indicator Bernoulli, a (truncated) exponential `τ_i`, conjugate `α,β`, and slice-sampled `r,s`. Supports a dispersed `init` for convergence diagnostics. |
| **Pareto/GGG (common-k)** | `estimate_ggg.fit_ggg` | Augmented Metropolis-within-Gibbs. `λ_i` updated by a vectorised **independence-MH** step whose proposal is the Pareto/NBD conjugate Gamma and whose acceptance ratio is a survival-function correction `Q(k, k·λ'·d)/Q(k, k·λ·d)`; `k` is slice-sampled from the pooled renewal likelihood. Collapses to the Pareto/NBD sampler at `k = 1`. |

## 4. Predictive distributions (`score.py`, `estimate_ggg.py`, `timing.py`)

The **Simulated Purchase Pattern (SPP)** identity generates `x*` exactly: while alive,
purchases are Poisson, so the count in the window `(T_i, T_i+T*]` is

$$x_i^{*(j)} \sim \mathrm{Poisson}\!\left(\lambda_i^{(j)} L_i^{(j)}\right), \quad L_i^{(j)} = \max\!\left(0, \min(\tau_i^{(j)}, T_i+T^*) - T_i\right).$$

- **MCMC** feeds full posterior draws `(λ, μ, τ)` into SPP (`spp_predict`).
- **MLE plug-in** draws individual `(λ, μ, τ)` at the fixed MLE point
  (`conditional_individual_draws`) — carrying individual + count uncertainty but *not*
  parameter uncertainty, isolating exactly what the Bayesian treatment adds.
- **Pareto/GGG** forward-simulates the Gamma renewal with a left-truncated first gap
  (`spp_predict_ggg`); counts are no longer Poisson.
- **Heuristic** is a degenerate (Dirac) predictive at `x_i/T_i · T*`.
- **Timing** (`timing.py`) gives the wait-time distribution to the next purchase
  `t_{x+1}` (memoryless for Pareto/NBD; left-truncated Gamma renewal for Pareto/GGG).

## 5. Evaluation framework (`score.py`, `make_tables_sn.py`)

- **CRPS** — sample estimator `E|X−y| − ½ E|X−X'|`; proper, reduces to absolute error for
  a point forecast.
- **Log score** — Laplace-floored negative log predictive mass (`logscore_check.py`); a
  second proper score that penalises overconfident tails.
- **Randomized PIT** — Czado–Gneiting–Held count PIT; `U(0,1)` under calibration,
  summarised by a Kolmogorov–Smirnov distance (PIT-KS).
- **Coverage & sharpness** — central-interval coverage and mean predictive SD.
- **Significance & equivalence** — paired Wilcoxon with Benjamini–Hochberg FDR control,
  plus a two-one-sided-tests (TOST) equivalence check for the central MCMC≈MLE null.

## 6. Why MCMC ≈ MLE — the variance decomposition

By the law of total variance,

$$\mathrm{Var}(x^*_i \mid \text{data}) = \underbrace{\mathbb{E}_{\theta}[\mathrm{Var}(x^*_i \mid \theta)]}_{\mathcal{O}(1),\ \text{individual + Poisson}} + \underbrace{\mathrm{Var}_{\theta}(\mathbb{E}[x^*_i \mid \theta])}_{\mathcal{O}(1/N),\ \text{parameter uncertainty}}.$$

MCMC propagates the second term; the plug-in ignores it. For any realistic cohort
(`N ≥ 100`) the first term dominates, so the two predictive distributions coincide. See
[theory_variance_decomposition.md](theory_variance_decomposition.md).

## 7. Data schemas ("message definitions")

**Per-customer cohort row** (output of `simulate_*` / `empirical.elog_to_summary`):

| Field | Meaning |
| --- | --- |
| `x` | repeat purchases in the calibration window |
| `t_x` | recency: time of last repeat purchase |
| `T_cal` | calibration window length (acquisition-relative) |
| `litt` | Σ log inter-purchase gaps (Pareto/GGG only) |
| `x_star_{h}` | ground-truth repeat purchases in horizon `h ∈ {13, 26, 52}` |

**Results row** (`results/*.csv`): `N, T, rep, horizon, method, cond, nMAE, nRMSE,
nMdAE, CRPS, cov50/80/95, sharpness_std, pit_ks` and, for the extensions, `k_hat`,
`E_lambda_*`, `clv_*`, `timing_*`.

## 8. Module map

| Module | Role |
| --- | --- |
| `simulate.py`, `simulate_misspec.py` | Data-generating processes (Pareto/NBD, GGG, mixture) |
| `estimate.py`, `estimate_ggg.py` | MLE, Abe MCMC, common-k Pareto/GGG |
| `score.py` | Predictive draws + CRPS / PIT / coverage / sharpness |
| `timing.py`, `clv.py` | Extensions B (timing) and E (CLV) |
| `run_study.py`, `run_ggg.py`, `run_misspec.py`, `run_mixture.py` | Experiment runners |
| `analyze.py`, `make_tables.py`, `make_tables_sn.py`, `pit_figures.py`, `ggg_report.py`, `convergence.py`, `logscore_check.py` | Aggregation, tables, figures, diagnostics |
| `empirical.py` | CDNow / Grocery loaders and validation |
