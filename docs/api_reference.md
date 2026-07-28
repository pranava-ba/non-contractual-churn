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
