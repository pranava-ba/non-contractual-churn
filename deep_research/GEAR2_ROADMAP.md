---
title: "GEAR 2 — Prescriptive / Causal-ML Roadmap"
type: roadmap
status: DRAFT for author review — nothing built yet; this doc gates implementation
created: 2026-09-20
role: The detailed plan for Gear 2. Gear 1 = the descriptive→predictive work (Phase 1 MCMC
      calibration paper + Phase 2 statistical-vs-ML benchmark, both done). Gear 2 = the
      prescriptive shift: causal ML that turns calibrated forecasts into retention decisions.
---

# 🚗 Gear 2 — From Forecasting to Intervention

**One line.** Gear 1 taught us to *predict* silent churn and *how confident to be*. Gear 2 asks
the next question the papers explicitly leave open: **given a customer's state, what does a
retention action actually *do*, and whom should we act on?** That is a *causal* question, and it
is what turns a forecasting model into a tool.

> **Legend:** ✅ done · 🔄 in progress · ⬜ to do · 🟡 needs your decision · 🤖 I can do · 🧑 you ·
> ⭐ headline / novelty-bearing · 🧪 test

---

## 0. Why causal ML, and why it fits *this* project

**The gap.** Every BTYD output — `P(alive)`, `E[x*]`, residual CLV, Top-A% — is an *observational*
prediction: what happens **under the status quo**. None of them says what a retention offer, a
re-engagement email, or a discount would *change*. A firm that acts on churn risk targets:

| Customer type | Churn risk | Uplift (what actually matters) | Propensity model does… |
|---|---|---|---|
| **Persuadable** | high | **high +** — action saves them | targets ✅ (right, by luck) |
| **Lost cause** | high | ~0 — churns regardless | targets ❌ (wasted budget) |
| **Sure thing** | low | ~0 — stays regardless | skips ✅ |
| **Sleeping dog** | low/mixed | **negative** — action *annoys* them | may target ❌ (backfire) |

A churn-propensity (or predicted-value) model ranks the **first column**; the decision-relevant
quantity is the **second**. That second column is the **conditional average treatment effect
(CATE / uplift)** τ(x) = E[Y(1) − Y(0) | X = x]. Causal ML estimates it. This is the precise sense
in which Gear 2 *remedies* the problem instead of merely diagnosing it.

**Why this project is unusually well-placed:**

1. **We own a validated generative model** (`src/simulate.py`: Pareto/NBD with per-customer latent
   λ, μ, τ; `src/simulate_misspec.py` for departures; Pareto/GGG for timing). So we can inject a
   **known** treatment effect and read off **ground-truth CATE** — which *no* real dataset gives.
2. **We own a calibration methodology** (`src/score.py` CRPS/PIT/coverage; `src/conformal.py`
   recalibration; `src/churn.py` Brier/ECE/reliability). Gear 1's thesis was *"are the forecasts
   calibrated?"* Gear 2's differentiator is ⭐ **"are the *treatment-effect estimates*
   calibrated?"** — calibrated *decisions*, not just calibrated *forecasts*. Almost no uplift paper
   asks this.
3. **We own a profit-evaluation harness** (`src/run_profit_study.py`: margin M, contact cost c,
   break-even `M·E[x*] − c`, oracle-profit share, Top-A%). Gear 2 is a **drop-in contrast** on the
   same harness: **uplift targeting `M·τ̂ᵢ − c` vs value targeting `M·Ê[x*ᵢ] − c`**. If uplift wins
   on realised profit, that is the whole managerial argument in one table.

**Thesis continuity.** Gear 1 = *"structural vs distribution-free, judged by calibration."*
Gear 2 = *"structural (model-based) vs black-box causal ML, judged by calibrated targeting value."*
Same spine, new axis.

---

## 1. The modelling choices (🟡 = your call — see §7)

### 1a. How the intervention enters the DGP (Stage-A simulator)
The treatment `T ∈ {0,1}` perturbs a **latent parameter**, and because we know each customer's
latents we can simulate **both potential outcomes** Y(0), Y(1) → ground-truth τᵢ.

