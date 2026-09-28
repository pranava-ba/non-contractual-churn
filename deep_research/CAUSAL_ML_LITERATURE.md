---
title: "Causal-ML Literature Pull (Gear 2)"
type: reference
created: 2026-09-20
role: The causal-ML corpus for Gear 2 (prescriptive/uplift), the analogue of LITERATURE_MATRIX.md
      for the non-contractual-churn corpus. Feeds the Gear 2 paper's Related Work and method choice.
      Companion to GEAR2_ROADMAP.md; tooling in TOOLING_CAUSAL_ML.md; datasets in DATASETS_LOG.md.
---

# Causal-ML literature — from prediction to intervention

**Scope.** The literature Gear 2 stands on: estimating **heterogeneous treatment effects (CATE) /
uplift** and turning them into **targeting policies**, with emphasis on the **marketing / churn /
retention** application and on **uncertainty calibration of treatment effects** (our differentiator).
This is a *different* literature from the non-contractual-churn corpus (LITERATURE_MATRIX.md); the two
meet exactly at Gear 2's thesis: *estimate whom a retention action changes, on the BTYD state.*

**How this connects to our work.** BTYD gives the *state* (P(alive), residual value, RFM); causal ML
gives the *effect of acting on that state*. The single most important prior result for our framing is
**Ascarza (2018)**: targeting the highest-**risk** customers is often futile — you must target the
highest-**lift** (uplift) customers. That is the whole motivation for Gear 2 in one citation.

**Legend — Cal?** (does the paper quantify *calibrated uncertainty of the treatment effect*, not just a
point CATE?): ❌ point CATE / ranking only · ⚠️ interval but not calibration-tested · ✅ calibration/
coverage of the effect · 🔬 methodology we *use* · ❓ tbd. **Pri**: 🔴 read fully · 🟡 skim · ⚪ reference.

---

## 1. The motivating marketing / churn line  *(why uplift, not propensity)*

| Paper | Yr | Venue | Role in Gear 2 | Cal? | Pri |
|---|---|---|---|:--:|:--:|
| ⭐ **Ascarza — Retention Futility** | 2018 | J. Marketing Research | **the thesis**: target on *lift*, not *risk*; high-risk targeting is often ineffective; leverages A/B tests for targeting | ❌ | 🔴 |
| ⭐ **Devriendt, Berrevoets & Verbeke — "stop predicting churn, start using uplift"** | 2021 | Information Sciences | frames churn as an uplift, not classification, problem — our exact pivot | ❌ | 🔴 |
| **Lemmens & Gupta — Managing Churn to Maximize Profits** | 2020 | Marketing Science | profit-based (not accuracy-based) churn targeting; loss function that ranks by profit | ❌ | 🔴 |
| **Devriendt, Moldovan & Verbeke — survey + experimental eval of uplift** | 2018 | Big Data | *"a stepping stone toward prescriptive analytics"* — the field map + baselines | ❌ | 🔴 |
| **Verbeke, Olaya et al. — cost-sensitive causal / value-driven uplift** | 2021–23 | DSS / EJOR | targeting under margin M & cost c — maps onto our profit harness `M·τ̂−c` | ❌ | 🟡 |
| **Fernández-Loría & Provost — causal decision-making ≠ effect estimation** | 2022 | INFORMS J. Data Sci. | *ranking* for decisions can beat *accurate* CATE — shapes how we evaluate | ❌ | 🟡 |
| **Hitsch, Misra & Zhang — HTE & optimal targeting policy evaluation** | 2024 | Quant. Marketing & Econ. | policy-value evaluation of targeting rules on field data | ❌ | 🟡 |
| Uplift for B2B customer churn | 2021 | Industrial Marketing Mgmt | domain application; churn-specific | ❌ | ⚪ |
| Ascarza et al. — *In pursuit of enhanced CLV* / retention reviews | 2017–18 | J. Svc Res / CLV | positions retention interventions in the CLV frame | ❌ | ⚪ |

> These are the papers that make Gear 2 a *marketing-science* contribution, not just an ML exercise.
> The through-line: a churn/CLV *forecast* is not a *decision*; the decision needs the treatment effect.

---

## 2. CATE / uplift estimators  *(the methods we will run)*

| Method | Paper | Yr | What it is | In tooling |
|---|---|---|---|---|
| **S/T/X-learner** | Künzel, Sekhon, Bickel & Yu | 2019 (PNAS) | meta-learners over any base regressor; X-learner strong under treatment imbalance | econml, causalml, sklift |
| **R-learner** | Nie & Wager | 2021 (Biometrika) | Robinson-residual objective; "quasi-oracle" | econml, causalml |
| **DR-learner** | Kennedy | 2023 (EJS) | doubly-robust pseudo-outcome regression | econml (DRLearner) |
| **Causal forest** | Wager & Athey | 2018 (JASA) | honest RF for CATE with pointwise CIs | econml, grf (R) |
| **Generalized random forests** | Athey, Tibshirani & Wager | 2019 (Ann. Stat.) | GRF umbrella; local moment forests | econml, grf |
| **Double/debiased ML (DML)** | Chernozhukov et al. | 2018 (Econ. J.) | Neyman-orthogonal, cross-fit nuisance | econml (LinearDML, CausalForestDML), DoubleML |
| **Uplift trees/forests** | Rzepakowski & Jaroszewicz | 2012 (KAIS) | splits on distributional divergence of the treatment response | causalml, sklift |
| **BART / Bayesian causal forest** | Hill 2011; Hahn, Murray & Carvalho 2020 | | Bayesian CATE with posterior intervals (natural fit for our calibration lens) | bartMachine, pymc |
| **TARNet / CFR (deep)** | Shalit, Johansson & Sontag | 2017 (ICML) | representation-balancing neural CATE | (optional; torch) |

