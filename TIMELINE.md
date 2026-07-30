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

### M7 — Statistical vs. machine-learned calibration benchmark (Phase 2)
Brought machine learning into the same proper-scoring lens across counts, value, churn and
timing, on seven public cohorts (active rates 1.6%→96%). **Result:** calibration is governed
by the shared **parametric count assumption** — invariant to estimation method
(MLE ≈ MCMC ≈ amortized) and to model variant (Pareto/NBD ≈ BG/NBD) — and is repairable
model-agnostically (**Conformalized BTYD**) or structurally (**Pareto/GGG** timing). Added
`ml_benchmark`, `conformal`, `amortized`, `estimate_bgnbd`, `clv_benchmark`/`clv_data`,
`covariate_benchmark`, `churn`, and `datasets`, each with a confirmed multi-seed study runner
and `results/*_summary.csv`. CI (GitHub Actions), `CITATION.cff`, and a `make reproduce`
Makefile were added alongside.

## Release history

| Version | Date | Highlights |
| --- | --- | --- |
| **1.0.0** | 2026-07-28 | First public release: full calibration study, Pareto/GGG, extensions B & E, paper, docs. |

See the [CHANGELOG](CHANGELOG.md) for details.

## Roadmap (planned)

Completed in **M7** (see above): the extensions are now wired into scored studies
(`run_timing_study.py`, `run_clv_study.py`); the model/ML benchmark and BG/NBD are done
(`ml_benchmark.py`, `estimate_bgnbd.py`); and the covariate question is answered
(`covariate_benchmark.py` — demographics add nothing over RFM). Still open:

- **Heterogeneous-k Pareto/GGG.** Generalise the common-`k` sampler to
  `k_i ~ Γ(t, γ)` (full Platzer–Reutterer), nesting the current model.
- **More BTYD variants.** MBG/NBD and BG/CNBD-k under the same lens (BG/NBD already showed the
  variant is immaterial).
- **Further misspecification axes.** Non-stationarity, seasonality, and dependence between
  the purchase and dropout processes.
- **Log-score in the main grid.** Persist predictive draws so the logarithmic score is
  reported across the full simulation grid, not only representative datasets.
- **Importable package API.** Refactor `src/` into an installable `paretonbd` library, then
  PyPI/Zenodo release (deferred to the very end).
