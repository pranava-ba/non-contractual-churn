# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **CLV posterior (`clv.py`):** `sample_posterior_nu` now samples the mean transaction
  value from the correct **Inverse-Gamma** posterior instead of a Gamma. The previous
  code returned per-customer mean spend ~1/observed (orders of magnitude too small and
  anti-correlated with the data); posterior spend now tracks observed spend with proper
  shrinkage.
- **`timing.py`:** the empty-input branch of `score_timing_forecast` now returns the
  `timing_MAE` key (was `timing_nAE`), so cross-cohort aggregation no longer breaks.

### Added
- Numerical regression tests: `test_clv_posterior_spend_is_realistic` (posterior spend
  tracks observed, correlation > 0.9) and `test_parameter_recovery` (MLE/MCMC recover
  `E(λ)` and agree).
- Documentation suite: `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `CONTRIBUTING.md`,
  `TIMELINE.md`, `CHANGELOG.md`, `SECURITY.md`, and a Documentation Directory section in
  the README.

### Changed
- Removed the unused `seaborn` dependency from `pyproject.toml`.
- Clarified the README: the Pyodide app is "no-server-required" (CDN-loaded, needs a
  network connection) rather than "standalone"; softened "proves" to "shows … via a
  law-of-total-variance scaling argument".

## [1.0.0] — 2026-07-28

First public release.

### Added
- **Estimation:** robust bounded multi-start MLE and a pure-`numpy` Abe (2009)/BTYDplus
  data-augmentation MCMC Gibbs sampler (`estimate.py`); common-`k` Pareto/GGG augmented
  sampler (`estimate_ggg.py`).
- **Scoring:** sample CRPS, Laplace-floored discrete log score, Czado et al. (2009)
  randomized PIT, interval coverage, and sharpness (`score.py`, `logscore_check.py`).
- **Study:** simulation runners and analysis producing the paired Wilcoxon /
  Benjamini–Hochberg and TOST equivalence results, tables, and figures.
- **Extensions:** purchase-timing forecasting `t_{x+1}` (`timing.py`, Extension B) and
  Gamma-Gamma probabilistic CLV (`clv.py`, Extension E).
- **Empirical validation** on the CDNow and Grocery public benchmarks (`empirical.py`).
- **Convergence diagnostics:** split-R-hat, ESS, and forecast-score reproducibility
  across overdispersed chains (`convergence.py`).
- **Paper:** Springer Nature `sn-jnl` manuscript, *"Non-contractual churn with MCMC: are
  Pareto/NBD purchase forecasts calibrated?"*
- **Tooling:** PEP 621 packaging, MIT license, pytest suite, Sphinx/ReadTheDocs docs, and
  a Pyodide interactive web application.

[Unreleased]: https://github.com/pranava-baascaran/pareto-nbd-extension/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/pranava-baascaran/pareto-nbd-extension/releases/tag/v1.0.0