⭐ **BTYD-structural CATE (ours).** Because our DGP is a validated Pareto/NBD, we can compute a
*model-based* uplift by plugging the shifted μ into the BTYD expected-value formula — the causal
analogue of Gear 1's "structural vs distribution-free" contrast. No external paper does this; it is a
Gear 2 novelty candidate.

---

## 3. Policy learning & evaluation  *(turning τ̂ into a decision, and scoring it)*

| Topic | Paper | Yr | Use in Gear 2 |
|---|---|---|---|
| **Qini / uplift curve** | Radcliffe 2007; Radcliffe & Surry 2011 | | headline targeting metric; economic reading (gain vs campaign size) |
| **RATE (rank-weighted ATE)** | Yadlowsky, Fleming, Shah, Brunskill & Wager | 2025 (JASA) | tests whether a *prioritization rule* beats random — evaluates our policy |
| **Policy learning (observational)** | Athey & Wager | 2021 (Econometrica) | learn a targeting policy with regret guarantees |
| **Empirical welfare maximization** | Kitagawa & Tetenov | 2018 (Econometrica) | budget-constrained targeting rule |
| **Off-policy value: IPW / doubly-robust** | Dudík, Langford & Li 2011; Dudík et al. 2014 | | value of our policy on real data without full ground truth |
| **Uplift eval pitfalls / benchmarks** | Bokelmann & Lessmann 2023; Rößler & Schoder 2022; UpliftBench 2026 | | how uplift metrics disagree → we report several, not one |
| **Cost-sensitive causal classification** | Verbeke, Olaya et al. | 2020–21 | break-even `τ̂ > c/M` targeting; our profit harness |

---

## 4. Uncertainty / calibration of treatment effects  ⭐ *(our differentiator)*

Gear 1 asked "are the *forecasts* calibrated?"; Gear 2 asks "are the *treatment-effect estimates*
calibrated?" This sub-literature is young and citable — and almost no *uplift* paper tests it.

| Paper | Yr | Venue | What it gives us |
|---|---|---|---|
| **Lei & Candès — conformal inference of counterfactuals & ITE** | 2021 | JRSS-B | the foundation: valid ITE prediction intervals |
| **Alaa, Ahmad & van der Laan — conformal meta-learners for ITE** | 2023 | ICML/NeurIPS | conformal intervals *around meta-learner CATE* — plugs into `conformal.py` |
| **Systematic review of conformal inference for treatment effects** | 2025 | arXiv 2509.21660 | the survey to cite for the calibration-of-effects framing |
| **Conformal ITE via conditional density** | 2025 | AAAI | narrower valid intervals |
| **Sensitivity analysis of ITE (robust conformal)** | 2023 | — | coverage under unobserved confounding — our robustness section |
| Wager & Athey pointwise CIs; Bayesian-causal-forest posteriors | 2018/2020 | | model-based effect intervals to compare against conformal |

**Claimable Gear 2 contribution:** bring PIT / coverage / CRPS (our Gear 1 machinery) to *τ̂ intervals*
against **ground-truth τ** from the simulator — a calibration benchmark of causal estimators that the
uplift literature has not done.

---

## 5. Reading path (suggested order)

1. **Ascarza (2018)** — why lift beats risk (the motivation).
2. **Devriendt et al. (2021, Info Sci)** — churn-as-uplift (the pivot).
3. **Devriendt et al. (2018, Big Data)** — the field survey + baselines + Qini.
4. **Künzel et al. (2019)** + **Nie & Wager (2021)** + **Wager & Athey (2018)** — the estimators.
5. **Chernozhukov et al. (2018)** — DML orthogonality (why cross-fitting).
6. **Athey & Wager (2021)** + **Yadlowsky et al. (2025, RATE)** — policy learning & evaluation.
7. **Lei & Candès (2021)** + **Alaa et al. (2023)** — calibrated effect intervals (our angle).
8. **Lemmens & Gupta (2020)** + **Verbeke/Olaya** — profit-driven targeting (our harness).

---

## 6. Novelty position for the Gear 2 paper — RE-CONFIRMED (was provisional)

- Uplift/HTE methods are mature; applying them to churn/retention is **not** new (Ascarza; Devriendt).
- **What is open / ours:** (a) uplift **on the BTYD latent state** with a **structural (model-based)
  CATE** baseline; (b) a **calibration benchmark of the treatment-effect estimates** against
  simulator ground truth (nobody scores uplift *calibration*); (c) the **same profit harness**
  contrasting uplift vs value vs propensity targeting on genuinely non-contractual transaction logs.
- **Re-confirmed 2026-09-21** via a bounded 11-search deep dive:
  `deep_research/GEAR2_NOVELTY_RESWEEP.md`. Verdict: **holds.** One closely-adjacent paper found
  (a structural-Bayesian CLV-under-endogenous-marketing paper covering Pareto/NBD + BG/NBD +
  heterogeneous effects) requires an explicit differentiation paragraph in Related Work but does
  not do calibration-of-effects, a ground-truth recovery test, an estimator bake-off, or real-data
  DR/Qini validation. ~6 further methodologically-relevant papers (CATE calibration lineage,
  causal survival forests, survival off-policy evaluation, a concurrent KDD 2026 structural-bias
  evaluation paper) are must-cites, not threats. This is no longer "verify against the tracker" —
  it's a completed, logged sweep; re-run only if a `causal_ml_uplift`-tagged paper later surfaces
  that specifically combines BTYD + calibration.

*Sources for this pull are logged in the session CHANGELOG (2026-09-20) and the tracker. Re-sweep
sources logged in `GEAR2_NOVELTY_RESWEEP.md` (2026-09-21).*
