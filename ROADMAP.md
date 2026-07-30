# Pareto/NBD Extension — Research Roadmap

Extending **Simon, L. (2025).** *A generalised comparison of Pareto/NBD based
forecasts using MCMC, maximum likelihood, and heuristics.* Journal of Business
Economics 95:1079–1105. https://doi.org/10.1007/s11573-025-01237-8

Goal: **journal/conference paper**. Stack: **Python**.

---

## ▶ CURRENT STATE (handoff, updated 2026-07-29)

**Phase 1 (original paper) — COMPLETE.** Manuscript is `paper/manuscript.tex` (Springer Nature
`sn-jnl`, 23 pp, retitled *"Non-contractual churn with MCMC: are Pareto/NBD purchase forecasts
calibrated?"*). Findings: MCMC ≡ MLE (statistically equivalent, TOST); forecasts calibrated &
robust; Pareto/GGG restores calibration under regularity; model ≫ heuristic; two evaluation traps.
`paper/manuscript_beta.tex` is the pre-Springer article-class snapshot.

**Phase 2 (calibration benchmark: statistical vs ML) — Steps 1–11 DONE, all confirmed with
multi-seed studies (see the "Phase 2" section below for per-step status and `CHANGELOG.md` for the
dated log with numbers).** One-line story: *calibration is governed by the parametric count
assumption shared across the BTYD family and by correct evaluation — not by estimation method or
model variant; where that assumption fails (bulk-buying/dense data), distribution-free ML or a
one-pass conformal recalibration fixes it.* Contributions: cross-dataset ML-vs-BTYD benchmark,
Conformalized BTYD (repair), amortized neural inference, probabilistic CLV (deep ZILN), timing
(Pareto/GGG beats Pareto/NBD), churn P(active) calibration, BG/NBD (variant immaterial), bootstrap
PIT-KS null. This is realistically a **second paper**.

**What's left:**
- **Writing** — the Phase 2 paper/section (the user asked to do writing LAST). Write from `CHANGELOG.md`.
- **Step 12 finalization** (optional): importable `import paretonbd` API (package refactor), PyPI/Zenodo (need accounts). CI/CITATION.cff/Makefile/tests are done.
- **Bundle sync** — `github_upload_bundle/` + `.zip` are ~20 modules behind; re-sync before any GitHub push:
  `cd github_upload_bundle && zip -rq ../github_upload_bundle.zip . -x '*/__pycache__/*' '*.pyc'`

**New src/ modules from Phase 2:** `ml_benchmark`, `datasets`, `conformal`, `amortized`, `clv_data`,
`clv_benchmark`, `covariate_benchmark`, `estimate_bgnbd`, `churn`, `timing`, and their `run_*_study`
runners; results in `results/*_summary.csv`; new tests in `tests/test_phase2.py`.

---

## What the original paper does (baseline we must beat)

- Compares **estimation methods** (MCMC [Abe 2009], MLE, heuristic) *within the
  classical Pareto/NBD model* on **4 forecast tasks**:
  1. number of future purchases, 2. active-customer identification,
  3. Top A% (10/20%) customers, 4. timing of next purchase.
- **Data:** 3,000 *simulated* datasets (primary) + 4 empirical (CDNow, Grocery =
  public; Gusto, Homeshopping = proprietary).
- **Simulation params (Table 2):** E(λ)∈[.02,.3], CV(λ)∈[.5,2.5], E(μ)∈[.02,.2],
  CV(μ)∈[.5,2.5], N∈[1000,4000], T∈[26,72] wks, T*∈{13,26,52}. Acquisition within
  first 90 days. All drawn from uniforms.
- **Tools (R):** MLE = CLVTools; MCMC = BTYDplus (Abe 2009), 10k draws, 4 chains,
  burn-in 2k, thin 20.
- **Findings:** models beat heuristics on tasks 1–3; MCMC slightly > MLE + gives
  intervals; timing (task 4) too inaccurate to use.
- **Key weaknesses we exploit:** evaluates only *point* errors (nMAE/nRMSE/nMdAE),
  never tests interval **calibration**; compares by **eyeballing boxplots** (no
  significance tests); only the *estimator* varies, never the *model*.

---

## Chosen first direction: A + D — Calibration & probabilistic evaluation

**One-line pitch:** Simon claims MCMC's edge is the *full posterior* (uncertainty
quantification), but she never checks whether those predictive intervals are
**calibrated** or **sharp**, and compares methods only by eye. We evaluate the
*full predictive distribution* of future purchases with **proper scoring rules
(CRPS, log score), calibration diagnostics (PIT / coverage), and sharpness**, and
replace boxplot-eyeballing with **formal paired tests** (Wilcoxon, Diebold–Mariano
+ multiple-comparison correction). This converts her qualitative "slightly better,
plus intervals" into a quantitative, testable claim — and tells practitioners
whether the intervals can be trusted for decisions.

