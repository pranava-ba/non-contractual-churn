# API Reference

## Module: `estimate`

### `fit_mle(df, seed=0, n_start=3, x0=None)`
Fits population parameters $(r, \alpha, s, \beta)$ using robustified closed-form Pareto/NBD log-likelihood with method-of-moments initialization and parameter bounds $[10^{-5}, 10^5]$.

### `fit_mcmc(df, n_draws=6000, burn_in=2000, thin=8, seed=0, hyper=None, init=None)`
Runs the Abe (2009) data-augmentation Gibbs sampler returning population parameter draws and individual $(\lambda_i, \mu_i, \tau_i)$ posteriors.

## Module: `estimate_ggg`

### `fit_ggg(df, n_draws=1500, burn_in=500, thin=5, seed=0, hyper=None, n_quad=40)`
Fits the common-$k$ Pareto/GGG model with Gamma-distributed inter-purchase times using augmented Metropolis-within-Gibbs sampling.

## Module: `score`

### `crps_samples(pred, y)`
Computes sample-based Continuous Ranked Probability Score per customer.

### `log_score_smoothed(pred, y, eps=1e-6)`
Computes Laplace/Epsilon smoothed discrete logarithmic score.

### `randomized_pit(pred, y, rng)`
Calculates Czado et al. (2009) randomized probability integral transform.

## Module: `timing` (Extension B)

### `sample_next_purchase_time_pnbd(lam, mu, tau, T_cal, seed=0)`
Generates posterior-predictive wait times until next purchase $t_{x+1}$ under Pareto/NBD.

### `sample_next_purchase_time_pggg(lam, mu, tau, k, T_cal, t_x, seed=0)`
Generates posterior-predictive wait times under Pareto/GGG Gamma renewal process.

## Module: `clv` (Extension E)

### `fit_gamma_gamma(x, m_obs)`
Estimates Gamma-Gamma monetary model parameters $(p, q, v)$ via MLE.

### `predict_clv_distribution(pred_x_star, nu_draws, discount_rate=0.0)`
Generates probabilistic Customer Lifetime Value (CLV) forecast distributions.

---

## Phase 2 — statistical vs. machine-learned

The modules below extend the framework from *within-family* comparison (estimator, variant)
to *structural-vs-ML* comparison across counts, value, churn and timing. See the
[selection guide](selection.md) for how they fit together.

## Module: `datasets`

Loaders that turn four public transaction logs into the standard cohort summary, mirroring
`empirical.elog_to_summary`. Active rates span 1.6% (Olist) to 96% (Dunnhumby).

### `load_online_retail_ii()`, `load_olist()`, `load_dunnhumby()`, `load_tafeng()`
Return the raw event log for each benchmark as a `DataFrame`.

### `load_summary(name)`
Returns the ready-to-score cohort summary (`x, t_x, T_cal, x_star`) for
`name ∈ {"OnlineRetailII", "Olist", "Dunnhumby", "Ta-Feng"}` (and the sparse CDNow/Grocery
benchmarks via `empirical`).

## Module: `ml_benchmark`

Probabilistic gradient-boosted RFM forecasters scored under the BTYD scoring engine. See
[ML benchmark](ml_benchmark.md).

### `rfm_features(df)`
Builds the recency–frequency–monetary feature matrix from a cohort summary.

### `poisson_gbm_forecast(X_train, y_train, X_test, n_draws=400, seed=0)`
Poisson-loss gradient boosting; predictive is `Poisson(ĝ(RFM))` — the ML analogue of the BTYD
count assumption.

### `hurdle_gbm_forecast(X_train, y_train, X_test, n_draws=400, seed=0)`
Two-part (hurdle) model: a boosted `P(active)` classifier × a boosted shifted-Poisson positive
count.

### `quantile_gbm_forecast(X_train, y_train, X_test, n_draws=400, seed=0)`
Distribution-free multi-quantile gradient boosting (pinball loss); makes no parametric
assumption about the count law.

### `compare_btyd_vs_gbm(df, horizon, test_frac=0.3, seed=0, ...)` / `compare_all(df, horizon, test_frac=0.3, seed=0, ...)`
Score BTYD against the Poisson-GBM (`compare_btyd_vs_gbm`) or against all three ML forecasters
(`compare_all`) on a fair customer split.

## Module: `conformal`

Distributional recalibration of the BTYD predictive. See [Conformalized BTYD](conformal.md).

### `recalibrate_samples(pred_cal, y_cal, pred_test, n_out=500, seed=0)`
Learns an isotonic PIT→coverage warp on a calibration split and applies it to test predictive
samples.

### `compare_conformal(df, horizon, recal_frac=0.5, seed=0, ...)`
Reports PIT-KS, CRPS and coverage before ("raw") and after recalibration.

## Module: `amortized`

One-pass neural estimator for the Pareto/NBD. See [amortized inference](amortized.md).

### `cohort_features(df)`
Summary-statistic feature vector for a cohort.

### `generate_training_data(n_cohorts=4000, seed=0)`
Simulates cohorts and their known parameters as `(X, Y)` training pairs.

### `fit_amortizer(X, Y, seed=0)`
Trains the MLP mapping cohort summaries → `(r, α, s, β)`.

### `amortized_params(am, df)`
Instant single-forward-pass parameter estimate for a new cohort.

### `compare_amortized_vs_mcmc(df, horizon, am, seed=0, mcmc_draws=1500)`
Head-to-head CRPS and PIT-KS of the amortized estimator versus MCMC.

## Module: `estimate_bgnbd`

BG/NBD variant under the same lens. See [BG/NBD](bgnbd.md).

### `fit_bgnbd(df, seed=0, n_start=3) -> BGNBDResult`
Multi-start MLE of the BG/NBD population parameters.

### `bgnbd_predict(df, fit, horizon, n_draws=400, seed=0)`
Predictive draws of future counts under the fitted BG/NBD.

## Module: `clv_data`

Monetary cohort loaders for the CLV benchmark.

### `load_online_retail_ii_money()`, `load_tafeng_money()`, `load_dunnhumby_money()`
Return the monetary transaction log for each cohort.

### `clv_summary(txn, cal_weeks, horizon)` / `load_clv_summary(name)`
Build (or load by name) the monetary cohort summary with observed and holdout spend.

## Module: `clv_benchmark`

Structural vs. deep probabilistic CLV. See [probabilistic CLV](clv_benchmark.md).

### `clv_features(df)`
Feature matrix for the value models.

### `btyd_gg_clv_predict(df, horizon, seed=0, mcmc_draws=1500)`
Pareto/NBD counts × Gamma-Gamma spend → predictive value distribution.

### `ziln_clv_predict(X_train, y_train, X_test, n_draws=400, seed=0, epochs=1000)`
Deep zero-inflated-lognormal value model (requires `torch`).

### `compare_clv(df, horizon, test_frac=0.3, seed=0, mcmc_draws=1500)`
Scores structural CLV against the deep ZILN on the monetary target.

## Module: `covariate_benchmark`

### `load_demographics()`
Loads the Dunnhumby household demographics.

### `compare_covariate_value(horizon=26, test_frac=0.3, seed=0, ...)`
Tests whether adding demographics to the ML value model improves calibration (it does not).

## Module: `churn`

Calibration of the active-customer probability. See [churn calibration](churn.md).

### `ece(p, outcome, n_bins=10)`
Expected calibration error of a probability vector.

### `churn_scores(p_active, outcome)`
Returns ECE and Brier score.

### `compare_churn(df, horizon, test_frac=0.3, seed=0, mcmc_draws=1500)`
BTYD `P(active)` versus a boosted classifier.
