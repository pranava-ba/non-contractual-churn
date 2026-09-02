# First-Review Presentation — Build Guide

A slide-by-slide plan for rebuilding `First Review` from scratch. For each slide: **Format**
(layout), **On-slide** (the exact text to type — keep it terse), **Visual** (figure/diagram), and
**Say** (one line to narrate — this is your viva prep). 20 slides, ~10–12 minutes.

---

## 0. Global setup

- **Aspect / size:** keep the college template's **4:3 (10×7.5")** for consistency, or 16:9 if you prefer.
- **Fonts:** one sans family (Calibri or Arial). Title **28 pt bold**, body **16–20 pt**, table text **11–12 pt**. Never below 11 pt.
- **Color theme (pick one and reuse everywhere):** a dark **navy `#1F3764`** for titles/headers + one accent (teal `#2A9D8F` or amber `#E9A13B`). White background. This is the same "uniform theme" you'll later apply to the figures.
- **Every slide:** college header on Slide 1 only; footer "First Review" + slide number + date on all.
- **Bullet discipline:** max ~5 bullets/slide, max ~2 lines each. Put the detail in *speaker notes*, not on the slide.
- **Rubric you're scoring against (50):** Clarity 7 · Problem & Objective 7 · Literature (5+ sources) 7 · Methodology/Planning 7 · **Dataset + Preprocessing + Initial Implementation 15** · Viva 7. The 15-mark item is the biggest — Slides 10–15 must clearly show a working pipeline with results.

---

## 1. Slide-by-slide

### Slide 1 — Title
- **Format:** Title slide. College header band at top (name, "An Autonomous Institution", address, Dept. of CSE (AI & ML)).
- **On-slide:**
  - **Title:** *Non-Contractual Churn: Are Customer-Purchase Forecasts Calibrated?*
  - **Subtitle:** *A Statistical vs. Machine-Learned Benchmark*
  - Student Members: **B. A. Pranava** (Reg. No. ____) · **Vyasa R. Rajeswaran** (Reg. No. ____)
  - Supervisor: **Name ____**, **Designation ____**
  - Subject: 231ALP711P — Project Work Phase I · Date: ____
- **Say:** "Our project asks whether the forecasts businesses use to predict customer churn are actually trustworthy — not just accurate."

### Slide 2 — Introduction
- **Format:** Title + 4 bullets.
- **On-slide:**
  - In non-contractual settings (retail, e-commerce, groceries) customers **churn silently** — no cancellation to observe.
  - "Buy-Till-You-Die" (BTYD) models — **Pareto/NBD** — infer from purchase history whether a customer is still "alive."
  - These forecasts drive **CLV, targeting and retention-budget** decisions.
  - **Problem:** models are trusted for point predictions — but is the *uncertainty* they report trustworthy? And do ML models really do better?
- **Say:** "Because you never see a customer quit, you must infer it from behaviour — and the question is how much to trust that inference."

### Slide 3 — Objective
- **Format:** Title + 4 numbered bullets.
- **On-slide:**
  - **O1** — Evaluate whether Pareto/NBD forecasts are *calibrated*, not just accurate (CRPS, PIT, coverage).
  - **O2** — Benchmark statistical BTYD vs machine-learning across **counts, value, churn, timing**.
  - **O3** — Diagnose *where and why* calibration breaks.
  - **O4** — Propose and validate **repairs** (conformal recalibration; Pareto/GGG).
- **Say:** "Four objectives — measure calibration, compare the two model families, find the failure, and fix it."

### Slides 4–6 — Literature Survey
- **Format:** Title + **5-column table** per slide: `YEAR | AUTHORS | TITLE | METHODOLOGY | OUTCOME (Adv./Disadv.)`. 3 rows each (9 papers total → satisfies "5+ sources").
- **Slide 4 (foundations):**
  | 1987 | Schmittlein, Morrison & Colombo | Counting Your Customers | Pareto/NBD stochastic "alive?" model | Foundational CBA model; point-error evaluation only |
  | 2005 | Fader, Hardie & Lee | Counting Your Customers the Easy Way | BG/NBD (geometric dropout) | Tractable, widely used; no calibration check |
  | 2016 | Platzer & Reutterer | Ticking Away the Moments | Pareto/GGG (Gamma timing) | Better timing when buying is regular; still point-error |