**Why journal-worthy:** proper scoring rules + calibration (Gneiting & Raftery
2007; Gneiting, Balabdaoui & Raftery 2007 sharpness principle; Czado, Gneiting &
Held 2009 for count PIT) are standard in forecasting but have ~never been applied
to BTYD/CBA purchase forecasts. Methodological contribution, not a replication.

**Pipeline (see `src/`):**
1. `simulate.py` — reproduce her Pareto/NBD DGP (Table 2). ✅ built
2. `fit.py` — MLE + Bayesian (MCMC) Pareto/NBD → per-customer *predictive
   distribution* of x* (posterior-predictive / bootstrap samples).
3. `score.py` — point (nMAE/nRMSE/nMdAE, replicate her as sanity check) +
   probabilistic (CRPS, coverage @ 50/80/95%, PIT histogram, sharpness).
4. `tests.py` — paired Wilcoxon signed-rank + Diebold–Mariano across datasets,
   Holm/BH correction, effect sizes + CIs.
5. `empirical.py` — validate on CDNow (public); check real metrics vs sim intervals.

**Compute note:** full 3,000× MCMC is cluster-scale. The *methodology* claim holds
on a tractable subset (few hundred datasets) + empirical data. Design for scale,
run a subset.

### STATUS — A+D executed and verified (see `paper/results_summary.md`)
Pipeline built + validated: `simulate.py`, `estimate.py` (MLE + Abe Gibbs MCMC),
`score.py`, `run_study.py`, `analyze.py`, `empirical.py`. Ran 90 main + 60 extreme
simulated datasets (15 reps) + CDNow/Grocery. **Verified findings:**
- **H1 REFUTED:** MCMC ≈ MLE for calibration/accuracy at all N (Wilcoxon BH p≥0.15).
  Original headline is dead; the null is the result.
- Early "MCMC wins at small N" was an **MLE optimiser overflow artifact** — fixed
  (bounded params + MoM init + overflow rejection); gap vanished. Fair-baseline
  caveat is now a contribution.
- **H3 CONFIRMED:** zero-inflation masking (all-cust cov95≈0.98) + active-customer
  under-dispersion (≈0.90); worse at small N / low frequency.
- **Model ≫ heuristic:** BH p<1e-3 every metric (extends Simon to probabilistic scoring).
- **Empirical:** all three findings replicate on CDNow (N=2357) + Grocery (N=1525).

**Under-dispersion claim RETRACTED** — was a selection artifact of conditioning on
realised activity (y>0); with forecast-time conditioning (x>0) the forecasts are
well-calibrated (PIT-KS ~0.03-0.04, on sim + real data). Two evaluation traps
documented: coverage-on-counts is degenerate; outcome-conditioning fabricates
miscalibration.

**Misspecification stress-tests (both robust):** fit Pareto/NBD to (a) regular
Gamma-k IPT and (b) 2-segment mixture heterogeneity. Calibration robust to both —
only IPT k≥3 nudges the repeat-buyer subgroup past significance; mixture shows no
break even at 10:1. Figures: fig1 coverage, fig3 PIT, fig4 misspecification.

Narrative LOCKED: *Pareto/NBD purchase forecasts are calibrated and remarkably
robust; MCMC=MLE (estimator immaterial); model≫heuristic; calibration governed by
correct evaluation, not model sophistication.* A reassurance + methodological-caution
paper. Two principled stress-tests done — STOP stress-testing (further search = motivated).
Remaining: Results/Intro/Discussion prose, typeset (Springer LaTeX).

---

## Saved for later — remaining directions

### B. Fix the next-purchase-timing forecast (her stated failure)  ⭐ clearest "beyond"
She declares timing "too inaccurate to use" (plug-in median of λ). Target it:
predict from the **posterior-predictive distribution of t_{x+1}** instead of a
plug-in; or a **discrete-time hazard model / ML regressor on RFM**; or use
**Pareto/GGG** (relaxes exponential inter-purchase times — the exact reason her
timing forecast fails). Beating a result the author herself calls a failure is the
most defensible "we did better."

