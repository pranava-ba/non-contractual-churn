# Reading Order — easy → difficult

A staged path through the references behind *"Non-contractual churn with MCMC: are
Pareto/NBD purchase forecasts calibrated?"*, ordered so each item prepares you for the
next. 📄 = a PDF sitting in this `references/` folder; 🔗 = read online.

**In a hurry?** The minimum spine is: **3 → 9 → 14 → 17 → 19 → 28**
(tutorial → a friendly model → the target paper → Pareto/GGG → the MCMC sampler → proper
scoring). Everything else fills in the gaps.

---

## Level 1 — Plain-language orientation (no math)

1. **Buy Till you Die (Wikipedia)** — 🔗 https://en.wikipedia.org/wiki/Buy_Till_you_Die
   Five-minute map of the model family and vocabulary.
2. **Non-contractual customer churn (blog)** — 🔗 https://medium.com/rond-blog/non-contractual-customer-churn-f46a1cf8eec4
   Intuition for *why* silent churn is hard before any equations.
3. **Buy 'Til You Die — A Walkthrough** · McCarthy & Wadsworth (2014) — 📄 `BTYD-walkthrough.pdf`
   Hands-on vignette of the `BTYD` R package. See the models *used* end-to-end before you
   meet the theory. Skim the code, read the prose.

## Level 2 — Applied churn papers (light math, motivation)

4. **A Proposed Churn Window for Non-Contractual Purchases** · Ganeson, Lew & Razak (2022) — 📄 `Vol.12.No.04.04.pdf`
   Directly on-topic and gentle: how you even *define* churn without a contract.
5. **Churn management in hospitality** (2025) — 📄 `s40537-025-01204-8.pdf`
   An applied churn-management case study; accessible framing of the business problem.
6. **On the Profitability of Long-Life Customers in a Noncontractual Setting** · Reinartz & Kumar (2000)
   The managerial case for customer-lifetime thinking. Motivation, not method.
7. **Instant Customer Base Analysis: Managerial Heuristics Often "Get It Right"** · Wübben & von Wangenheim (2008)
   The "do we even need a model?" argument — the foil your paper answers.
8. **To model, or not to model: Forecasting for customer prioritization** · Huang (2012)
   Continues the heuristics-vs-models debate; short and readable.

## Level 3 — Foundational BTYD models (moderate — start the math here)

9. **"Counting Your Customers" the Easy Way (BG/NBD)** · Fader, Hardie & Lee (2005) — 📄 `fader_et_al_mksc_05.pdf`
   **The friendliest BTYD derivation.** Begin your mathematical reading here, not with the
   original Pareto/NBD.
10. **Customer-Base Analysis in a Discrete-Time Noncontractual Setting** · Fader & Hardie (2010) — 📄 `fader_et_al_mksc_10.pdf`
    A discrete-time cousin; consolidates the modelling style.
11. **Counting Your Customers: Who Are They and What Will They Do Next?** · Schmittlein, Morrison & Colombo (1987)
    The original **Pareto/NBD** — the model this whole repo studies. A classic, but denser
    notation; easier now that you've read (9).
12. **Empirical validation and comparison of models for customer base analysis** · Batislam, Denizel & Filiztekin (2007)
    How these models are compared on real data — the tradition your paper critiques.
13. **Forecasting Repeat Sales at CDNOW: A Case Study** · Fader & Hardie (2001)
    Background on the CDNow benchmark used in the paper.

## Level 4 — The target paper and richer models (moderate–hard)

14. **A generalised comparison of Pareto/NBD based forecasts using MCMC, maximum likelihood, and heuristics** · Simon (2025) — 📄 `s11573-025-01237-8.pdf`
    **The paper you are extending.** Read once Levels 1–3 are comfortable.
15. **Data set requirements and parameter recovery in customer base analysis** · Simon & Adler (2022)
    The small-sample parameter-recovery context for the MCMC-vs-MLE question.
16. **Modeling Purchasing Behavior with Sudden "Death"** · Bemmaor & Glady (2012)
    A flexible dropout model; a harder read.
17. **Ticking Away the Moments: Timing Regularity Helps to Better Predict Customer Activity** · Platzer & Reutterer (2016)
    The **Pareto/GGG** model behind Extension A (regular inter-purchase timing). Harder —
    Gamma renewal timing.
18. **BTYDplus** (R package manual) · Platzer (2021)
    Reference for the Abe/GGG samplers; skim as needed while reading the code.

## Level 5 — Bayesian estimation machinery (hard — methods)

19. **Counting Your Customers One by One: A Hierarchical Bayes Extension to the Pareto/NBD Model** · Abe (2009)
    The **MCMC sampler** at the heart of the Bayesian arm. Central but technical.
20. **The Calculation of Posterior Distributions by Data Augmentation** · Tanner & Wong (1987)
    The data-augmentation idea Abe relies on. Classic, technical.
21. **Slice Sampling** · Neal (2003)
    The sampler used to update the gamma shape parameters. Technical.
22. **Rank-Normalization, Folding, and Localization: An Improved R̂ for Assessing Convergence of MCMC** · Vehtari et al. (2021)
    The convergence diagnostics (R̂, ESS) in the paper's appendix.

## Level 6 — Forecast-evaluation theory (hardest — the evaluation foundation)

23. **Controlling the False Discovery Rate** · Benjamini & Hochberg (1995)
    The multiple-testing correction used throughout. Widely applied; moderate–hard.
24. **A Comparison of the Two One-Sided Tests Procedure...** · Schuirmann (1987)
    The **TOST** equivalence test that turns the MCMC≈MLE null into a positive claim.
25. **The Prequential Approach** · Dawid (1984)
    Where the calibration idea comes from. Abstract and hard.
26. **Predictive Model Assessment for Count Data** · Czado, Gneiting & Held (2009)
    The **randomized PIT** for counts — the core calibration diagnostic. Technical.
27. **Probabilistic forecasts, calibration and sharpness** · Gneiting, Balabdaoui & Raftery (2007)
    The "maximise sharpness subject to calibration" paradigm. Technical.
28. **Strictly Proper Scoring Rules, Prediction, and Estimation** · Gneiting & Raftery (2007)
    The theoretical foundation of CRPS and the log score. The most abstract — read last.

---

*Companion:* `zeroth_review_study_guide.html` in this folder is a study guide compiled
during an early review pass. Local PDFs are named as downloaded; the rest are cited in
`../paper/refs.bib`.
