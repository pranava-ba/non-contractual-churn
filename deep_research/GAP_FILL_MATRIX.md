---
title: "Gap-Fill Matrix — how our paper patches, fills, and improves on each prior paper"
type: synthesis
created: 2026-08-21
role: "One long table synthesising the deep-dive series + LITERATURE_MATRIX + corpus_critique into a
       single 'what they left open → how we close it' view. Read after LITERATURE_MATRIX.md (which grades
       the novelty defense) — this doc is the constructive companion: not just 'do they calibrate?' but
       'what does our paper *do about* each one?'"
companion: LITERATURE_MATRIX.md · deep_dive.md · corpus_critique.md · gap_crosswalk_manzoor2024.md
math: LaTeX ($...$). Renders in any MathJax/KaTeX viewer, incl. GitHub.
---

# Gap-Fill Matrix — how our paper improves on the prior literature

> **What this is.** [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md) answers the *defensive* question — *does
> any prior paper evaluate customer forecasts by calibration?* (answer: none in the ML stream). This doc
> answers the *constructive* one — **for each prior paper, what gap / open question / limitation does it
> leave, and how does our paper patch, fill, or overturn it?** Every row is distilled from that paper's
> standalone deep-dive (`*_deep_dive.md`) and cross-checked against [`corpus_critique.md`](corpus_critique.md).

## The one-mechanism spine (why every row rhymes)

Our paper's unifying claim is that the calibration behaviour of a structural BTYD forecast is **governed by
its shared parametric count assumption** (Gamma–Poisson), and is *invariant* to the estimator (MCMC / MLE /
heuristic) and to the family variant (Pareto/NBD ≡ BG/NBD). Where that count law matches the
data-generating process, structure wins on calibration; where it fails (dense / over-dispersed / seasonal
regimes), a distribution-free learner or a richer structural model wins. This is why we can (a) inherit
Simon's four managerial tasks unchanged, (b) re-grade every competitor by one lens, and (c) offer **two
repairs** — model-agnostic *Conformalized BTYD* and structural *Pareto/GGG* — as the fixes. Each table row
below is one facet of that single mechanism.

**Legend — Calib?** (from the novelty scoreboard): ❌ point-error / accuracy only · ⚠️ predicts a
distribution but never tests its calibration · ✅ evaluates calibration · 🔬 tool / review, not a customer
forecast. **Our evidence, spanning seven public cohorts** (a ~50× activity range, 1.6 %–96 % active).

---

## 1. The master table

### 1a. The source paper & structural foundations