### C. Modern ML / alternative-model benchmark  — biggest "wow", more effort
She only varies the *estimator*, never the *model*. Add:
- **Other BTYD:** BG/NBD, MBG/NBD, **Pareto/GGG** (Platzer & Reutterer 2016).
- **ML:** gradient boosting on RFM features; a neural/deep-probabilistic CLV model.
Run all on the same 4 tasks + the new probabilistic scoring from A. If ML/Pareto-GGG
wins on any task → clear "beyond." Even a null ("simple BTYD still beats ML on
sparse CBA data") is publishable.

### E. Extend to covariates / spending process → CLV  — largest scope, biggest gap she named
She flags absence of covariates + monetary/spending process as the #1 limitation.
Add the **Gamma-Gamma spend model** and/or **covariate-based Pareto/NBD**, redo the
generalised comparison on **CLV** (money) rather than purchase counts. Highest
managerial relevance; most work.

**Suggested sequencing:** A+D (rigorous core) → B (headline "beat her failure") →
C or E (scope/novelty). A+D's scoring infrastructure is reused by B and C.

---

## Phase 2 — Calibration benchmark: statistical vs. ML customer forecasting

The reframe: our contribution is the *evaluation lens* (proper scoring + PIT calibration +
TOST). The ML-vs-BTYD literature only ever compares on point error — nobody on calibration.
So we bring ML into the same CRPS/PIT framework and ask whether flexible ML produces
better-*calibrated* forecasts than parsimonious BTYD, or whether structure wins on sparse,
zero-inflated count data. Honest either way; extends the thesis rather than contradicting it.

Executing one by one (status tags: TODO / WIP / DONE):

1. **ML comparator infrastructure** — RFM feature builder + probabilistic ML forecasters that
   plug into `score.py`. Start: Poisson gradient boosting (sklearn
   `HistGradientBoostingRegressor(loss="poisson")`), predictive = `Poisson(ĝ(RFM))`; score
   CRPS/PIT/coverage vs. BTYD on existing simulated + CDNow + Grocery, with a fair
   train/test customer split. No new data needed. **[WIP:** `src/ml_benchmark.py` built +
   smoke-tested on sim/CDNow/Grocery — BTYD sharper everywhere, GBM competitively/better
   *calibrated* on real data. Next: full multi-seed study + tables.**]**
2. **Stronger ML comparators** — zero-inflated (hurdle) GBM (the count analog of ZILN,
   Wang et al. 2019) + distribution-free quantile GBM. **[DONE:** `hurdle_gbm_forecast`,
   `quantile_gbm_forecast`, `compare_all` in `ml_benchmark.py`; confirmed by the four-method
   15-seed study (all headline diffs p≤6.1e-5). QuantileGBM wins both axes where Poisson fails
   (Online Retail II, Dunnhumby, Ta-Feng); HurdleGBM best-calibrated on zero-heavy sets; BTYD wins
   on Simulated/Grocery and sharpest on CDNow. Mechanism: BTYD's miscalibration = the parametric-
   Poisson assumption. The ZILN deep model proper (monetary) belongs to the CLV extension
   (Step 7).**]**
3. **Dataset ingestion layer** — loaders for new public sets → the cohort summary, mirroring
   `empirical.elog_to_summary`. **[DONE:** `src/datasets.py` loads Online Retail II, Olist,
   Dunnhumby, Ta-Feng; active rates span 1.6%→96%. Instacart skipped (no absolute timestamps).**]**
4. **Empirical calibration benchmark** — BTYD vs. ML across all datasets; CRPS/PIT/coverage/TOST
   tables. Olist = zero-inflation stress test; Dunnhumby = dense + covariates. **[DONE:**
   `src/run_ml_study.py`, 15 seeds × 7 datasets, paired Wilcoxon (`results/ml_study_summary.csv`).
   Confirmed map: BTYD wins/ties 5/7; on Online Retail II ML wins both (BTYD PIT-KS 0.211±0.01);
   dense Dunnhumby poorly calibrated for both. Remaining polish: TOST on the tie cases, a paper
   table + section.**]**
5. **Conformal recalibration ("Conformalized BTYD")** — split-conformal / isotonic on the BTYD
   predictive to restore coverage. **[DONE:** `src/conformal.py` + `run_conformal_study.py`
   (`results/conformal_study_summary.csv`). Confirmed (15 seeds, paired Wilcoxon): repairs every
   miscalibrated set (Online Retail II 0.212→0.044, Dunnhumby 0.164→0.097, Ta-Feng 0.072→0.027,
   CDNow 0.056→0.034; all p<0.001), preserves/improves accuracy, no harm where calibrated.
   Recalibrated BTYD matches/beats the best ML while keeping interpretability.**]**
6. **Amortized neural inference** — neural estimator vs. MCMC; does it match calibration?
   **[DONE:** `src/amortized.py` + `run_amortized_check.py`. An MLP (summary stats → Pareto/NBD
   params, trained once on 4000 sim cohorts) gives instant inference; confirmed amortized ≈ MCMC on
   25 held-out cohorts (CRPS p=0.51) and matches/beats MCMC calibration on all real data. Third,
   instant estimation route — forecast calibration is estimation-method-agnostic.**]**
7. **Probabilistic CLV — structural vs. deep (ZILN)** — Pareto/NBD + Gamma-Gamma vs. a deep
   zero-inflated-lognormal MLP (Wang et al. 2019) on the monetary target. **[DONE:** `src/clv_data.py`,
   `src/clv_benchmark.py`, `run_clv_study.py`, `covariate_benchmark.py`. Confirmed (15 seeds, paired
   Wilcoxon): the deep ZILN is significantly better calibrated than BTYD+GG on all 3 monetary
   datasets (Online Retail 0.212→0.031, Ta-Feng 0.082→0.020, Dunnhumby 0.143→0.073; all p<0.001) at
   comparable accuracy — structural CLV inherits the Poisson miscalibration. Covariate value:
   demographics add nothing (Dunnhumby, p=0.77) — RFM suffices.**]**
8. **Integrate existing extensions** — Extension E (CLV) done in Step 7; Extension B (timing).
   **[DONE:** `run_timing_study.py` (+ `t_next`/`litt` in the data pipeline). Confirmed (12 seeds):
   Pareto/GGG significantly beats Pareto/NBD on next-purchase-timing median error where purchasing
   is regular (Sim k=3 MdAE 3.23 vs 4.49; Grocery 2.98 vs 3.89; all p<0.001) — rebuts Simon's
   "timing too inaccurate." CRPS mixed (better median, not always sharper distribution).**]**
9. **Score the churn dimension** — calibrate P(alive) / active-customer identification.
   **[DONE:** `churn.py` + `run_churn_study.py`. Confirmed (15 seeds, Brier + ECE): BTYD's P(active)
   is well-calibrated where its assumptions hold (Simulated/Grocery) but badly miscalibrated on
   misspecified/dense data (Online Retail ECE 0.185 vs ML 0.051; Dunnhumby, Ta-Feng), where the ML
   classifier wins — the churn-dimension analog of the whole Phase 2 finding, matching the title.**]**
10. **More BTYD variants under the lens** — BG/NBD, MBG/NBD, full heterogeneous-k Pareto/GGG,
    BG/CNBD-k. **[DONE (BG/NBD):** `estimate_bgnbd.py` + `run_bgnbd_study.py`. Confirmed (10 seeds):
    Pareto/NBD and BG/NBD are essentially interchangeable — CRPS within 0.5% everywhere, calibration
    close, and both equally broken on misspecified/dense data. The variant barely matters because
    they share the Poisson-count assumption; extends "estimation method immaterial" to "model
    variant immaterial" within the family. (MBG/NBD, BG/CNBD-k left as further variants.)**]**
11. **Rigor items** — bootstrap/Lilliefors correction for the estimated-parameter PIT-KS null;
    log-score across the full grid. **[DONE (bootstrap null):** `run_pit_bootstrap.py`. The naive
    1.36/√n critical value is ~10% too small (CDNow 0.028→0.031 corrected) — the Lilliefors effect;
    CDNow's mild departure survives the correction (still detectable), Grocery is calibrated. Honest
    significance for the empirical PIT claim. (Log-score across the full grid still pending; it is in
    `logscore_check.py` for representative datasets.)**]**
12. **Engineering maturity** — GitHub Actions CI, importable `import paretonbd` library API,
    one-command `make reproduce`, property-based + oracle tests, `CITATION.cff`, PyPI/Zenodo.
    **[WIP:** CI (`.github/workflows/ci.yml`), `CITATION.cff`, and `Makefile` (`make
    reproduce`/test/lint/docs/paper) done; pyproject `[dev]`+`[ml]` extras. Remaining:
    importable `import paretonbd` API, property/oracle tests, PyPI/Zenodo.**]**

---

## Reproducibility notes
- Public data: CDNow & Grocery (R `BTYDplus`: `cdnow`, `groceryElog`). Gusto &
  Homeshopping are proprietary — not needed; our sim + CDNow suffice.
- Python estimation options: `pymc-marketing` (Bayesian Pareto/NBD, individual-level
  posteriors — the modern, maintained successor to `lifetimes`), `lifetimes`
  (`ParetoNBDFitter`, MLE, unmaintained), or hand-rolled MLE (closed-form likelihood).
- Scoring: implement sample-CRPS in numpy (no dep) or use `properscoring`/`scoringrules`.