- **(i) Shift the dropout rate μ** — treated customers drop out slower: μᵢ → μᵢ·(1−δ), δ ∈ (0,1).
  *This is the natural "retention" story* (you keep them alive longer). **Recommended default.**
- **(ii) Shift the purchase rate λ** — treated buy more often while alive: λᵢ → λᵢ·(1+γ).
  (an "upsell/engagement" story).
- **(iii) Both** — a realistic campaign shifts both.
- **Effect heterogeneity:** δ can be constant (homogeneous ATE), a function of the latents/RFM
  (heterogeneous — the interesting case for uplift), or even **negative for a sub-segment**
  (manufactured "sleeping dogs", to prove uplift beats propensity).

### 1b. Assignment mechanism (this is the identification knob 🧪)
- **Randomized** T ⟂ (λ,μ): the clean start; every estimator should work; validates the pipeline.
- **Confounded** P(T=1 | X) depends on state (e.g. firms over-target high-value or high-risk
  customers): now naïve differences are biased and *causal* methods must earn their keep.
- **Overlap / positivity** stress: make some strata almost-always/never treated.

### 1c. Outcome Y (🟡 pick primary; report others as robustness)
- **Residual CLV over horizon h** (money) — `src/clv.py` Gamma-Gamma × future purchases. *Most
  managerially meaningful; recommended primary.*
- **Retention / active at t+h** — binary `P(x* > 0)` (`src/churn.py`). Cleanest, matches "churn".
- **Incremental future purchases** `E[x*]` (count) — closest to the existing profit harness.

### 1d. Context / features X
BTYD **posterior state** (P̂(alive), Ê[x*], residual-value posterior mean/sd) **+ RFM**
(`ml_benchmark.rfm_features`). ⭐ A key ablation: **does the BTYD state beat raw RFM as the
covariate set for the causal model?** (Gear-1-style "structure helps" question.)

---

## 2. The staged ladder (A → B → C, one by one)

### Stage A — Semi-synthetic (the core; ground-truth CATE) ⭐
The methodological heart. Everything is checkable against truth here.

| # | Status | Who | Task |
|---|:--:|:--:|---|
| A0 | ✅ | 🤖 | **Env:** econml 0.17.0 + causalml 0.17.0 installed & smoke-tested on Py 3.13 (§6); lightgbm/xgboost/shap came along. Pinned in `pyproject.toml` under a new `causal` extra (2026-09-21). |
| A1 | ⬜ | 🤖 | **Intervention DGP:** extend `simulate.py` (new `simulate_intervention.py`) — assign T, perturb μ/λ, emit `y0`, `y1`, `tau_true_cate`, plus the observed factual `y_obs`. |
| A2 | ⬜ | 🤖 | **Feature builder:** assemble X = BTYD posterior state + RFM on the calibration window. |
| A3 | ⬜ | 🤖 | **Estimators v0:** S-, T-learner on sklearn base learners (no new deps) — the floor. |
| A4 | ⬜ | 🤖 | **Estimators v1:** X-, DR-, R-learner; causal forest / DML (econml); uplift tree/forest + meta-learners (causalml). |
| A5 | ⬜ | 🤖 | ⭐ **Structural CATE:** plug shifted-μ into the BTYD closed-form E[value] → a *model-based* uplift, the causal analogue of Gear 1's structural forecaster. |
| A6 | ⬜ | 🤖 | ⭐ **Calibrated intervals:** conformal ITE (Lei & Candès 2021) via `conformal.py`; score coverage/PIT of τ̂ intervals vs true τ. |
| A7 | ⬜ | 🤖 | **Policy + profit:** wire `M·τ̂ − c` targeting into `run_profit_study.py`; budget-constrained targeting; oracle-share. |
| A8 | ⬜ | 🤖 | **Evaluation battery:** the §4 tests (PEHE, Qini, calibration, robustness), multi-seed like Gear 1. |
| A9 | ✅ | 🤖 | Saved `results/gear2_*_summary.csv`; figures in `results/figures_gear2/` (`make_gear2_figures.py`); `tests/test_gear2.py` (12 tests, fast/deterministic, covers the DGP, both novelty estimators, the pure metric functions, and the Dunnhumby DR estimator; heavier econml/causalml fit is smoke-tested if the `causal` extra is installed). 2026-09-21. |

