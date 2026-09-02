---
title: "Gap cross-walk — Manzoor et al. (2024) field review vs. our gap analysis"
type: gap-crosswalk
created: 2026-08-10
source: "Manzoor, Qureshi, Kidney & Longo (2024), A Review on Machine Learning Methods for Customer
         Churn Prediction and Recommendations for Business Practitioners, IEEE Access 12 (ARROW@TU
         Dublin, Articles 241). §VI Gap Analysis & Recommendations + Appendix."
companion: "deep_research/pareto_nbd_extension_gap_analysis.md (our 30-gap master table)"
---

# Manzoor et al. (2024) §VI vs. our gap analysis

Manzoor et al. surveyed **212 articles** (185 primary, 2015–Jan 2024, + 27 supportive) and distilled
the field's state into **five critical gaps** with matched recommendations, plus a profit-metric
apparatus (MPC / EMP, Verbraken et al.). It is a **field-level** gap analysis (what the churn-ML
*literature* lacks); ours is a **paper-level** one (what Simon 2025 leaves open). They sit at different
altitudes, which is exactly why the comparison is useful: it tells us whether our specific extension
also answers the field's general complaints.

**Headline verdict:** our project already patches **4 of Manzoor's 5 gaps** (dataset *recency* is the
one partial/open, via F8), and — more tellingly — **fills a gap the review itself did not name:
probability calibration.** Manzoor's own metric gap (their Gap 4) stops at *profit-awareness* and never
reaches *calibration*, which is precisely our central lens. The one place they push harder than we do is
**XAI/explainability of the ML side** (their Gap 5), where we answer from the structural side
(interpretable BTYD + Conformalized BTYD) rather than with SHAP-style tooling.

## The large synced table

| # | Manzoor (2024) §VI gap | Their recommendation | Our gap ID(s) | Our status | Evidence (module / result) | What we can still do |
|---|---|---|---|:--:|---|---|
| **M-G1** | **Datasets old or private** — old ⇒ stale features; private ⇒ non-replicable, no cross-study comparison | Create up-to-date, high-quality, anonymised **public** datasets with governance + documentation | **D4** (done), **F8** (open), D-series | ◑ **mostly patched** (recency partial) | 7 **public** cohorts (CDNow, Grocery, Online Retail II, Olist, Dunnhumby, Ta-Feng + 1 simulated), active rates **1.6%→96%**; all replicable from public data + code. Our §1 already substitutes public sets for Simon's proprietary Gusto/Homeshopping | **F8** — a genuinely Indian / more-recent / non-retail cohort; **foreground reproducibility** (public data + code) as our direct answer to the replicability half of this gap |
| **M-G2** | **No consensus on feature-set** — behavioural vs. feedback vs. network features | Integrate feature-sets: behavioural + demographics + social/communication graphs + customer feedback | **G2** (done), covariate-targets | ✅ **addressed (targeted null)** | Static demographics **and** a time-varying promo covariate both **immaterial over RFM** (counts p=0.38, value p=0.77, churn degenerate). RFM suffices | State **RFM-sufficiency** as our contribution to the debate; **scope out** social/graph/text features in Limitations (we are transaction-only by design) |
| **M-G3** | **No consensus on classifiers** — simple vs. ensembles/DL; models **lack generalisation across domains** | Select classifiers by the **underlying data, size, shape**; prioritise generalizability, dimensionality, over/underfitting, class imbalance | **M1, M2, M3** (done) + BTYD family (G1) | ✅ **exceeded** | GBM variants + ZILN + hazard ML + classifier vs Pareto/NBD, BG/NBD, Pareto/GGG across 7 cohorts; **decision rule**: structure wins sparse/regular, distribution-free ML (QuantileGBM) wins dense/miscalibrated — calibration governed by the count assumption | Frame our **"which model when, by data regime"** rule as the concrete answer their recommendation 3 asks for; it *is* the missing consensus, evidence-backed |
| **M-G4** | **Traditional metrics inadequate** — accuracy/precision/recall/ROC ignore individual **profitability**; not all customers equal | Design techniques with **profit-based metrics** (MPC, EMP) | **U1, U2** (calibration), **V1** (tests), **V2** (profit), **V3** (cost), Top-A% | ✅ **central contribution** | Proper scoring + PIT/CRPS/coverage/ECE replaces point error; **V2 profit layer** (% of oracle, contact-cost sweep, margin M / break-even c/M); cost frontier; Top-A% value-weighting | **Cite the profit-metric lineage** (Verbraken et al. EMP/MPC) + Manzoor for V2 — *currently uncited* in `refs_phase2.bib`; and stress we go **beyond profit metrics to calibration**, which their gap omits (see reverse gap) |
| **M-G5** | **Performance–explainability tradeoff** — ensembles/DL performant but opaque | Adopt **XAI** for interpretation, feature importance, bias, transparency | Conformalized BTYD; interpretability framing | ◑ **addressed structurally, not via XAI** | Our thesis contrasts parsimonious/interpretable BTYD with black-box ML; **Conformalized BTYD** gets ML-competitive calibration **without sacrificing** the closed-form fit or interpretable params | Frame Conformalized BTYD as **resolving** the tradeoff; either **scope out** SHAP-style XAI in Limitations (cite Boukrouh & Azmani 2025) or add a small importance pass as future work |
| **M-R★** | *(reverse gap — Manzoor does **not** name it)* **Probability calibration** | — (their metric gap stops at profit) | **U1, U2, U3** + Conformalized BTYD | ✅ **we fill a gap the review missed** | The whole paper. A 2024 review centred on evaluation metrics flags profit-awareness but never probability calibration | **Use Manzoor's Gap 4 as evidence** the field sees the metric problem but stops short of calibration — strong motivation for our lens; consistent with the `LITERATURE_MATRIX` Calib? tally (Manzoor is a 🔬 tool-review, does not itself calibrate) |

