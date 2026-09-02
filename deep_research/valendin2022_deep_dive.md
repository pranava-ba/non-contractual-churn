---
title: "Valendin et al. (2022), *Customer Base Analysis with Recurrent Neural Networks* — deep-dive"
type: deep-read
created: 2026-08-11
source: "Jan Valendin, Thomas Reutterer, Michael Platzer, Klaudius Kalcher. Customer base analysis with
         recurrent neural networks. International Journal of Research in Marketing 39(4) (2022) 988–1018.
         DOI 10.1016/j.ijresmar.2022.02.001. Local: references/phase2/09_valendin_2022_rnn_customer_base.pdf"
role: "The closest existing ML-vs-BTYD customer-base benchmark, and the natural next comparator to bring
       under our calibration lens. Their descriptive-stats table inspired our colored Data-table chips."
math: LaTeX. companion: deep_dive.md · corpus_critique.md · LITERATURE_MATRIX.md §2b
---

# Valendin et al. (2022) — deep-dive

**Thesis.** Replace the parametric BTYD machinery with an **LSTM that reads each customer's raw
purchase-timing sequence** and simulates their future transaction stream. It matches or beats Pareto/NBD,
Pareto/GGG, and the Gaussian-process propensity model (Dew & Ansari 2018) on individual-level RMSE across
eight real cohorts, and — the headline — **infers seasonality directly from the data without being told
it exists**.

---

## 0. TL;DR — Valendin vs. our paper

| Axis | **Valendin (2022)** | **Our paper** |
|---|---|---|
| **ML paradigm** | **sequence model (LSTM)** on the *raw event stream* | **RFM-summary models** (GBM variants, ZILN) |
| **Comparison** | LSTM vs. structural BTYD (P/NBD, P/GGG, GPPM) | structural BTYD vs. ML, *both* paradigms |
| **Evaluation** | **point error** — individual RMSE, MAE, aggregate bias, NITT | **calibration** — CRPS, PIT, coverage, ECE |
| **Seasonality** | a *strength* — the LSTM learns it from the stream | a *limitation* — stationary BTYD + RFM-ML cannot |
| **Targets** | counts, timing (NITT), aggregate tracking | counts, value, churn, timing |
| **Data** | 8 real cohorts (incl. CDNOW), rich descriptive tags | 7 public cohorts |
| **Relationship** | **the point-error version of the comparison we run by calibration.** Their RNN is the natural next comparator under our lens, and most likely to win exactly where we are weakest (non-stationarity). |

---

## 1. What the paper does
- **Model.** A Long Short-Term Memory recurrent network consumes a customer's discretised
  (weekly/monthly) transaction sequence and is trained to predict the next-period activity; forecasting
  proceeds by **simulating** many future sequences per customer, from which any quantity (counts, timing,
  aggregate tracking) is read. A **Base LSTM** uses only the transaction stream; an **Extended LSTM** adds
  time-varying and static covariates (marketing appeals, demographics).
- **Benchmarks.** Pareto/NBD (MCMC via `BTYDplus`), Pareto/GGG, and the Gaussian-Process Propensity Model
  (GPPM; Dew & Ansari 2018).
- **Data (Table 3).** Eight cohorts — Charity Contributions, Electronics Retailer, Blood Donations,
  **CDNOW**, Groceries, Yogurt Purchases, Multichannel Merchant, Sunscreen — each characterised by a rich
  descriptive battery: cohort size, **clumpiness**, the **Wheat–Morrison regularity $r_{\text{WM}}$**, a
  **seasonality score**, calibration/holdout lengths, mean events, non-repeaters, inactive fraction.
- **Evaluation.** Individual-level **RMSE** (their preferred metric, penalising large errors under low
  event frequencies), MAE for the median, aggregate **forecast bias**, and **NITT** (next inter-transaction
  time). Best result per dataset in bold; the LSTM rows are color-highlighted.