**Gate A→B:** causal estimators recover the known τ with (a) low PEHE, (b) calibrated intervals,
(c) an uplift policy that beats propensity/value/random on realised profit.

### Stage B — Real uplift datasets (external validity)
No ground-truth τ, so evaluate by **randomized-holdout Qini / uplift@k + doubly-robust policy
value**. Fit the BTYD layer where the log structure allows; else use RFM/state and note it.

| Dataset | Treatment | Status |
|---|---|---|
| **Dunnhumby (Complete Journey, already on disk)** | observational campaign/coupon exposure | ✅ **Done** — `run_uplift_dunnhumby.py`, doubly-robust policy value; uplift beats value ~4x. |
| **Hillstrom / MineThatData** | randomized email (mens/womens/none) | ✅ **Done** — `run_uplift_hillstrom.py` via `scikit-uplift`; uplift beats value ~2x on Qini AUC. |
| **X5 / RetailHero** | randomized SMS | ✅ **Done (2026-09-21).** Author supplied `retailhero-uplift.zip` directly (login-walled at source; `sklift.fetch_x5` confirmed hanging on the login redirect). 200,039 clients, `python src/run_uplift_x5.py` ran clean with zero script changes → `results/gear2_x5_summary.csv`. **Sharpest of the three real-data confirmations**: predicted-value targeting's Qini AUC is negative on every one of 3 seeds (worse than random); every uplift estimator positive (0.0096–0.0109). See `GEAR2_STAGE_A_RESULTS.md §4.3`. |
| **Criteo-Uplift** | randomized ad exposure | ⬜ not started; 25M rows, huge; visit/conversion outcomes. |
| **Lenta / Starbucks (rewards)** | promo | ⬜ not started; secondary. |

**Status: Stage B is COMPLETE (2026-09-21) — all three targeted real datasets done.** All three
reproduce the synthetic ordering **uplift > value > random** (see
[GEAR2_STAGE_A_RESULTS.md §4](GEAR2_STAGE_A_RESULTS.md)), X5 most sharply (value-targeting is
negative — worse than random — on every seed). Criteo/Lenta remain optional breadth, not required
for the gate below.

**Gate B→C:** learned policy beats churn-targeting and random on real experiments — **met**, on
all three real datasets.

### Stage C — Real deployment / partner (the remedy in the wild) 🧑
Quasi-experiment or a live pilot with a partner firm. Needs data sourcing (a you-decision, like
the F8 India dataset). Most naturally the **capstone / future-work** in the paper, not a blocker.

---

## 3. Idea catalogue — everything implementable

**Estimators**
1. Meta-learners: **S / T / X / DR / R-learner** (base = GBM/RF; reuse `ml_benchmark` learners).
2. **Causal forest / GRF** (econml `CausalForestDML`).
3. **Double ML** (econml `LinearDML`, `SparseLinearDML`, `CausalForestDML`, `DRLearner`).
4. **Uplift trees/forests** + meta-learners (causalml).
5. ⭐ **BTYD-structural uplift** — analytic CATE from the generative model itself.
6. ⭐ **econml vs causalml cross-check** (your explicit ask) — same inputs, compare CATE ranking,
   policy value, calibration; document *where and why* they diverge (default hyper-params,
   cross-fitting, honest splitting). See §5.
7. **Ensemble / stacking** of learners; a "conformalized causal ensemble".

**Uncertainty & calibration** (the ⭐ differentiator)
8. Conformal ITE intervals; jackknife+ / CV+ for τ̂.
9. Calibration-of-uplift diagnostics: coverage & PIT of τ̂ vs true τ (synthetic); reliability of
   the *ranking* on real data.
10. Bootstrap/posterior CATE intervals from the BTYD-structural route → compare sharpness vs ML.