- **Slide 5 (ML-CLV + the paper we extend):**
  | 2019 | Wang, Liu & Miao | A Deep Probabilistic Model for CLV | Zero-inflated lognormal (ZILN) net | Predicts value distribution; assessed on accuracy, not calibration |
  | 2022 | Valendin et al. | Customer Base Analysis with RNNs | Recurrent neural network | ML gains over BTYD on point error; calibration unexamined |
  | 2025 | Simon | Generalised comparison of Pareto/NBD forecasts | MCMC vs MLE vs heuristics | Motivates us; compares only point error, calls timing "too inaccurate" |
- **Slide 6 (churn ML, recent):**
  | 2005 | Buckinx & Van den Poel | Partial defection in non-contractual FMCG | Logistic / NN / random forests | Canonical churn classifier; accuracy/AUC, no calibration |
  | 2024 | De Caigny, De Bock & Verboven | Hybrid black-box churn prediction | Ensemble + SHAP | Recent ML churn; point classification |
  | 2025 | Imani et al. | Customer Churn Prediction: A Systematic Review | Survey of ML/DL churn | Maps the field; confirms calibration isn't evaluated |
- **Say:** "Two literatures — stochastic BTYD and machine learning — and neither one checks calibration."

### Slide 7 — Summary of Literature
- **Format:** Title + 4 bullets (the gap).
- **On-slide:**
  - BTYD models dominate non-contractual CBA but are judged almost only on **point error**.
  - ML/DL churn & CLV models report accuracy gains — but **never test calibration**.
  - Proper scoring & PIT are standard in weather/energy forecasting, **scarcely used** in CBA.
  - **Gap → our niche:** no one asks whether the uncertainty is trustworthy, or compares BTYD vs ML **by calibration**.
- **Say:** "That empty intersection — calibration × customer forecasting — is exactly where we sit."

### Slide 8 — Architecture of the Proposed Method
- **Format:** Title + **flow diagram** (boxes + arrows, top→bottom). If short on time, a text pipeline works.
- **Diagram (nodes):** `Transaction event logs (7 cohorts)` → `Preprocess → per-customer RFM summary` → split → **two parallel branches** [`Statistical: Pareto/NBD, BG/NBD, Pareto/GGG (MLE/MCMC/amortized)`] and [`ML: Poisson/Hurdle/Quantile-GBM, deep ZILN`] → `Predictive distributions` → `Evaluation: CRPS · PIT · coverage` → `Repairs: conformal recalibration | Pareto/GGG`.
- **Say:** "Both model families run the same pipeline; we score their full predictive distributions and then repair them."

### Slide 9 — Proposed System (Methodology)
- **Format:** Title + 2 mini-sections of bullets.
- **On-slide:**
  - **The calibration lens** — score the whole distribution, not the mean:
    - CRPS (lower = sharper, if calibrated) · PIT (should be Uniform) · coverage (95% ⇒ 95%).
  - **Four dimensions:** how many (counts) · how much (value) · still active? (churn) · when (timing).
  - **Hypothesis:** one shared *parametric count assumption* governs calibration — regardless of estimator (MLE≈MCMC≈amortized) or variant (Pareto/NBD≈BG/NBD).
- **Say:** "One idea unifies the whole paper: calibration is set by the count assumption, not by how you fit the model."

### Slide 10 — Datasets & Initial Implementation  ⭐ (drives the 15-mark item)
- **Format:** Title + 3 labelled blocks.
- **On-slide:**
  - **Datasets — 7 cohorts, activity 1.6% → 96%:** Simulated, CDNow, Online Retail II, Grocery, Olist, Dunnhumby, Ta-Feng.
  - **Preprocessing:** raw event logs → per-customer RFM summary; calibration/hold-out split by rolling cut-point.
  - **Implemented (Python):** Pareto/NBD & BG/NBD (MLE + MCMC Gibbs + amortized neural), Pareto/GGG; ML forecasters (GBM + deep ZILN); conformal recalibration; CRPS/PIT/coverage engine.
  - **Status:** full pipeline running; multi-seed results across all four dimensions →
