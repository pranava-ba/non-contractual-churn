---
title: "Corpus critique — every local paper: best takeaway, biggest flaw, and does our paper cover it"
type: critique
created: 2026-08-11
purpose: A paper-by-paper critical read of the entire local library (references/), oriented to one
         question — how can it improve OUR manuscript? Deepest focus on Ulrich (2026) and Simon (2025).
companion: deep_dive.md · LITERATURE_MATRIX.md · gap_crosswalk_manzoor2024.md
---

# Corpus critique

**Scope.** Every PDF under [`../references/`](../references/), read for three things: the single best
*takeaway*, the biggest *flaw/limitation*, and whether our manuscript (`paper/manuscript_phase2.tex`,
v2.0.6) already *covers* it — plus a concrete *action* where it doesn't. Method: full read for the
high-stakes papers (Ulrich, Simon, Platzer, Valendin, Wang, the two reviews) and full-text term-scan +
targeted reads for the rest (`scratchpad/critique_scan.py`).

**Headline.** Nothing in the corpus threatens the thesis, and the coverage is strong. The read
surfaced **seven concrete improvements** (§5), of which three are worth doing now: (i) answer Fader
(2005)'s explicitly-open rate–dropout question with our dependence-stress result; (ii) make the Data
table's buying-pattern chips *quantitative* using the Wheat–Morrison regularity statistic
$r_{\text{WM}}$ and clumpiness (as Platzer 2016 and Valendin 2022 do); (iii) fold Ulrich's
partial-identification *interval* into the churn/limitations discussion.

---

## 1. The two load-bearing papers

### 1a. Ulrich (2026), *Dead Reckoning* — the concurrent BTYD-calibration paper ⭐

**Best takeaways (what we should keep).**
1. **The identity $A=\lim_{H\to\infty}R_H$.** The summed "alive" count is the infinite-horizon limit of
   an observable family of finite-horizon return probabilities $R_H=P(X_H\ge1)$. This is the cleanest
   possible statement of *why* our finite-horizon $P(x^*>0)$ target is the right one — and it is his,
   so we cite it (done, §churn).
2. **The "category error."** Grading summed $P(\text{alive})$ against a finite-horizon realised outcome
   overshoots (~2.25× on his panel) while the *same model's* $R_H$ forecast errs ~1.18×. Most apparent
   BTYD "miscalibration" of aliveness is a horizon category error, not model failure. Naming it is a
   gift: it pre-empts the reviewer who says "but BTYD aliveness is famously miscalibrated."
3. **Partial identification / set-identified count.** Realised returners are a hard lower bound; the
   point above it is chosen by estimation convention (structure, prior, a software ridge default —
   7.6× spread across observationally-interchangeable specs; 42% from a ridge default alone). *This is
   his, not ours* — we must never claim it, only acknowledge it.
4. **Static-map-fails-under-drift.** A recalibration frozen on past data "is a bet that the past
   persists"; under drift it must give way to a dynamic (Bornhuetter–Ferguson loss-development) layer.
   Independent corroboration of our seasonal-conformal result (frozen warp does nothing, $r$ stays 0.94).
5. **He hands us the ML citation.** He explicitly declines the ML horse race (p.27) and notes the
   discriminative challenger "reports no alive count at all (Valendin 2022), which… may be a feature."
   Our central axis is untouched and he supplies the motivation for it.

**Biggest flaws / where to push back.**
- **Working draft, single author, self-supplied data.** arXiv v4, not peer-reviewed; data from
  MakerStock, which he co-founded — a selection/COI caveat we can note when leaning on his numbers.
- **The identified interval is honest but can be managerially vacuous.** $[\text{realised returners},
  \infty)$ is trivially wide; the *practical* payload is the $R_H$ reframing, not the interval. Our
  finite-horizon design already delivers the payload without needing the interval.
- **Churn/aliveness only.** Value, timing and the *counts* calibration map are out of scope for him
  (p.27, "revenue and profit are out of scope"). Our four-target reach is the differentiator.
- **His remedy is heavier than ours.** The dynamic loss-triangle layer is more machinery than our
  one-pass per-window conformal warp; we should position ours as the lightweight cousin (done, §robust).

**Have we covered all of it?** Almost. Cited + distinguished at four sites (intro first-claim, Related
Work, §churn category-error, §robust drift). **Gap:** we do not yet mention his *partial-identification
interval* as a reporting option. **Action A1 (§5).**

### 1b. Simon (2025), *A generalised comparison* — our source paper

**Best takeaway.** The four managerial tasks we inherit wholesale — future counts, active-customer
identification, top-segment ranking, next-purchase timing — plus the clean finding that model-based
forecasts beat heuristics on the first three and that MCMC is marginally preferable to MLE. It is the
scaffold our paper stands on.