## How it holds up

- **Convergent where it counts.** Four of the five field gaps land squarely on work we have already
  done (D4, G2, M1–M3, U/V-series). The review, written independently and at field scale, validates
  that our specific extension targets the problems the whole literature is complaining about — a good
  external sanity check on scope.
- **We out-reach it on evaluation.** Manzoor's sharpest metric complaint (Gap 4) reaches *profit* but
  not *calibration*. Our lens is therefore novel even against this review's own gap list — the same
  conclusion the Ulrich read produced from the theory side (see [[ulrich-dead-reckoning]]).
- **It out-reaches us on explainability.** Their Gap 5 (XAI) is the one axis where we answer obliquely
  (structural interpretability + Conformalized BTYD) rather than head-on. This is a deliberate scope
  boundary, not an oversight, and should be stated as such.
- **Dataset recency is the shared soft spot.** Their Gap 1 (old/private data) is our F8 — the one open
  experimental item. Our datasets are at least all *public and replicable*, which answers the harder
  half of their complaint.

## What this adds to our next phase

Nothing here reopens experiments; it sharpens the **write-up and citations**:

1. **Add the profit-metric lineage** — `verbraken` (EMP/MPC) + `manzoor2024` to `refs_phase2.bib`;
   cite in the §profit (V2) motivation. Closes the one concrete citation gap this review exposes.
2. **Cite Manzoor (2024) + Imani (2025) as the field surveys** in Related Work, and use Manzoor's Gap 4
   as the springboard for our calibration lens ("the field sees the metric problem, reaches profit,
   stops before calibration").
3. **Add one Limitations paragraph on XAI** (their Gap 5): position structural interpretability +
   Conformalized BTYD as our answer; name SHAP-style attribution on the ML forecasters as future work
   (link Boukrouh & Azmani 2025).
4. **Reinforce F8** (their Gap 1) and foreground our public-data/reproducibility posture as the reply.
5. **Optional framing device:** an Intro/Discussion line that our paper *operationalises 4 of the 5
   recommendations a 2024 field review calls for, and adds the calibration axis the review omits.*

Model to borrow from this paper: its **Conflict-of-Interest / disclaimer** block ("The authors declare
that there is no conflict of interest…") and its **Table 7 abbreviations appendix** — both feed the
"remember to include" checklist in [`writing_inspiration.md`](writing_inspiration.md) §F.

---
*Read scope: only §VI (Gap Analysis & Recommendations) + Appendix of Manzoor et al. (2024), per
request. The rest of the review is unread. Companion to
[`pareto_nbd_extension_gap_analysis.md`](pareto_nbd_extension_gap_analysis.md).*
