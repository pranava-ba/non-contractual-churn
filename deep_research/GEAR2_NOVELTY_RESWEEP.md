---
title: "Gear 2 — Novelty Re-Sweep (bounded, 2026-09-21)"
type: novelty-check
created: 2026-09-21
role: The Gear-2 analogue of Phase 2's pre-submission bounded citation sweep. Re-confirms (or
      corrects) the provisional novelty position in CAUSAL_ML_LITERATURE.md against the live
      literature, ~11 targeted searches, before the paper's Related Work section is written.
status: RESOLVED — novelty claim holds, with one closely-adjacent paper requiring a prominent
        differentiation paragraph (§1) and ~7 methodological must-cites (§2).
---

# Gear 2 novelty re-sweep

## 0. Method

11 targeted web searches (2026-09-21), covering every axis of the claim in
`CAUSAL_ML_LITERATURE.md`'s provisional position: (1) BTYD/Pareto-NBD × causal ML/uplift
generally, (2) CLV × causal forest / treatment effects, (3) conformal prediction × treatment
effects/uplift in marketing, (4) Pareto/NBD × causal inference/intervention specifically, (5) the
single closest hit chased in depth, (6) conformal+causal ROI (a second closest hit), (7) survival
off-policy evaluation (BTYD's censoring structure), (8) semi-synthetic ground-truth uplift
evaluation under structural bias (methodologically closest to our Stage A design), (9) CATE
calibration + causal forest coverage, (10) sleeping dogs / do-not-disturb terminology currency,
(11) Ascarza (2018) follow-up work. Bounded, not exhaustive — the same spirit as the Phase 2
9-paper genealogy sweep, sized to the claim being checked rather than a full corpus rebuild.

## 1. The one closely-adjacent paper — requires a differentiation paragraph

**"Modelling Customer Lifetime Value under Endogenous Marketing Interventions: A Structural
Bayesian Approach"** (*International Journal of Engineering and Management Research*, low-tier
venue, exact year not resolved from search snippets — treat as recent/2025-26). This is the
**closest prior work found** and the only one that combines BTYD models by name (Pareto/NBD,
BG/NBD) with a causal/endogenous-assignment framing and heterogeneous treatment effects:

- Jointly models the purchase process **and** the firm's marketing-assignment process (i.e.,
  treats assignment as *endogenous/confounded* — exactly our `confounded` DGP arm) via a
  structural Bayesian hierarchical model.
- Claims conventional CLV models overstate marketing elasticity by 20-40% under endogenous
  targeting, worse as targeting sophistication rises.
- Recovers heterogeneous treatment effects for segmentation/budget allocation.

**What it does NOT do (confirmed absent from every summary/abstract source returned):**
calibration of the treatment-effect *estimate itself* (no coverage/interval check of any kind);
no ground-truth CATE validation via a controlled simulator injection (it's bias-*correction* on
real/simulated-to-real data, not a validated-oracle recovery test); no comparison across multiple
causal-ML estimator families (it is one structural Bayesian model, not a bake-off); no econml/
causalml library comparison; no real-data doubly-robust/Qini external validation on a named
retail dataset; no conformal repair or calibration↔sharpness framing; no "three-tool regime map."

**Verdict: not a novelty threat to the paper's actual claims, but the single most important
citation in Related Work.** It independently corroborates our confounded-assignment finding
(naive estimates are biased when firms already target on value/risk — our Stage A shows this
directly, `GEAR2_STAGE_A_RESULTS.md` confounded-vs-randomized comparison) from a different
methodological angle (structural Bayesian bias-correction vs. our black-box+structural CATE
bake-off plus calibration). Cite prominently; the paper should explicitly say "our structural
BTYD-CATE estimator (§3.2) is method-of-moments and calibration-of-effects-focused, complementary
to \[this paper\]'s full hierarchical-Bayesian bias-correction approach — the two could be
combined in future work."

## 2. Methodologically relevant, not competing (must-cite, not a threat)