**Biggest flaws (which are literally our contribution).**
- **Point-error/boxplot evaluation only** — no proper scoring, no calibration. This is the gap our
  whole paper fills.
- **Declares timing "too inaccurate to use"** without trying a richer process. We overturn this with
  Pareto/GGG (§timing) — a direct refutation, not an extension.
- **Holds the model fixed, varies only the estimator.** We do the opposite (fix the lens, vary the
  model), which is the cleanest framing of our novelty.
- **Proprietary data (Gusto/Homeshopping)** — non-replicable. We substitute seven public cohorts.
- **Frames MCMC as the costly option to avoid.** We show the vectorised sampler sits on the
  accuracy–cost frontier (§cost) — a second, quieter refutation.

**Have we covered all of it?** Yes, comprehensively — Simon is the motivating spine of Related Work,
§timing, and §cost. No action needed beyond what is already written.

---

## 2. BTYD foundations

| Paper | Best takeaway | Biggest flaw (often their own admission) | Our coverage | Action |
|---|---|---|---|---|
| **Schmittlein, Morrison & Colombo (1987)** — Pareto/NBD | The model itself; the $P(\text{alive})$ expression | Hard to estimate; assumes stationarity within the window | Cited; the model we study | — |
| **Fader, Hardie & Lee (2005)** — BG/NBD | Computationally-easy geometric-dropout alternative | **They explicitly leave open** whether the rate–dropout correlation is "good or bad" ("we hope future research will shed light") | Variant-invariance shown; cited | **A2:** our dependence-stress test *answers this open question* — say so |
| **Fader & Hardie (2010)** — discrete-time (BG/BB) | BTYD for periodic/discrete transaction opportunities | Restricted to discrete-opportunity settings; Schmittlein's "regular opportunity" caveat | Not used (our cohorts are continuous-time) | **A6:** name as future work for periodic cohorts |
| **Platzer & Reutterer (2016)** — Pareto/GGG | Gamma inter-purchase timing (regularity $k$) improves activity prediction; defines $r_{\text{WM}}$ + clumpiness $C$ | Own admission: marketing covariates "beyond scope"; $C$ can't separate clumpiness from latent churn | **Our timing repair**; cited | **A3:** adopt their $r_{\text{WM}}$/clumpiness to quantify our cohort descriptor chips |
| **Abe (2009)** — HB Pareto/NBD | The data-augmentation MCMC sampler we implement | Heavy (per-customer latent augmentation) | Our sampler; cited | — |
| **McCarthy & Wadsworth (2014)** — BTYD walkthrough | Reference implementation of estimation | Software vignette; the un-patched BTYD had a known bug | Our own Python impl.; cite for orientation | — |
| **Ganeson, Lew & Razak (2022)** — churn window | Each customer has an individual churn window (colored diagrams) | Heuristic (historical average), not probabilistic; no calibration | Our `fig:churnwindow` does this probabilistically | **A4:** cite it in §churn for the per-customer-window idea |
| **Hospitality churn (2025)** — BG/NBD + RL | Extends identification to multiple interactions + an RL action layer; notes churn risk *evolves over time* | Domain-specific; bespoke RL thresholds; no calibration | Action/RL layer is out of our scope | mention as action-layer future work (low) |

## 3. ML for CLV / churn (the competitors)

| Paper | Best takeaway | Biggest flaw | Our coverage | Action |
|---|---|---|---|---|
| **Gupta et al. (2006)** — CLV review | Maps the CLV terrain; "next-period-only" models under-serve full CLV | Pre-ML, pre-calibration (2006) | Cited for framing | — |
| **Chamberlain et al. (2017)** — CLV embeddings (ASOS) | Learned features rival handcrafted RFM in a deployed system | Point-error only; proprietary | ML-CLV counterpoint; cited | — |
| **Wang, Liu & Miao (2019)** — deep ZILN | Model the full value distribution directly (our value comparator) | "Calibration" = decile charts of the *mean*, not distributional (no PIT/CRPS/coverage) | Strongest value comparator; `tab:clv` highlights ZILN's calibration win | covered (⚠️ noted) |
| **Valendin et al. (2022)** — RNN CBA | Sequence model beats Pareto/NBD on point error; **rich descriptive-stats + colored tags** (our figure/table reference) | Point-error only; "calibration" = *estimation window* throughout | Closest ML-vs-BTYD benchmark; cited; the natural next comparator under our lens | **A3** (borrow $r_{\text{WM}}$) already adopts their tag idea |
| **Buckinx & Van den Poel (2005)** | Canonical non-contractual churn; restrict to loyal customers to sidestep unidentifiability | Only "best" customers; AUC/accuracy; threshold churn | Cited (v2.0.2) | — |
| **Miguéis et al. (2012)** | First-category sequences predict churn | Offline baskets only; point-error | Cited (v2.0.2) | — |
| **De Caigny et al. (2024)** — hybrid black-box + segmented interpretability | SHAP-based visualization of hybrid churn models | AUC/EMP-profit; no calibration | Cited (v2.0.3, XAI ¶) | — |
| **Saif et al. (2026)** — ChurnNet | *Conventional* ensembles still beat an elaborate deep time-series model in non-contractual retail | Accuracy/precision/recall; no calibration | Cited (v2.0.3) — corroborates "flexible ≠ better" | — |
| Coolwijk (2024) ViT · Wachwanakijkul (2024) car-sharing · Mufti (2026) rolling-window · Boukrouh (2025) XAI · Leoni–Perego (2022) thesis · Sci Rep (2024) ensemble | recent churn variety | all point-error/accuracy; **0 calibration** | scanned; Boukrouh cited (XAI); rest discard/optional | — |