**Policy & decision layer**
11. Threshold policy `M·τ̂ − c > 0`; **budget-constrained** top-k by τ̂.
12. **Policy trees** (econml `PolicyTree` / `DRPolicyTree`) — interpretable targeting rules.
13. Cost-sensitive / heterogeneous-cost targeting; multi-treatment (which offer, not just whether).
14. Fairness/segment audit of who the policy targets.

**Robustness & identification**
15. Confounded assignment; **unobserved-confounder sensitivity** (Rosenbaum-style / econml sensitivity).
16. Overlap/positivity stress; propensity trimming.
17. Effect-size sweep (small→large δ); **sleeping-dogs** (negative-uplift segment) recovery.
18. Misspecified DGP (`simulate_misspec.py`) — does causal ML degrade gracefully, does structural break?

**Baselines to beat**
19. Random, treat-all, treat-none, **churn-propensity targeting** (`churn.py`), **predicted-value
    targeting** (existing `run_profit_study.py`). These are the strawmen the uplift policy must beat.

**Tool / package**
20. `paretonbd` prescriptive module: `estimate_uplift(df, treatment, outcome, method=…)`,
    `target_policy(uplift, margin, cost, budget)`, `qini_curve`, `policy_value`.

---

## 4. Test catalogue — what we can measure 🧪

**CATE recovery (synthetic only — needs truth)**
- **PEHE** = √mean((τ̂ − τ)²); bias; **Spearman rank-corr(τ̂, τ)** (targeting only needs the ranking).
- Per-stratum error (do we get the *heterogeneity*, not just the ATE?).

**Calibration of the treatment effect** ⭐
- Coverage & PIT of τ̂ intervals vs true τ (synthetic); interval width / sharpness.
- Reliability of predicted vs realised uplift by decile (real & synthetic).

**Policy value**
- **Qini coefficient** & Qini curve; **uplift@k**; AUUC.
- **Realised profit** and **% of oracle profit** on `run_profit_study.py` — uplift vs value vs
  propensity vs random. The headline table.
- Off-policy value via **IPW & doubly-robust** estimators (for real data without full truth).
- Paired significance tests + **FDR control** (reuse `tost.py` / Gear-1 stats harness).

**Sensitivity / stress**
- vs **effect size** δ; vs **confounding strength**; vs **overlap**; vs **N**; vs **heterogeneity
  level**; vs **outcome** (CLV / retention / count); vs **DGP misspecification**.

**Library agreement (your ask)** 🧪
- econml vs causalml: agreement in τ̂ ranking (Spearman), in chosen targets (Jaccard of top-k),
  in policy value; a short **"do they agree?"** verdict with the reasons for any gap.

**Structural vs black-box** ⭐
- BTYD-structural uplift vs causal ML **when the DGP is BTYD** (structural should win — the
  "correctly-specified oracle") **vs under misspecification** (ML should catch up). Direct echo of
  Gear 1's structural-vs-distribution-free result.

**Ablations**
- Feature set: BTYD posterior state vs raw RFM. Base learner: GBM vs RF vs linear. Horizon h.

---

## 5. On running econml *and* causalml (is it a good idea?)

**Yes — but as a deliberate cross-check, not redundancy.** The value:
- They implement **overlapping but not identical** method sets (econml leans DML/orthogonal-ML +
  causal forests + policy trees; causalml leans uplift trees/forests + its own meta-learner API).
  Running both **de-risks a library-specific bug or default** and lets us report the *most
  appropriate* estimator from each family.