| Paper | What it is | Why it's cited, not a threat |
|---|---|---|
| Xu & Yadlowsky (2022), *Calibration Error for Heterogeneous Treatment Effects*, AISTATS | Defines a calibration-error metric for CATE models, evaluated on Criteo-Uplift | **Predates** our work by years and is general methodology, not BTYD/retail-specific. It's the *origin* of "calibration of CATE" as a checkable property — cite alongside Lei & Candès (2021) as the methodological ancestry of our differentiator, not a competing application. |
| Van der Laan et al., *Causal isotonic calibration for heterogeneous treatment effects* (arXiv 2302.14011) | Isotonic recalibration of CATE estimates | Same family as Gear 1's own `conformal.py` isotonic recalibration, applied to treatment effects instead of forecasts — cite as a recalibration alternative to our split-conformal approach (future-work: compare the two repair methods). |
| *Orthogonal causal calibration* (arXiv 2406.01933, 2024) | Another CATE-calibration method | Same bucket — general methodology, cite as further evidence calibration-of-effects is an active but *general* (not BTYD-applied) sub-literature. |
| Cui, Kosorok, Sverdrup, Wager & Zhu (2023), *causal survival forests*, JRSS-B | HTE estimation for right-censored survival outcomes | BTYD's churn/dropout is structurally a survival/censoring problem; our `CausalForestDML` treats the outcome as a plain count/continuous target, not censored. **A genuine limitation to flag in Discussion**, not a competing paper: future work could swap in a causal survival forest for the churn/retention outcome specifically. |
| Kubota, Takahashi & Saito (2026), *Off-Policy Evaluation and Learning for Survival Outcomes under Censoring* (arXiv 2603.22900) | IPCW-based doubly-robust off-policy value estimators for censored outcomes | Directly relevant to our `dr_policy_value` (§5 of `methods.md`), which does **not** currently handle censoring explicitly. Cite as a stronger DR estimator for a churn/retention outcome specifically — a concrete, named improvement to flag for future work. |
| Ai, Chen, Wang, Shang, Tao & Li (2024), *Improve ROI with Causal Learning and Conformal Prediction*, ICDE | Conformal prediction for ROI-targeting robustness under covariate shift | Confirms conformal+causal-ML is an active applied-marketing direction generally, but targets *covariate-shift robustness* of a point ROI prediction, not *interval calibration* of the CATE itself, and is not CLV/BTYD-specific. Cite as sibling applied work, not overlapping. |
| Yang, Liu & Huang (2026), *Evaluating Uplift Modeling under Structural Biases*, KDD 2026 | Semi-synthetic ground-truth uplift evaluation to isolate structural biases in evaluation *metrics*; finds targeting and prediction are distinct objectives | **Methodologically the closest in spirit to our Stage A design** (semi-synthetic + ground truth to isolate bias) and echoes our "prediction ≠ decision" theme at the level of *metrics*. But it studies **metric robustness** (which evaluation metric ranks estimators consistently under bias), not **estimator/decision performance on a specific domain (BTYD/retail) with calibration of the effect itself**. Different question, same toolkit — cite prominently as a concurrent, complementary KDD 2026 paper, and note the shared "ground-truth semi-synthetic" methodology as independent convergence on the same evaluation gap, not redundancy. |

## 3. Not relevant (checked and ruled out)

General BTYD-ML integration surveys and popularizations (`hackernoon.com`'s "predict everything
except what happens when you act" — a blog post, not a paper, but confirms the *problem framing*
is recognized outside academia too); Xie & Huang-style NN-parameter-estimation-for-Pareto/NBD
papers (already covered by the Phase 2 genealogy sweep — estimation, not causal); general uplift-
modeling surveys/tutorials (Wikipedia, Medium, scikit-uplift docs — background, not novel prior
art); CLV-industry-benchmark blog content (not academic).

## 4. Updated novelty position

**Holds.** No paper found puts the Pareto/NBD-family BTYD state through (a) a causal-ML estimator
bake-off across libraries, (b) a ground-truth CATE validation via controlled simulator injection,
(c) calibration of the *treatment-effect estimate itself* (not just the forecast), and (d) real
retail-transaction external validation (DR + Qini) — as one paper. The one closely-adjacent paper
(§1) attacks the same problem (BTYD + endogenous/causal targeting) from a different angle (single
structural-Bayesian bias correction, no calibration-of-effects, no ground-truth recovery test, no
estimator bake-off) and should be the lead citation in Related Work, differentiated explicitly
rather than merely listed. Two 2026 papers (§2, survival OPE and the KDD structural-bias
evaluation) are close enough in spirit that Related Work should name them and state the
distinction plainly, matching how Phase 2 handled its closest comparators (Xie 2020, Ulrich 2026)
rather than omitting them.

**Action for `paper_gear2/outline.md`'s Related Work section:** lead with the endogenous-CLV paper
(§1) and its explicit differentiation paragraph; cite the calibration-of-CATE lineage (Xu &
Yadlowsky 2022, isotonic/orthogonal calibration) as ancestry for the calibration differentiator;
cite the survival/censoring papers (Cui et al. 2023, Kubota et al. 2026) as a named Discussion-
section limitation/future-work item rather than pretending the outcome isn't censored; cite the
KDD 2026 structural-bias evaluation paper as a complementary concurrent methodology paper.