## 4. Field reviews & evaluation tools

| Paper | Role for us | Note |
|---|---|---|
| **Manzoor et al. (2024)** — IEEE Access review | Field survey #1; profit-metric lineage | 212 studies, **0 BTYD, 0 calibration**; cited (v2.0.3) |
| **Imani et al. (2025)** — MDPI PRISMA review | Field survey #2 | 240 studies, **0 BTYD, 0 calibration**; cited (v2.0.3) |
| **Gneiting & Raftery (2007)** — proper scoring | CRPS / log-score foundation | used correctly |
| **Gneiting, Balabdaoui & Raftery (2007)** — sharpness/calibration | Our *guiding principle* (maximise sharpness s.t. calibration) | used correctly |
| **Czado, Gneiting & Held (2009)** — PIT for counts | The **randomized PIT** we need for small, zero-inflated counts | exactly our regime ("low count situation where continuum approximations fail"); used correctly |
| **Guo et al. (2017)** — NN calibration | ECE + temperature scaling | we use ECE; temperature scaling is an alt recalibration we could name |
| **Kuleshov, Fenner & Ermon (2018)** — calibrated regression | Isotonic recalibration → **Conformalized BTYD** | limitation: asymptotic guarantee, needs a held-out split; we adapt to discrete BTYD |
| **Lilliefors (1967)** — KS with estimated params | Logic for our parametric-bootstrap PIT–KS null | used correctly (App. G) |
| **Friedman (2001)** — GBM | The gradient-boosting forecasters | used correctly |
| **Koenker & Bassett (1978)** — quantile regression | The distribution-free QuantileGBM | used correctly |
| **Cranmer et al. (2020)** — SBI frontier | Positions our amortized estimator | now visualised in `fig:taxonomy`/`fig:architecture` |

**Verdict on the tools:** every method is used in the regime it was designed for, and cited. No
corrections needed; the only optional touch is naming temperature scaling (Guo) alongside our conformal
map as one more recalibration family (we already promise Platt/isotonic/full-conformal comparison as
future work).

---

## 5. Improvements for our paper (prioritised)

| # | Improvement | Source | Effort | Value |
|---|---|---|---|---|
| **A2** | State that our **dependence-stress test answers Fader (2005)'s open question** on whether rate–dropout correlation is "good or bad" (it is immaterial to calibration across $\rho\in[-0.6,0.6]$) | Fader 2005 | 1 sentence | **high** — turns a robustness check into a 20-year-old open-question answer |
| ~~**A3**~~ | ~~Make the descriptor chips quantitative with regularity + seasonality stats~~ **— investigated 2026-08-11, do NOT add.** Computed per-cohort inter-purchase-CV regularity ($k=1/\text{CV}^2$: CDNow 1.30, Grocery 2.49, Olist 1.54, Ta-Feng 1.63, Dunnhumby 0.98, ORII 1.88 — all mildly regular except memoryless Dunnhumby) and a Valendin-eq.4 static seasonality score. **The static seasonality metric contradicts the paper's authoritative result:** it scores Online Retail~II only 0.31 ("low") yet ORII is *the* seasonal cohort by the §robust rolling-window analysis ($r=0.93$), and scores sparse Olist highest (1.12, on just 152 multi-purchase customers). A static calibration-window MAD measures something different from the dynamic forecast-ratio-vs-intensity correlation. **Keep the chips qualitative** (they are backed by §data/§robust); reconciling the two seasonality measures is itself a minor future-work note, not a table change. | Platzer 2016 / Valendin 2022 | done (investigated) | resolved: keep qualitative |
| **A1** | Acknowledge Ulrich's **partial-identification interval** for the aliveness *count* in §churn/Limitations, and note reporting an identified interval as future work (sidestepped by our finite-horizon target) | Ulrich 2026 | 1–2 sentences | med-high — deepens the Ulrich engagement, pre-empts the identification critique |
| **A4** | Cite **Ganeson (2022)** in §churn for the per-customer churn-window concept our `fig:churnwindow` formalises | Ganeson 2022 | 1 cite | med (needs bib entry) |
| **A5** | Name **temperature scaling (Guo 2017)** alongside isotonic/Platt/full-conformal in the recalibration-variants future-work sentence | Guo 2017 | 1 phrase | low |
| **A6** | Note **discrete-time BTYD (Fader 2010)** as the natural model for periodic-transaction cohorts in Limitations | Fader 2010 | 1 phrase | low |
| **A7** | Position our per-window conformal as the lightweight cousin of Ulrich's **dynamic Bornhuetter–Ferguson layer** as an explicit future extension | Ulrich 2026 | 1 sentence | low (partly done in §robust) |