| # | Paper (yr) · Calib? | What it did / its lens | Gap · open question · limitation it left | **How our paper patches / fills / overturns it** |
|---|---|---|---|---|
| 1 | **Simon (2025)** — *our source paper* · ❌ | First **generalised** comparison of 3 estimators (MCMC/MLE/heuristic) across 4 managerial tasks (counts, active-customer ID, top-$A\%$, next-purchase timing); graded by point error + classification accuracy; proprietary data. | (i) **Point-error / boxplot only** — blind to the predictive distribution. (ii) **Fixes the model, varies only the estimator.** (iii) Declares next-purchase **timing "too large to be used in practice."** (iv) Frames **MCMC as the premium option** to avoid. (v) **Proprietary** (Gusto, Homeshopping) — non-replicable. | We **adopt her four tasks wholesale** and **replace her evaluation with calibration** (CRPS, randomized PIT, coverage, ECE); **add the model axis she holds fixed** (BTYD vs ML). We **overturn timing** (Pareto/GGG cuts median timing error a sixth-to-a-quarter where buying is regular) and **overturn cost** (the vectorised sampler sits on the accuracy–cost frontier — every route calibrates alike). We swap proprietary data for **7 public cohorts.** |
| 2 | **Schmittlein, Morrison & Colombo (1987)** — Pareto/NBD · ❌† | Introduced the model we study: Gamma–Poisson purchasing × exponential lifetime, latent $P(\text{alive})$; graded by aggregate fit. | Hard to estimate; assumes within-window **stationarity**; $P(\text{alive})$ is **latent/unobservable** and never scored by calibration. | We grade this exact model's **predictive distribution** by calibration rather than aggregate fit; **localise** its calibration to the shared count assumption; and forecast the **observable** finite-horizon $P(x^{*}>0)$ instead of the latent $P(\text{alive})$. |
| 3 | **Fader, Hardie & Lee (2005)** — BG/NBD · ❌ | Estimation-friendly geometric-dropout variant (closed form, spreadsheet-fittable); tracking plots + conditional expectations. **Explicitly leaves open** whether the rate–dropout correlation is "good or bad." | Introduces a *variant* but never settles whether it matters; the rate–dropout dependence question is left "for future research." | **Variant-invariance:** Pareto/NBD ≡ BG/NBD *for calibration* — the estimation convenience is free of calibration cost. And our **dependence-stress test answers their 20-year-open question**: the correlation is immaterial to calibration across $\rho\in[-0.6,0.6]$ (PIT–KS stays 0.022–0.029). |
| 4 | **Platzer & Reutterer (2016)** — Pareto/GGG · ❌† | Adds inter-purchase **regularity $k$** ($k{=}1$ = memoryless Pareto/NBD); uses it to sharpen **activity/aliveness** prediction; graded by activity accuracy + tracking. | Regularity deployed **only for aliveness**, graded by **point accuracy**; marketing covariates out of scope. | We **repurpose the same $k$ as Repair II** to forecast next-purchase **timing** — the task Simon called hopeless — cutting median timing error a sixth-to-a-quarter where buying is regular and tying where memoryless, and we grade it by **calibration**. The $k$ knob becomes our decision rule "timing, regular buying → Pareto/GGG." |
| 5 | **Abe (2009)** — HB Pareto/NBD · ❌† | The data-augmentation **MCMC** sampler (basis of `BTYDplus`); hierarchical-Bayes estimation. | Heavy per-customer latent augmentation; dropout rates poorly recovered (Ulrich: corr 0.18 vs 0.80 for purchase rates). | We **implement the sampler** and show **every estimation route calibrates alike**, so full Bayesian inference **need not be traded away** — the sampler is on the accuracy–cost frontier, refuting the "MCMC is the expensive option" framing. |
| 6 | **Fader & Hardie (2010)** — discrete-time BG/BB · ❌† | BTYD for **periodic / discrete** transaction opportunities. | Restricted to discrete-opportunity settings. | Named in our **Limitations / future work** as the natural model for periodic cohorts (ours are continuous-time). |

### 1b. Machine-learning competitors (the direct contest)

| # | Paper (yr) · Calib? | What it did / its lens | Gap · limitation it left | **How our paper patches / fills / improves** |
|---|---|---|---|---|
| 7 | **Wang, Liu & Miao (2019)** — deep ZILN · ⚠️ | Predicts the **full zero-inflated-lognormal value distribution** with one network; evaluated by **decile charts** (predicted-vs-actual *mean* LTV) + normalized Gini. | "Calibration" = **mean-per-decile reliability only** — *not distributional* (no PIT / CRPS / coverage); **value target only**. The single competitor that comes closest to our lens while stopping short. | We **adopt ZILN as our value comparator** and grade it **distributionally** (PIT–KS, coverage): ZILN is **better calibrated than structural CLV on every monetary cohort at comparable accuracy** — the monetary face of the count-assumption mechanism. Naming Wang as the honest **⚠️ partial exception** *sharpens* the novelty claim ("ML reaches decile-mean, not distributional, calibration") rather than threatening it. |
| 8 | **Valendin et al. (2022)** — RNN CBA · ❌ | **LSTM on the raw event stream** beats Pareto/NBD, Pareto/GGG, GPPM on individual-level **RMSE** across 8 cohorts; **learns seasonality automatically**. | **Point-error only** (RMSE/MAE/bias/NITT); every "calibration" in the text = the *estimation window*; never PIT/CRPS/coverage. | Our paper **is the calibration re-run of their comparison.** We cite them as the **closest ML-vs-BTYD benchmark** and the **named next comparator under our lens** — the sequence model most likely to extend its advantage in the non-stationary regime (our acknowledged weak spot). We borrow their **descriptive-tag table** idea and mined their **GPPM (Dew & Ansari 2018)** citation as a fourth route to escaping the count law. |
| 9 | **Chamberlain et al. (2017)** — CLV embeddings · ❌† | Learned embeddings rival hand-crafted RFM in a deployed CLV system. | **Point-error only; proprietary.** | Cited as an **ML-CLV counterpoint** — a learned-feature route to CLV that is still ungraded by calibration; sits inside the ML class our lens re-examines. |
| 10 | **Gupta et al. (2006)** — Modeling CLV · ❌† | Maps the CLV terrain; notes next-period-only models under-serve full CLV. | Pre-ML, **pre-calibration** (2006). | Cited for **framing the CLV landscape** our four-target study spans. |