- A documented **agreement/divergence analysis** is itself a small contribution (practitioners want
  to know if the tooling choice matters — mirrors Gear 1's "estimator doesn't matter" finding).
- **Risk:** double the API surface and dep weight; different conventions (propensity handling,
  cross-fitting, honest splits) can make naïve comparisons unfair. **Mitigation:** compare on
  identical X, T, Y, base learners, and folds; document each library's defaults explicitly.

**Empirical verdict (from the §6 smoke test, 2026-09-20):** both install and run on Py 3.13, and on
a matched base learner they agree *exactly* (rank-corr 1.000, identical top-20% targets). The
differences came entirely from the **estimator** (econml's causal-forest DML beat the shared
meta-learners by ~3× on PEHE), not the library. **So: yes, run both — but for estimator coverage
(econml → DML / causal forest / policy trees; causalml → uplift trees/forests), not because we
expect the libraries to disagree.** No sklearn fallback is needed.

---

## 6. ✅ RESOLVED: environment & econml-vs-causalml smoke test (2026-09-20)

*(Python 3.13.5 on Windows.)*

- **econml 0.17.0** — installed clean (prebuilt cp313 wheel). ✅
- **causalml 0.17.0** — installed clean (compiled from source on 3.13, wheel built OK). ✅
- **Bonus deps pulled in:** lightgbm 4.7.0, xgboost 3.4.1, shap 0.52 — Gear 1 had noted
  lightgbm/xgboost *missing*; they are now available for the ML base learners too.
- **Smoke test** (both libraries, one toy DGP, n=3000, randomized T, known heterogeneous
  τ(x)=1+X₀ with a negative "sleeping-dog" region), CATE-recovery vs ground truth:

  | Estimator | Library | PEHE | rank-corr w/ true τ |
  |---|---|---:|---:|
  | Causal Forest DML | econml | **0.216** | **0.982** |
  | X-learner | econml | 0.452 | 0.905 |
  | X-learner (BaseXRegressor) | causalml | 0.452 | 0.906 |
  | T-learner | econml | 0.733 | 0.792 |
  | T-learner (BaseTRegressor) | causalml | 0.733 | 0.792 |

  **Cross-library agreement (matched base learner, T-learner):** Spearman **1.000**, Pearson
  **1.000**, top-20% target overlap (Jaccard) **1.000**.

- **Verdict → §5.** The two libraries **agree exactly when matched**; the lever is the *estimator*
  (causal forest ≫ meta-learners: PEHE 0.22 vs 0.73), not the tooling. So no build fallback needed;
  running both is worthwhile for **estimator coverage**, not because they disagree.

---

## 7. ✅ RESOLVED — decisions (2026-09-20)

Rather than pick single levels for options 1–4, the user asked to **test the combinations** ("if that
is a good idea"). Verdict: a **smart factorial** — yes; a blind full Cartesian product — no (it explodes
and most cells only re-confirm the base case). The resolution:

1. **Intervention target** → **test both** μ-only and μ+λ (a DGP factor). λ-only dropped as least
   managerially central.
2. **Primary outcome** → **all three, computed jointly** off each simulation (CLV primary, retention,
   count) — they are three *views* of the same simulated customers, not separate DGPs, so no extra cost.
3. **Effect realism** → **sweep δ** ∈ {0.2, 0.35, 0.5, 0.65} and **test all three effect structures**
   {homogeneous, heterogeneous, sleeping-dogs}. Sleeping-dogs **in** (it's the sharpest uplift-beats-
   propensity argument; the DGP now yields a visible ~19% negative-CATE segment).
4. **Assignment** (promoted to an explicit factor) → **test both** randomized and confounded.
5. **Library set** → **run both econml + causalml on every task, tabulate features/performance per
   task, pick the better per task** (a per-task bake-off, not a single winner).
6. **Venue** → **deferred to the very end** (user: "let the venue be the last check").

## 7.0b ✅ RESOLVED — post-engineering-debt next steps (2026-09-21)

With Stage A/B complete, the engineering debt closed (deps pinned, `tests/test_gear2.py`, figures,
`docs/uplift.md`), and the `mu1`/`lam1` clip-floor DGP bug fixed (§7.0a below), the user chose the
next-steps order explicitly — **recorded here so it isn't lost**:

1. ✅ **Build the `paretonbd` prescriptive module** (§3 item 20) — **done 2026-09-21**:
   `src/prescriptive.py` (`estimate_uplift`, `target_policy`, `fit_dr_nuisances`/
   `dr_policy_value`, `oracle_policy_value`, `qini_auc`/`qini_curve`, plus re-exports of
   `structural_btyd_cate`/`conformal_ite`), consolidating the already-built/tested estimator and
   metric code (`uplift_estimators_ext.py`, `run_uplift_study.py`, `run_uplift_dunnhumby.py`)
   behind a stable, tested (8 new tests in `tests/test_gear2.py`, 17/17 Gear 2 tests passing),
   documented (`docs/api_reference.md`, `docs/uplift.md`) importable API. **Not deferred to the
   end** the way Gear 1's package API was — the user made an explicit call to do this before the
   paper.
2. ✅ **Full first-pass draft of the Gear 2 paper complete** (§8 deliverables), 2026-09-21 —
   `paper_gear2/outline.md`, `methods.md`, `results.md`, `introduction.md` (incl. Related Work,
   with the novelty re-sweep's lead-comparator differentiation folded in), `discussion.md` (incl.
   Conclusion), `abstract.md` (written last, per the draft order). All numbers sourced to
   `GEAR2_STAGE_A_RESULTS.md`/the CSVs, cross-checked against source data before being asserted in
   prose (not asserted from memory). **LaTeX'd the same day**: `paper_gear2/manuscript_gear2.tex`
   (Springer sn-jnl, 17-entry `refs_gear2.bib` every entry verified against a primary source,
   compiles clean via `latexmk -pdf`). **X5 landed the same day too** — the author supplied the
   competition data directly; ran clean with zero script changes; the sharpest of the three
   real-data confirmations (predicted-value targeting negative on every seed, worse than random —
   see §4.3 in `GEAR2_STAGE_A_RESULTS.md`). All markdown + the .tex updated, 0 PLACEHOLDER markers
   remain, 21-page PDF compiles clean, 61/61 tests pass. **Remaining before this is
   submission-ready:** a cover-to-cover consistency pass, an abbreviations/disclaimer appendix, a
   submission-day novelty re-sweep, and then — last, per §7 item 6 — the venue decision.

### 7.0a ✅ RESOLVED — `simulate_intervention.py` clip-floor bug, fixed (2026-09-21)
`mu1`/`lam1` were floor-clipped at an absolute `1e-4`; for the rare customer whose drawn `mu0` (or
`lam0`) was already below that floor (the Gamma heterogeneity has a heavy tail down to ~1e-7), the
clip could invert the treatment's direction for that customer specifically. Fixed by flooring at a
genuine underflow guard (`1e-9`, never binds given `eff` is already clipped to (-0.95, 0.95)
upstream) instead of an absolute floor that could exceed the intended shifted value. Regression
tests added (`tests/test_gear2.py`): a strict zero-negative-CATE invariant for the homogeneous
case, and an explicit sweep across 8 seeds confirming customers with `mu0 < 1e-4` (the old floor)
no longer get an inverted-direction CATE. **Post-fix spot-check confirmed (2026-09-21):** re-ran
the same delta=0.5/5-seed/12-family subset the published aggregates are drawn from (60 cells, 660
rows, 331s, not overwriting `results/gear2_uplift_summary.csv`) and compared against it head to
head. Differences are noise-level (e.g. `econml_CausalForest` overall policy_pct -3.17 → -2.47,
`structural_BTYD` -0.69 → -1.05, `base_value` -17.98 → -17.66) and every headline ordering is
unchanged: causal methods still best, value-targeting still catastrophic under sleeping dogs
(-54.97 vs. the original -55.92), uplift > value > random throughout. **No re-run of the
published factorial was needed; `GEAR2_STAGE_A_RESULTS.md` stands as-is.**

### 7.1 The Stage-A experiment matrix  ⭐ (the "smart factorial")

**Full-cross the 3 axes that change the right answer** (small, interpretable):
`target {μ, μ+λ}` × `structure {homog, heterog, sleeping-dogs}` × `assignment {rand, confound}`
= **12 DGP families**.

**Sweep as robustness lines** (one-factor-at-a-time, not fully crossed): `δ ∈ {0.2,0.35,0.5,0.65}`,
cohort `N`, heterogeneity level. **Outcomes**: computed jointly (3 per run, no extra sims).

**Cross every DGP family with every estimator:** S/T/X/R/DR-learner, CausalForestDML, uplift-RF,
⭐ BTYD-structural CATE, + baselines (propensity-targeting, value-targeting, random, treat-all/none).
**Each estimator run in both libraries** where both implement it (option 5 bake-off).

**Metrics:** PEHE, rank-corr vs true τ, ⭐ calibration coverage/PIT of τ̂, Qini/AUUC, policy profit
(% of oracle) on `run_profit_study.py`. **Seeds:** 10–15 per cell (Gear-1 discipline).

**The headline interaction to surface:** *estimator × effect-structure* — uplift targeting should beat
propensity/value targeting **most decisively in the sleeping-dogs family**, and match them elsewhere.

Scale: 12 families × ~9 estimators × 15 seeds ≈ 1.6k fits per δ (fast on simulated data); the δ/N/het
sweeps stay OFAT so the grid never blows up. This is systematic **and** legible.

**Status: Stage A COMPLETE ✅ (2026-09-20), Stage B auto-fetchable portion COMPLETE ✅ (2026-09-20),
test/figure/doc/dependency debt closed ✅ (2026-09-21).** DGP `src/simulate_intervention.py`;
harness `src/run_uplift_study.py` (8 estimators × 480-cell factorial); follow-ups
`src/run_uplift_extras.py` (high-tree coverage + regret, feature ablation); new estimators
`src/uplift_estimators_ext.py` (structural BTYD-CATE + conformal-ITE); real-data validation
`src/run_uplift_dunnhumby.py` + `src/run_uplift_hillstrom.py`; figures `src/make_gear2_figures.py`
→ `results/figures_gear2/`; tests `tests/test_gear2.py` (12 passing); deps pinned in
`pyproject.toml[causal]`; narrative doc `docs/uplift.md`. Full results + interpretation in
[GEAR2_STAGE_A_RESULTS.md](GEAR2_STAGE_A_RESULTS.md). Headline: prediction≠decision (value-targeting
−58× oracle under sleeping dogs); three-tool regime map; causal-forest intervals genuinely
overconfident (0.80 @1200 trees), conformal-ITE repairs (0.96); both real datasets confirm
uplift > value > random. **Next (all 🧑/paper-scale, not bounded engineering):** X5/RetailHero
manual download (optional breadth), the `paretonbd` prescriptive module (§3 item 20), and drafting
the Gear 2 paper itself (§8) — none of these are "left to do" in the small-task sense; see §9.

---

## 8. Deliverables

- **Paper (paper-led):** *"From forecasting to intervention: calibrated causal targeting on the
  buy-till-you-die state."* Spine: predict→prescribe gap → μ-shift intervention model → causal
  estimators on the BTYD state → calibration-of-CATE + policy evaluation → semi-synthetic results
  (A) → real-data validation (B) → managerial decision rule + tool → discussion / future work (C).
- **Tool:** `paretonbd` prescriptive module (§3 item 20).
- **Evidence:** `results/gear2_*_summary.csv`, figures, `tests/test_gear2.py`.
- **Docs:** a `docs/uplift.md` in the monograph style; CHANGELOG worklog per session.

**Companion research docs (2026-09-20):** [CAUSAL_ML_LITERATURE.md](CAUSAL_ML_LITERATURE.md) (the
causal-ML corpus) · [TOOLING_CAUSAL_ML.md](TOOLING_CAUSAL_ML.md) + [TOOLING_NONCONTRACTUAL.md](TOOLING_NONCONTRACTUAL.md)
(package inventories) · [DATASETS_LOG.md](DATASETS_LOG.md) (dataset hunt, incl. the Dunnhumby treatment
find) · tracker categories `causal_ml_uplift` / `causal_ml_churn`.

## 9. Risks
- **No treatment in real data** → mitigated by the A→B→C ladder (synthetic truth first).
- **Py 3.13 build failures** for econml/causalml → sklearn meta-learner fallback (§6).
- **Unfair library comparison** → identical inputs/folds/base learners (§5).
- **Effect unidentifiable under confounding** → sensitivity analysis, honest about assumptions.
- **Scope creep** — §3 is a menu, not a mandate; §7 decisions prune it to a shippable core.