**Recommended now:** A2, A1, A5, A6, A7 (all prose, zero new data risk) and A3 (a real, on-theme data
enhancement that makes the Valendin-style table rigorous). A4 needs a verified bib entry for Ganeson.

---

## 6. Reference-mining Ulrich's bibliography (2026-08-11) — four verified adds

Mined the 39-page Ulrich (2026) PDF's reference list (he is the closest calibration-adjacent work, so
his bibliography is the likeliest place to find a customer-forecast calibration paper we missed).
No missed *calibration* competitor — but four genuinely useful, OpenAlex-verified adds surfaced, now
folded into v2.0.8:

| Added | Why it matters | Placed |
|---|---|---|
| **Gopalakrishnan, Bradlow & Fader (2017)** — cross-cohort changepoint model (Mktg Sci 36(2):195–213) | A **structural** BTYD route to non-stationarity — directly grounds our headline seasonality limitation | §Limitations |
| **Bachmann, Meierer & Näf (2021)** — time-varying contextual factors in latent attrition (Mktg Sci 40(4):783–809) | Second structural non-stationarity route; "bring it under the calibration lens" is now concrete | §Limitations |
| **Jerath, Fader & Hardie (2011)** — generalization of Pareto/NBD for customer "death" (Mktg Sci 30(5):866–880) | Another Pareto/NBD generalization (dropout process) for completeness | §Related Work |
| **Van Calster et al. (2019)** — "Calibration: the Achilles heel of predictive analytics" (BMC Medicine 17:230) | High-profile external statement that calibration matters — strengthens the intro motivation | §Introduction |

**Valendin (2022)'s bibliography, same pass** — two more OpenAlex-verified adds:

| Added | Why it matters | Placed |
|---|---|---|
| **Dew & Ansari (2018)** — Bayesian nonparametric CBA / Gaussian-process propensity (Mktg Sci 37(2):216–235) | A **fourth route** to escaping the parametric count law — a *nonparametric structural* model — completing the taxonomy of fixes (ML / conformal / richer-parametric / nonparametric) | §mechanism ("why the count assumption is the axis") |
| **Lemmens & Gupta (2020)** — managing churn to maximize profits (Mktg Sci 39(5):956–973) | Rounds out the profit-metric lineage beside Verbraken/Manzoor | §profit |

Also noted but **not** added (out of scope or redundant): Bornhuetter–Ferguson (1972, actuarial IBNR —
Ulrich's dynamic layer), Brier (1950), Manski (2003, partial-ID foundation), Gneiting & Jordan (2021,
CORP reliability diagrams — a methodological upgrade we could adopt if we add reliability diagrams),
McCarthy & Fader (2018, CBCV). ~~The CORP reliability-diagram method (Dimitriadis–Gneiting–Jordan 2021,
used by Ulrich) is the one genuine *methodology* upgrade on the table for a future revision.~~
**Done (v2.0.9, 2026-08-11):** implemented CORP reliability diagrams for churn (`fig:reliability`,
`src/make_reliability_data.py`), pooling per-customer P(active) over four splits and fitting the
isotonic/PAV curve — BTYD hugs the diagonal where the count law fits and departs where it breaks.

---
*Companion to [`deep_dive.md`](deep_dive.md), [`LITERATURE_MATRIX.md`](LITERATURE_MATRIX.md), and
[`gap_crosswalk_manzoor2024.md`](gap_crosswalk_manzoor2024.md). Nothing here reopens experiments; it is
a write-up/citation sharpening pass.*