- **Findings.** The LSTM performs best in *all eight* scenarios, with the largest individual-level gains in
  **high-frequency** settings (Groceries, Yogurt) and smaller gains in low-frequency ones (Blood Donations,
  Sunscreen). On timing (NITT) the Base LSTM deviates only ~2.8% on average vs Pareto/NBD ~11.8%,
  Pareto/GGG ~13.2%, GPPM ~19.2%. On the Christmas-period forecast, the LSTM tracks the seasonal peak the
  parametric models miss — "remarkable, because the deep learning model was not informed that there was
  something like a holiday season but directly inferred this from the observed stream"; it even handles a
  *reversed* seasonal pattern (Sunscreen, summer peak).

## 2. Novelty
The first customer-base-analysis application of a **sequence-to-sequence deep learning** model that (i)
needs no hand-engineered features (it reads the raw stream), (ii) learns **seasonality and covariate
response** automatically, and (iii) matches or beats the BTYD family on individual-level point error
across a wide cohort range. It reframes CBA from parametric estimation to learned simulation.

## 3. How it differs from our paper
- **They evaluate by point error; we evaluate by calibration.** Their entire results battery (RMSE, MAE,
  bias, NITT) is blind to the predictive distribution — the exact gap our paper fills. Every "calibration"
  in their text refers to the *estimation window*, not to forecast reliability; they never test PIT, CRPS,
  or coverage. Our paper is, in effect, the calibration re-run of their comparison.
- **Different ML paradigm.** Their LSTM operates on the raw event *sequence*; our ML forecasters (Poisson-,
  Hurdle-, Quantile-GBM, deep ZILN) operate on RFM *summaries*. Sequence models can express dynamics
  (seasonality, regime shifts) that RFM summaries cannot — which is why their RNN wins where ours would
  not, and why it is a distinct comparator, not a substitute.
- **Their strength is our limitation.** The RNN's automatic seasonality learning is precisely the
  non-stationarity axis on which our stationary structural model breaks (and where our per-window conformal
  and structural-seasonal repairs are only partial). Under our lens, their RNN is *the model most likely to
  extend its advantage in the non-stationary regime* — which our Limitations already anticipates.
- **Point-error wins ≠ calibration wins.** They report accuracy gains over Pareto/NBD on large datasets;
  our finding is that on *calibration*, structure wins on sparse/regular cohorts and only a
  distribution-free learner wins on dense ones — a distinction their metrics cannot see.

## 4. How we use it to improve our paper
- **Cited as the closest ML-vs-BTYD benchmark** (Related Work) and, explicitly, as **the natural next
  comparator to bring under the calibration lens** (Limitations) — the RNN on the raw event stream is the
  one most likely to extend its advantage where we are weakest.
- **Their descriptive-stats table (Table 3) inspired our colored Data-table chips** (sparse/dense/seasonal
  regime tags), and their $r_{\text{WM}}$/clumpiness/seasonality battery is the source we point to for a
  quantitative upgrade of those chips (investigated in `corpus_critique.md` A3).
- **They benchmark against GPPM (Dew & Ansari 2018)** — a citation we mined and added as the nonparametric
  structural route to escaping the count assumption.
- **Framing:** their result that gains concentrate in *high-frequency* settings dovetails with our
  mechanism — dense, over-dispersed data are exactly where the parametric count assumption fails and a
  flexible learner escapes.

## 5. Verdict
**The most important ML comparator, and a complement.** Valendin is what our paper is *about* — the
BTYD-vs-ML contest — but run on point error instead of calibration, with a sequence model instead of
RFM-ML. We keep it central: the closest prior benchmark, the source of our descriptive-tag idea, and the
named next comparator under our lens. No tension; it defines the frontier our calibration lens re-examines.

---
*Part of the deep-dive series. Companion to [`deep_dive.md`](deep_dive.md) and
[`corpus_critique.md`](corpus_critique.md). Its RNN + seasonality strength is the mirror image of our
non-stationarity limitation — see [`ulrich_deep_dive.md`](ulrich_deep_dive.md) §4.3 for the drift axis.*