- **Say:** "This isn't a proposal on paper — the pipeline is built and producing results on seven real datasets."

### Slide 11 — Novelty
- **Format:** Title + 4 bullets.
- **On-slide:**
  - **First** to compare BTYD vs ML by **calibration** (not point error), across all four dimensions.
  - A single diagnosis: the **count assumption** governs calibration.
  - Two validated repairs: **conformal** (model-agnostic) + **Pareto/GGG** (structural).
  - Invariance: MLE≈MCMC≈amortized; Pareto/NBD≈BG/NBD.
- **Say:** "The novelty is the evaluation lens and what it reveals, not the existence of the comparison."

### Slides 12–15 — Results & Discussion  *(one figure each — put figure large, 2–3 bullets above)*
> Figures live in `paper/figures/`. Export/insert the PNGs listed below.

- **Slide 12 — Calibration map (counts).** Fig: `fig_p2_calibration_map.png`.
  - Structure best on sparse (PIT-KS **0.04** Simulated/Grocery); breaks on dense (Online Retail II **0.21**, Dunnhumby **0.17**).
  - Distribution-free **Quantile-GBM wins exactly where BTYD breaks** (Dunnhumby 0.06). No universal winner.
  - **Say:** "The lens doesn't crown a model — it localises where each one's assumption fails."
- **Slide 13 — Repair I: Conformalized BTYD.** Fig: `fig_p2_conformal.png`.
  - One held-out recalibration restores calibration where broken, no harm where fine:
  - Online Retail II **0.212→0.044** · Ta-Feng **0.072→0.027** · Dunnhumby 0.164→0.097 · CDNow 0.056→0.034 (Grocery 0.036→0.036).
  - **Say:** "A single cheap recalibration fixes the intervals without touching the model's fit."
- **Slide 14 — Value & churn.** Fig: `fig_p2_clv.png` (or `fig_p2_churn.png`).
  - Money: deep **ZILN better calibrated** than structural CLV where the count assumption fails (Online Retail II 0.212→0.031).
  - Churn P(active): BTYD calibrated on sparse, miscalibrated on dense; **RFM suffices — demographics add nothing**.
  - **Say:** "The same assumption governs value and churn, not just counts."
- **Slide 15 — Repair II: Pareto/GGG + seasonality.** Fig: `fig_p2_timing.png`.
  - Pareto/GGG cuts next-purchase median error where buying is regular (Grocery **3.89→2.98 weeks**) — rebuts "timing too inaccurate."
  - Seasonality: structural term helps on controlled data (PIT-KS 0.090→0.030); on real cohorts **conformal alone suffices** (0.082→0.021).
  - **Say:** "Where a richer model matches the process, structure wins; otherwise recalibration is enough."

### Slide 16 — Action Plan (Aug → Oct 2026)
- **Format:** Title + 3-row timeline (or Gantt-style table: Month | Milestone).
- **On-slide:**
  - **Aug 2026** — Deep literature review (OpenAlex citation monitor); lock the benchmark across all 7 cohorts.
  - **Sep 2026** — Seasonality & robustness extensions; source an India non-contractual dataset; manuscript revision.
  - **Oct 2026** — Finalise results & figures (uniform theme); prepare Phase-II review / submission.
- **Say:** "Three months: finish the review, harden the results, prepare for Phase II."

### Slides 17–19 — References
- **Format:** Title + reference list (14 pt), split recent→foundational. See §2 for the full list.
- **Slide 17 = recent (2023–2025)**, **Slide 18 = ML & CLV**, **Slide 19 = foundational BTYD + calibration**.
- **Say:** (no narration — flip past, or "full list in the report.")

### Slide 20 — Thank You
- **Format:** Centered "Thank You" + team names; college logo.

---

## 2. Reference list (copy verbatim)

