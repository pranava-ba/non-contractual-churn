# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

<!-- Dated development log: a running record of what was done each session (newest first),
     alongside the usual Keep-a-Changelog release notes grouped within each day. -->

### 2026-07-30
- **Docs — Phase 2 overhaul (README + Sphinx site, all tiers):** the docs described only Phase 1;
  brought them current with the whole statistical-vs-ML body of work. **README:** broadened intro,
  a "statistical vs. machine-learned" Key-Features block, refreshed repository-structure tree (all
  Phase 2 modules, six datasets, `results/`, `Makefile`; dropped the now-ignored `paper/`), Phase 2
  runner quickstart + `make reproduce`, and a Documentation-Directory pointing at the selection
  guide. **`docs/api_reference.md`:** added every Phase 2 module (`datasets`, `ml_benchmark`,
  `conformal`, `amortized`, `estimate_bgnbd`, `clv_data`, `clv_benchmark`, `covariate_benchmark`,
  `churn`). **`docs/ARCHITECTURE.md`:** broadened §1 framing, added the statistical-vs-ML section and
  an updated module map. **New topic pages** (`ml_benchmark`, `conformal`, `amortized`, `bgnbd`,
  `clv_benchmark`, `churn`) plus a `selection.md` decision guide, wired into a restructured
  `index.rst`. **`TIMELINE.md`:** added the M7 milestone and corrected the roadmap (several "planned"
  items are done). Sphinx build succeeds (only the two pre-existing `_static`/`mermaid` warnings; no
  broken refs from the new pages).
- **Added — Phase 2 manuscript (expanded full draft):** `paper/manuscript_phase2.tex`, a
  self-contained Springer `sn-jnl` paper titled *"Non-contractual churn: statistical or
  machine-learned? A calibration benchmark of purchase, value, and timing forecasts"* (**25 pp**,
  compiles clean via `latexmk`; 24 references resolved, zero undefined). One combined paper folding
  in all Phase 2 dimensions — counts, monetary CLV, churn, and timing — around the unifying thesis
  that the shared parametric count assumption governs calibration, invariant to estimator
  (MLE≈MCMC≈amortized) and variant (Pareto/NBD≈BG/NBD), and is repairable model-agnostically
  (Conformalized BTYD) or structurally (Pareto/GGG timing). Expanded from the initial 18 pp draft
  with a formal problem-setup/notation section, full model likelihoods and predictive construction,
  formal CRPS/PIT/coverage/ECE definitions, per-dataset descriptions, three algorithm boxes (Gibbs,
  conformal recalibration, amortized net), a managerial decision-rule table, and extended-results
  appendices (accuracy/sharpness, 95% coverage, forecast-time `x>0` conditioning).
- **Added — reproducible paper assets:** `src/make_phase2_figures.py` (six figures →
  `paper/figures/fig_p2_*.png`) and `src/make_phase2_tables.py` (ten LaTeX tables emitted from
  `results/*_summary.csv`, matching the Phase 1 traceable-tables convention); `paper/refs_phase2.bib`
  for the ML/conformal/ECE references (Kuleshov 2018, Wang 2019, Friedman 2001, Koenker 1978, Guo
  2017, Lilliefors 1967, etc.), passed alongside `refs.bib`.
- **Added — planning:** `paper/phase2_outline.md`, the section-by-section scaffold (thesis, arc,
  results→asset map) the manuscript was drafted from.
- **Changed — `.gitignore`:** the `paper/` directory is now ignored — the research manuscript is a
  separate deliverable, kept out of the code repo. Already-tracked Phase 1 paper files are
  undisturbed; the new Phase 2 paper and future paper files are excluded going forward. The
  `src/make_phase2_*` reproducibility scripts stay tracked (they are code, not the paper).
- **Added — alternative typesettings (style experiment):** `src/make_phase2_variants.py` extracts the
  shared body of `manuscript_phase2.tex` into `paper/phase2_body_std.tex` and wraps it in two
  standard-`article` styles — `manuscript_phase2_modern.tex` (Times + New TX math, blue sans section
  headings, coloured links; 21 pp) and `manuscript_phase2_elegant.tex` (Palatino/newpx, centred
  small-caps headings, classic rules; 23 pp). Both compile clean (0 undefined citations) via natbib +
  `plainnat`. The Springer `sn-jnl` original is left untouched as the baseline.

