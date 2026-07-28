# Pareto/NBD Extension — Research Roadmap

Extending **Simon, L. (2025).** *A generalised comparison of Pareto/NBD based
forecasts using MCMC, maximum likelihood, and heuristics.* Journal of Business
Economics 95:1079–1105. https://doi.org/10.1007/s11573-025-01237-8

Goal: **journal/conference paper**. Stack: **Python**.

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

## Reproducibility notes
- Public data: CDNow & Grocery (R `BTYDplus`: `cdnow`, `groceryElog`). Gusto &
  Homeshopping are proprietary — not needed; our sim + CDNow suffice.
- Python estimation options: `pymc-marketing` (Bayesian Pareto/NBD, individual-level
  posteriors — the modern, maintained successor to `lifetimes`), `lifetimes`
  (`ParetoNBDFitter`, MLE, unmaintained), or hand-rolled MLE (closed-form likelihood).
- Scoring: implement sample-CRPS in numpy (no dep) or use `properscoring`/`scoringrules`.