### 1c. Non-contractual churn classification (the profit/accuracy stream)

| # | Paper (yr) · Calib? | What it did / its lens | Gap · limitation it left | **How our paper patches / fills / improves** |
|---|---|---|---|---|
| 11 | **Buckinx & Van den Poel (2005)** · ❌† | Canonical **non-contractual churn**; restricts to loyal/"best" customers to sidestep unidentifiability; AUC/accuracy, thresholded churn. | Only the **best customers**; **thresholded** churn; **no calibration**. | Cited (v2.0.2) as the canonical non-contractual churn reference; we forecast **probabilistic, finite-horizon, cut-off-free** churn ($P(x^{*}>0)$) with calibration over the *whole* base, not a thresholded classifier on a restricted subset. |
| 12 | **Miguéis et al. (2012)** · ❌† | First-category purchase sequences predict **partial churn**; point error. | **Offline baskets only; point-error.** | Cited (v2.0.2) as behavioural-churn lineage; subsumed by our calibrated probabilistic churn target. |
| 13 | **De Caigny et al. (2024)** · ❌ | Hybrid black-box churn + **SHAP** segmented interpretability; AUC / EMP-profit. | **No calibration.** | Cited (v2.0.3, XAI ¶); we position **structural interpretability + Conformalized BTYD** as the calibration-side answer to the performance–interpretability tradeoff, and name SHAP-style attribution as future work. |
| 14 | **ChurnNet — Saif et al. (2026)** · ❌ | **Conventional ensembles still beat** an elaborate deep time-series model in non-contractual retail; accuracy/precision/recall/F1/AUC. | **No calibration.** | Cited (v2.0.3) — **corroborates our "flexible ≠ better" thesis from the accuracy side**: added structural complexity does not automatically pay off, mirroring our calibration finding. |
| 15 | **Coolwijk (2024) · Wachwanakijkul (2024) · Mufti (2026) · Boukrouh (2025) · Leoni–Perego (2022) · Sci Rep (2024)** · ❌ ×6 | Recent churn variety — ViT/radar-image, car-sharing, rolling-window labelling, XAI e-commerce, retail thesis, ensemble-fusion telecom. | **All point-error / accuracy / profit; 0 calibration.** | **Scanned;** Boukrouh cited (XAI ¶); the rest **strengthen the novelty scoreboard** (each ❌ is one more direct competitor that never evaluates by calibration). None enters the comparison set. |

### 1d. Field reviews (the state-of-the-field anchors)

| # | Paper (yr) · Calib? | What it did / its lens | Gap it leaves (incl. the *reverse* gap) | **How our paper patches / fills / improves** |
|---|---|---|---|---|
| 16 | **Manzoor et al. (2024)** — IEEE Access review · 🔬 | Field-level review of ML churn (212 studies); names **5 critical gaps**; metric frontier reaches **profit** (MPC/EMP, Verbraken 2013). | **0 BTYD, 0 calibration** in full text. Its sharpest metric complaint (G4) reaches profit but **stops before calibration** — a *reverse gap* the review itself never names. | We **patch 4 of their 5 field gaps** (see [`gap_crosswalk_manzoor2024.md`](gap_crosswalk_manzoor2024.md)) — public data (G1), calibration as the metric upgrade past profit (G4), structural interpretability + Conformalized BTYD (G5) — **and fill the calibration gap the review omits.** Cited as **field survey #1** + the **profit-metric lineage** springboard. |
| 17 | **Imani et al. (2025)** — MDPI PRISMA review · 🔬 | **PRISMA-2020** systematic review (240 screened / 61 deep); names class imbalance, interpretability, **concept drift**, limited profit metrics. | **0 BTYD, 0 calibration.** A current (2025) synthesis that reaches drift + profit but **never reaches calibration**, and never touches the structural BTYD tradition. | **Independent, current corroboration** of the reverse gap and the siloed-literatures point; cited as **field survey #2.** Its **PRISMA funnel (Fig. 1)** and **taxonomy (Fig. 12)** are the templates for our `fig:prisma` and `fig:taxonomy`. Confirms **no India non-contractual dataset** across 240 studies (bears on open item F8). |

### 1e. The concurrent BTYD-calibration paper (the only ✅ — a complement)