### 2026-07-29
- **Planning:** added the **Phase 2** expansion plan to `ROADMAP.md` — a calibration benchmark
  of *statistical vs. machine-learning* customer forecasting (12 sequenced items: ML comparators,
  new public/Kaggle datasets, conformal recalibration, amortized neural inference, covariates,
  churn scoring, more BTYD variants, engineering maturity).
- **Added — Phase 2 Step 1:** `src/ml_benchmark.py` — a Poisson gradient-boosted RFM forecaster
  (`HistGradientBoostingRegressor(loss="poisson")`) whose Poisson predictive is scored under the
  existing CRPS / randomized-PIT / coverage engine, with a fair train/test customer split against
  Pareto/NBD (`compare_btyd_vs_gbm`).
- **Added — Phase 2 Step 3 (dataset loaders):** `src/datasets.py` — ingestion for four public
  benchmarks (Online Retail II, Olist, Dunnhumby, Ta-Feng) → the standard cohort summary via
  `elog_to_summary`; smoke-tested. Active rates span 1.6% (Olist, extreme zero-inflation) → 96%
  (Dunnhumby, extreme density), far wider than CDNow/Grocery alone.
- **Added — Phase 2 Step 4 (cross-dataset benchmark):** `src/run_ml_benchmark.py` +
  `results/ml_benchmark.csv`/`.log`. First pass (single seed, all customers): BTYD sharper on the
  classic sparse sets (CDNow, Grocery); on **Online Retail II, BTYD miscalibrates badly (PIT-KS
  0.20) and the GBM wins on both accuracy and calibration**; on extreme zero-inflation (Olist) the
  two are indistinguishable; on extreme density (Dunnhumby) BTYD wins but *both* are poorly
  calibrated. No universal winner — the calibration lens localizes where BTYD's assumptions break.
  Needs multi-seed confirmation before it becomes a paper claim.
- **Confirmed — Phase 2 Step 4 (multi-seed: 15 seeds × 7 datasets, paired Wilcoxon):**
  `src/run_ml_study.py` + `results/ml_study_summary.csv`. The map holds with tight sd and
  significance. Control passes (BTYD wins both axes on Simulated). BTYD wins-or-ties on 5/7 real
  datasets; **on Online Retail II BTYD's calibration collapses (PIT-KS 0.211±0.01 vs GBM 0.054)
  and it is also less accurate — ML wins both**, a confirmed counterexample to "structure always
  wins." On dense Dunnhumby *neither* model is well-calibrated (0.17–0.23). Multi-seed corrected
  a single-seed over-read (CDNow calibration is a tie, not a GBM win).
- **Added — Phase 2 Step 2 (stronger ML comparators):** `ml_benchmark.py` gains
  `hurdle_gbm_forecast` (zero-inflated hurdle — a P(active) classifier × shifted-Poisson positive
  count; the count analog of ZILN) and `quantile_gbm_forecast` (distribution-free multi-quantile
  GBM), plus `compare_all` scoring BTYD against all three ML models. Smoke test on the datasets
  where the Poisson assumption fails: the **distribution-free QuantileGBM is best on both accuracy
  and calibration** — Online Retail II PIT-KS **0.040** (vs BTYD 0.231, Poisson-GBM 0.072) and
  dense Dunnhumby **0.070** (vs BTYD 0.154, Poisson-GBM 0.253). Localizes BTYD's miscalibration to
  the parametric count assumption. **Confirmed by the full four-method multi-seed study (15 seeds ×
  7 datasets; all headline differences p≤6.1e-5 — every seed agrees):** BTYD wins accuracy AND
  calibration on Simulated/Grocery and stays sharpest on sparse CDNow; the distribution-free
  QuantileGBM wins both axes on Online Retail II, Dunnhumby and Ta-Feng (Dunnhumby PIT-KS 0.058 vs
  BTYD 0.169); the HurdleGBM is best-calibrated on the zero-heavy sets (CDNow/Online Retail/Olist).
  Conclusion: BTYD's miscalibration is the parametric-Poisson count assumption; distribution-free
  ML repairs it in the regimes where that assumption breaks.
