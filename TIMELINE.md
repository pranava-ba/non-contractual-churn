# Project Timeline & Roadmap

Milestone progression for the Pareto/NBD Extension, and where it is going next. The
research narrative and its status are tracked in more detail in
[`ROADMAP.md`](ROADMAP.md).

## Milestones (completed)

### M1 — Calibration & probabilistic evaluation (core, "A+D")
Built the reproducible pipeline (`simulate`, `estimate`, `score`, `run_study`,
`analyze`, `empirical`) and evaluated Pareto/NBD purchase forecasts with proper scoring
rules and calibration diagnostics for the first time in customer-base analysis.
**Result:** MCMC and MLE are statistically **equivalent** (TOST), refuting the headline
claim that Bayesian estimation yields better forecast uncertainty.

### M2 — Fair-baseline caveat
Traced an apparent "MCMC wins at small N" signal to a maximum-likelihood optimiser
diverging into a numerical-overflow region. Hardened `fit_mle` (bounded log-parameters,
method-of-moments start, overflow rejection); the artefact vanished.

### M3 — Evaluation traps & robustness
Documented two pitfalls — degenerate interval coverage on zero-inflated counts, and
outcome-conditioned PIT — and stress-tested the two central distributional assumptions
(inter-purchase regularity, bimodal heterogeneity). Calibration proved robust.

### M4 — Pareto/GGG loop (Extension A)
Implemented a common-`k` Pareto/GGG sampler (`estimate_ggg.py`) and showed that where
Pareto/NBD's calibration frays under strong regularity (`k ≥ 3`), the timing-aware model
**restores** it and corrects a downward bias in `E(λ)`.

### M5 — Springer Nature manuscript
Ported the paper to the `sn-jnl` template, expanded to 23 pages with equivalence tests,
sharpness, log-score, point-error, per-horizon and extreme-grid tables, and a
convergence-diagnostics appendix (R-hat/ESS + forecast-score reproducibility).

### M6 — Extensions B & E, packaging, docs
Added purchase-timing forecasting (`timing.py`, Extension B) and Gamma-Gamma
probabilistic CLV (`clv.py`, Extension E); PEP 621 packaging, MIT license, pytest suite,
Sphinx/ReadTheDocs docs, and a Pyodide interactive app.

## Release history

| Version | Date | Highlights |
| --- | --- | --- |
| **1.0.0** | 2026-07-28 | First public release: full calibration study, Pareto/GGG, extensions B & E, paper, docs. |

See the [CHANGELOG](CHANGELOG.md) for details.

## Roadmap (planned)

- **Integrate the extensions into scored studies.** Wire `timing.py` and `clv.py` into
  runner scripts and report CRPS/PIT/coverage tables for `t_{x+1}` and CLV, mirroring the
  purchase-count study.
- **Extension C — model & ML benchmark.** Add BG/NBD, MBG/NBD, and a gradient-boosted
  RFM baseline under the same proper-scoring lens; test whether *model* choice (as opposed
  to estimation method) moves calibration.
- **Heterogeneous-k Pareto/GGG.** Generalise the common-`k` sampler to
  `k_i ~ Γ(t, γ)` (full Platzer–Reutterer), nesting the current model.
- **Covariates.** Time-varying and customer-level covariates in the purchase and dropout
  processes, and their effect on calibration.
- **Further misspecification axes.** Non-stationarity, seasonality, and dependence between
  the purchase and dropout processes.
- **Log-score in the main grid.** Persist predictive draws so the logarithmic score is
  reported across the full simulation grid, not only representative datasets.