| # | Paper (yr) · Calib? | What it did / its lens | Boundary it draws (what it declines / leaves open) | **How our paper improves on / complements it** |
|---|---|---|---|---|
| 18 | **Ulrich (2026)** — *Dead Reckoning* · ✅ (BTYD-only) | Scores **BTYD aliveness** calibration (CORP reliability, Brier+Murphy, ECE, AUC) on an out-of-time $(v,H)$ grid; proves the summed "alive" count is **partially identified** (7.6× spread across observationally-equivalent specs; 42 % from a ridge default; 2.4× on CDNOW); names the **"category error"** ($\sum A$ overshoots realized returners 2.25× while the same model's $R_H$ errs only 1.18×); offers a dynamic loss-development recalibration layer. | **Deliberately excludes ML** ("did not run the horse race … the challenger reports no alive count at all, which may be a feature"). **Churn / aliveness only** — value, timing, and the counts-calibration map are out of scope. Remedy (loss-development triangle) heavier than needed. Concurrent "first to score BTYD-aliveness calibration" overlaps us **only on the churn target**. | We **run exactly the ML horse race he declines**, across **all four targets** and **7 public cohorts**, by calibration. Our churn target $P(x^{*}>0)$ **is his identified $R_H$** — we sit on the *correct side of his category error* and give it his name. We **cite his partial-ID** as the reason the count is ill-posed and note our finite-horizon target **sidesteps** it (interval reporting = future work). Our **per-window conformal is the lightweight cousin** of his dynamic layer; our frozen-warp drift result independently corroborates his "a static map bets the past persists." **Complement, not competitor** — overlap is a single, properly-cited, concurrent point. |

---

## 2. Evaluation tools — adopted as-is, not "improved on"

These are methods we **use in the regime they were designed for**, not prior customer-forecasting papers
we patch. Listed for completeness (full notes in [`corpus_critique.md`](corpus_critique.md) §4).

| Tool paper | What we take from it |
|---|---|
| Gneiting & Raftery (2007); Gneiting, Balabdaoui & Raftery (2007) | CRPS / log-score foundation; the *sharpness-subject-to-calibration* guiding principle |
| Czado, Gneiting & Held (2009) | the **randomized PIT** for small, zero-inflated counts — exactly our regime |
| Kuleshov, Fenner & Ermon (2018) | isotonic recalibration → our **Conformalized BTYD** |
| Guo et al. (2017) | ECE + reliability; temperature scaling named as an alt recalibration family |
| Dimitriadis, Gneiting & Jordan (2021) | **CORP reliability diagrams** (`fig:reliability`) — the same instrument Ulrich adopts |
| Lilliefors (1967) | the parametric-bootstrap **PIT–KS null** (App. G) |
| Friedman (2001); Koenker & Bassett (1978) | the GBM / QuantileGBM ML forecasters |
| Cranmer et al. (2020) | positions our amortized estimator in the SBI frontier (`fig:taxonomy`) |

---

## 3. Rollup — the four things our paper does that none of the above did

1. **One lens across the whole field.** We re-grade the source paper, both ML paradigms (RFM-summary GBM/ZILN
   *and*, by pointer, sequence-RNN), and the churn-classification stream by **probability calibration** —
   the metric that the ML-CLV literature (Wang ⚠️), the RNN benchmark (Valendin ❌), and *both* 2024–25 field
   reviews (Manzoor, Imani — 🔬, profit-but-not-calibration) never apply.
2. **The model axis Simon held fixed.** Structural BTYD **vs** ML, decided by calibration and localised to one
   mechanism (the shared count assumption), invariant to estimator and family variant.
3. **Two overturned verdicts + two open questions answered.** Timing (vs Simon, via Platzer's $k$) and cost
   (vs Simon, sampler on the frontier) are overturned; Fader (2005)'s rate–dropout question and Manzoor
   (2024)'s unnamed calibration gap are answered.
4. **Replicable evidence.** Seven **public** cohorts spanning ~50× activity replace the field's proprietary /
   telecom-UCI norm — patching the replicability half of the reviews' dataset gap.

---
*Companion to [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md) (novelty defense),
[`deep_dive.md`](deep_dive.md) (the plan + trackers), the eight `*_deep_dive.md` files (per-paper detail),
and [`corpus_critique.md`](corpus_critique.md) (takeaway/flaw/coverage per paper). Every claim here is
sourced from those docs; no experiment is reopened.*