- **Added — Phase 2 Step 5 (Conformalized BTYD):** `src/conformal.py` — distributional
  recalibration (Kuleshov, Fenner & Ermon 2018) of the BTYD predictive via an isotonic
  quantile-warp learned on a held-out calibration split (`recalibrate_samples`,
  `compare_conformal`). Smoke test: repairs BTYD's worst failure — Online Retail II PIT-KS
  **0.196→0.026** (CRPS 0.776→0.660, now beating the best ML), Dunnhumby 0.177→0.105 — while
  leaving already-calibrated Grocery untouched (0.037→0.042). Keeps BTYD's cheap fit +
  interpretability while fixing coverage. **Confirmed by the multi-seed before/after study (15
  seeds × 7 datasets, paired Wilcoxon):** significantly repairs every miscalibrated set — Online
  Retail II PIT-KS 0.212→0.044, Dunnhumby 0.164→0.097, Ta-Feng 0.072→0.027, CDNow 0.056→0.034
  (all p<0.001) — with accuracy preserved or improved (Online Retail CRPS 0.78→0.65), and no
  meaningful harm where already calibrated (Grocery unchanged). Recalibrated BTYD on Online Retail
  now matches the best ML on calibration and beats it on accuracy.
- **Added — Phase 2 Step 6 (amortized neural inference):** `src/amortized.py` +
  `run_amortized_check.py`. An MLP maps cohort summary statistics → Pareto/NBD parameters (trained
  once on 4000 simulated cohorts), so inference for any new cohort is a single forward pass — no
  sampler, no per-cohort optimisation. Confirmed: on 25 held-out simulated cohorts amortized ≈ MCMC
  (CRPS p=0.51; PIT-KS 0.032 vs 0.037, amortized marginally better), and it matches-or-beats MCMC
  calibration on every real dataset (Online Retail 0.121 vs 0.207). A third, *instant* estimation
  route confirming forecast calibration is estimation-method-agnostic.
- **Added — Phase 2 Step 7 (probabilistic CLV, first pass):** `src/clv_data.py` (monetary loaders
  + CLV summary for Online Retail II / Ta-Feng / Dunnhumby) and `src/clv_benchmark.py` comparing
  Pareto/NBD + Gamma-Gamma vs. a deep zero-inflated-lognormal MLP (ZILN, Wang et al. 2019, torch)
  on the monetary CLV target under CRPS/PIT/coverage. Smoke test shows a calibration-vs-sharpness
  tradeoff: BTYD+GG far more accurate but miscalibrated on Online Retail (CRPS 418, PIT-KS 0.215);
  ZILN well-calibrated (0.027) but imprecise (heavy lognormal tail); on dense Dunnhumby ZILN wins
  both (PIT-KS 0.048 vs 0.127, equal CRPS). ZILN then tuned (validation early-stop + heavy-tail cap
  fixed the over-dispersion: Online Retail CRPS 1744→519). **Confirmed by the multi-seed study (15
  seeds × 3 monetary datasets, paired Wilcoxon, `run_clv_study.py`):** the deep ZILN is
  significantly better calibrated than BTYD+Gamma-Gamma on every dataset (Online Retail PIT-KS
  0.212→0.031, Ta-Feng 0.082→0.020, Dunnhumby 0.143→0.073; all p<0.001) at comparable accuracy
  (CRPS tied on Ta-Feng/Dunnhumby, BTYD+GG a bit sharper on Online Retail). Extends the count
  finding to money: structural CLV inherits the Poisson miscalibration; the distribution-learning
  ZILN stays calibrated.