**Recent (Slide 17):**
1. Simon, L. (2025). *A generalised comparison of Pareto/NBD based forecasts using MCMC, maximum likelihood, and heuristics.* Journal of Business Economics, 95, 1079–1105.
2. Imani, M., Joudaki, M., Beikmohammadi, A., & Arabnia, H. (2025). *Customer Churn Prediction: A Systematic Review of Recent Advances, Trends, and Challenges in ML and DL.* (MDPI).
3. De Caigny, A., De Bock, K. W., & Verboven, S. (2024). *Hybrid black-box classification for customer churn prediction with segmented interpretability analysis.* Decision Support Systems.
4. Boukrouh, I., & Azmani, A. (2025). *Explainable machine learning models applied to predicting customer churn for e-commerce.* IAES IJ-AI, 14(1), 286–297.

**ML & CLV (Slide 18):**
5. Valendin, J., Reutterer, T., Platzer, M., & Kalcher, K. (2022). *Customer base analysis with recurrent neural networks.* IJRM, 39(4), 988–1018.
6. Wang, X., Liu, T., & Miao, J. (2019). *A deep probabilistic model for customer lifetime value prediction.* arXiv:1912.07753.
7. Buckinx, W., & Van den Poel, D. (2005). *Customer base analysis: partial defection of behaviourally loyal clients in a non-contractual FMCG retail setting.* EJOR, 164(1), 252–268.
8. Miguéis, V. L., Van den Poel, D., Camanho, A. S., & Falcão e Cunha, J. (2012). *Modeling partial customer churn.* Expert Systems with Applications, 39(12), 11250–11256.
9. Chamberlain, B. P., et al. (2017). *Customer lifetime value prediction using embeddings.* KDD.

**Foundational BTYD + calibration (Slide 19):**
10. Schmittlein, D. C., Morrison, D. G., & Colombo, R. (1987). *Counting your customers: Who are they and what will they do next?* Management Science, 33(1), 1–24.
11. Fader, P. S., Hardie, B. G. S., & Lee, K. L. (2005). *"Counting your customers" the easy way.* Marketing Science, 24(2), 275–284.
12. Platzer, M., & Reutterer, T. (2016). *Ticking away the moments.* Marketing Science, 35(5), 779–799.
13. Abe, M. (2009). *Counting your customers one by one.* Marketing Science, 28(3), 541–553.
14. Gneiting, T., & Raftery, A. E. (2007). *Strictly proper scoring rules, prediction, and estimation.* JASA, 102(477), 359–378.
15. Kuleshov, V., Fenner, N., & Ermon, S. (2018). *Accurate uncertainties for deep learning using calibrated regression.* ICML.

*(Full BibTeX in `paper/refs.bib` and `paper/refs_phase2.bib`; more candidates in `references/`.)*

---

## 3. Figures to export

| Slide | File (`paper/figures/`) | Shows |
|---|---|---|
| 12 | `fig_p2_calibration_map.png` | PIT-KS of 4 forecasters × 7 cohorts |
| 13 | `fig_p2_conformal.png` | before/after conformal recalibration |
| 14 | `fig_p2_clv.png` *(or `fig_p2_churn.png`)* | ZILN vs structural CLV calibration |
| 15 | `fig_p2_timing.png` *(or `fig5_ggg_vs_pnbd.png`)* | GGG vs Pareto/NBD timing error |

Optional spares: `fig_p2_amortized.png` (estimator invariance), `fig_p2_seasonality_real.png` (seasonality),
`fig_p2_robustness.png`, `fig_p2_cost.png`.

**Uniform-theme tip:** before final export, set one color per method and reuse it in every figure —
e.g. BTYD/Pareto-NBD = navy, BG/NBD = slate, Pareto/GGG = teal, ML/GBM = amber, ZILN = purple,
conformal = green. Same palette as the deck (§0).

---

## 4. Delivery notes (viva-ready)

- **Build order:** 9 → 10 → 11, then 12–15. Novelty (11) reads best right after methodology/datasets and before results.
- **Time budget (~11 min):** intro/objective 2 · literature 2.5 · method/architecture 2 · datasets+impl 1.5 · results 2.5 · plan/refs 0.5.
- **Have an answer ready for:** *What is calibration vs accuracy?* · *Why does the count assumption cause miscalibration?* · *What does conformal recalibration actually do?* · *Why compare against ML at all?* — these are the likely viva questions and each maps to a slide.
- **One-sentence pitch:** "We show that popular customer-churn forecasts are often mis-calibrated, we find exactly why, and we fix it two ways."