- **Added — Phase 2 Step 7 (covariate value):** `src/covariate_benchmark.py`. On the 801
  demographics-carrying Dunnhumby households, adding demographics (age/income/marital/home/kids) to
  the ML count model does NOT improve calibration (PIT-KS 0.206→0.205, paired Wilcoxon p=0.77) or
  sharpness — RFM already captures what matters; the dense-data miscalibration is about the count
  distribution, not missing covariates.
- **Building — Phase 2 Steps 8–12:** (a) **Step 8 timing** — added `t_next`/`litt` to the data
  pipeline and `run_timing_study.py`; smoke test shows Pareto/GGG beats Pareto/NBD on next-purchase
  timing for regular data (MdAE 2.68 vs 4.37 at k=3), addressing Simon's stated timing failure.
  (b) **Step 9 churn** — `churn.py` + `run_churn_study.py` score P(active) calibration (Brier +
  ECE) for BTYD vs an ML classifier. (c) **Step 10 BG/NBD** — `estimate_bgnbd.py` (MLE + vectorised
  `min(Geometric(p), Poisson(λT*))` predictive; recovers E(λ), competitive calibration) +
  `run_bgnbd_study.py`. (d) **Step 11 rigor** — `run_pit_bootstrap.py`, a parametric-bootstrap
  parameter-adjusted PIT-KS null. (e) **Step 12 tests** — `tests/test_phase2.py` (6 numerical
  tests for the new modules, all passing). **All confirmed by multi-seed studies:** Step 8 timing —
  Pareto/GGG beats Pareto/NBD on next-purchase median error where regular (Sim k=3 3.23 vs 4.49,
  Grocery 2.98 vs 3.89, p<0.001). Step 9 churn — BTYD's P(active) well-calibrated where its
  assumptions hold, badly miscalibrated on misspecified/dense data (Online Retail ECE 0.185 vs ML
  0.051), matching the count/CLV story. Step 10 — Pareto/NBD and BG/NBD essentially interchangeable
  (CRPS within 0.5%, calibration close, both broken on misspecified data): model variant is
  immaterial within the family. Step 11 — the naive 1.36/√n PIT-KS critical value is ~10% too small
  (Lilliefors); CDNow's mild departure survives the parameter-adjusted bootstrap null, Grocery is
  calibrated.
- **Docs:** added `docs/datasets.md` — why data age is irrelevant to a calibration study and why we
  avoid newer synthetic / cross-sectional datasets; wired into the Sphinx toctree.
- **Engineering (Phase 2 Step 12, partial):** added GitHub Actions CI
  (`.github/workflows/ci.yml` — pytest on py3.9/3.11/3.12 + flake8), `CITATION.cff`, and a
  `Makefile` (`make reproduce` / test / lint / format / docs / paper); `pyproject.toml` now
  declares `black`/`flake8` in `[dev]` and a `[ml]` extra (`scikit-learn`).
- **Process:** started keeping this dated development log in the changelog.

### 2026-07-28
- **Fixed — CLV posterior (`clv.py`):** `sample_posterior_nu` now samples the mean transaction
  value from the correct **Inverse-Gamma** posterior instead of a Gamma. The previous code
  returned per-customer mean spend ~1/observed (orders of magnitude too small and anti-correlated
  with the data); posterior spend now tracks observed spend with proper shrinkage.
- **Fixed — `timing.py`:** the empty-input branch of `score_timing_forecast` now returns the
  `timing_MAE` key (was `timing_nAE`), so cross-cohort aggregation no longer breaks.
- **Added:** numerical regression tests `test_clv_posterior_spend_is_realistic` (posterior spend
  tracks observed, correlation > 0.9) and `test_parameter_recovery` (MLE/MCMC recover `E(λ)` and
  agree); documentation suite `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `CONTRIBUTING.md`,
  `TIMELINE.md`, `CHANGELOG.md`, `SECURITY.md`, and a Documentation Directory in the README.
- **Changed:** removed the unused `seaborn` dependency from `pyproject.toml`; clarified the README
  (Pyodide app is "no-server-required", CDN-loaded, not "standalone"; softened "proves" to "shows …
  via a law-of-total-variance scaling argument").

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
