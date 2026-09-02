# Review Notes: "Non-contractual churn: statistical or machine-learned?"

Working notes on required fixes and open gaps, organized by priority.

---

## 1. Critical — numerical inconsistencies to reconcile before submission

These are cases where the same model/dataset pairing reports different numbers in different tables. Even if each is individually correct (different splits, different seed counts), a referee will read them as errors unless the discrepancy is explained in the text or the tables are made consistent.

### 1.1 Table 13 vs Table 14 — Pareto/NBD timing MdAE
| Dataset | Table 13 | Table 14 | Gap |
|---|---|---|---|
| Sim-k2 | 5.33 | 9.50 | ~78% |
| Sim-k3 | 4.49 | 5.83 | ~30% |
| Grocery | 3.89 | 4.25 | ~9% |
| CDNow | 107.08 | 106.03 | ~1% |

Table 14 is described as using "a common held-out split" (for fair comparison against the ML hazard model), which plausibly explains some of the gap — but a near-doubling on Sim-k2 needs an explicit sentence, not just a methods-section difference the reader has to infer. **Action:** add a footnote to Table 14 explaining why the held-out-split evaluation shifts Pareto/NBD's own MdAE this much, or rerun Table 13's numbers on the same split so the two tables are directly comparable.

### 1.2 BTYD/Pareto-NBD PIT-KS on Dunnhumby, reported three ways
- Table 2: 0.169
- Table 7: 0.166
- Table 8 (raw): 0.164

### 1.3 BTYD/Pareto-NBD PIT-KS on Online Retail II, reported four ways
- Table 2: 0.211
- Table 4 (MCMC): 0.207
- Table 7: 0.210
- Table 8 (raw): 0.212

**Action for 1.2/1.3:** These are probably just seed-count and split differences (15 vs 10 vs 8 seeds), but the spread should either be collapsed to one canonical number per dataset with a shared seed protocol, or every table should carry error bars/CIs so a reader can see 0.164–0.169 is noise, not drift.

---

## 2. Major gaps

### 2.1 Seasonality fix is diagnosed but not solved
Section 7.12 shows the conformal repair only partially removes seasonal bias (r drops from +0.94 to +0.43, not to zero), and states that "a genuinely time-aware structural model... is the cleaner long-run fix" — but no such model is built or tested, even a minimal one (e.g., a seasonal multiplier on the Poisson rate, or per-quarter refitting evaluated properly rather than just gestured at). This is arguably the paper's single most consequential open problem, since:
- It's the *only* stress axis that breaks calibration (Section 7.12).
- It appears on real data, including one of the paper's own headline datasets (Online Retail II, Christmas peak).
**Action:** either implement a minimal seasonal extension and report its calibration, or reframe the claim more conservatively as "identified, only partially repaired" rather than implying a clean solution exists.

### 2.2 Valendin et al. (2022) RNN comparator is discussed but never run
It is repeatedly cited as the natural benchmark (raw event-stream model vs. RFM-summary models) and deferred to future work. Since the paper's central claim is partly that "RFM already carries what matters" (Section 7.6), the one model type that could most directly test that claim — a sequence model that doesn't use RFM at all — is exactly the one left out. **Action:** either run a lightweight version of it, or soften the RFM-sufficiency claim to explicitly scope it to non-sequence ML comparators.

### 2.3 Demographic-covariate null is under-powered
"RFM already carries what matters" (re: demographics) rests on 801 Dunnhumby households only — one dataset, one subsample. It's a reasonable pilot finding but is currently stated as a general conclusion (Sections 7.6, 8.2). **Action:** either qualify the claim's scope explicitly ("on the one cohort with demographic data...") or find a second dataset with covariates to replicate it.

### 2.4 Multiple-comparison correction is under-specified
Section 5 ("Significance") says Holm-Bonferroni is applied to "headline effects" but doesn't specify, table by table, which p-values were corrected and which are raw. Tables 8, 10, 11, 13, 15 all report p-values without indicating correction status per-table. **Action:** add a footnote per table stating whether the reported p-values are raw or corrected, and over what family of tests the correction was computed.

---

## 3. Moderate issues

### 3.1 Section 7.8 (top-customer identification survives interval miscalibration) is underweighted
This is a genuinely interesting counterpoint to the paper's main thesis — ranking/targeting quality is robust even where predictive intervals are badly miscalibrated (Dunnhumby, Online Retail II). Currently it's a mid-paper subsection; given it's a "when does calibration *not* matter" finding that most practitioners care about (targeting decisions), it could be promoted toward the abstract/contributions list rather than left as a secondary result.

### 3.2 Discount-rate CLV aside is a tangent
The per-customer discounted-CLV analysis at the end of Section 7.6 interrupts the calibration narrative, and tests an unusually wide annual discount rate range (10%–100%) without justifying the upper bound. **Action:** trim to 1–2 sentences in the main text and move the full analysis to an appendix, or justify the 100% figure explicitly.

### 3.3 Companion paper (Pranava and Rajeswaran 2026) — delta from phase 1
Since this is the authors' own phase-1 working paper (not a third-party source), the earlier concern about "citing an unverifiable external source" doesn't apply. The remaining issue is scope overlap: Section 7.3 re-derives the MLE-vs-MCMC equivalence result that the companion paper already established, extending it to more estimators (HMC, Laplace, amortized) and to BG/NBD. **Action:** state explicitly, in one sentence near the start of 7.3, exactly what is reused vs. newly established here, so it doesn't read as re-publishing the same finding — this is really just a framing fix, not a sourcing problem.

### 3.4 Classic non-BTYD churn literature absent from related work
Buckinx & Van den Poel-style partial-defection models and survival-model churn approaches aren't discussed. Defensible given the paper's explicit BTYD-vs-ML scope, but a reviewer coming from the general churn-prediction literature (rather than the CBA tradition specifically) may ask why classical churn-specific baselines aren't in the comparison set at all.

---

## 4. Minor / polish

- **Novelty claim**: "to our knowledge, the first to evaluate [BTYD vs ML] by calibration" (Section 2) is a strong claim; the existing hedge ("the novelty is the evaluation lens... not the existence of the comparison") should stay prominent since it pre-empts the obvious pushback — don't cut it in editing.
- **PDF/typesetting extraction artifacts** (garbled sub/superscripts like "Rb", "λˆi", stray "T ∗") — check final typeset PDF, likely just an extraction/OCR issue in the copy reviewed, not a substantive problem, but worth a proofing pass.
- **Table 12 bolding**: caption says "best hit rate per row in bold" — verify bolding actually renders correctly in the final typeset version.

---

## 5. Suggested priority order for revision

1. Reconcile the Table 13/14 timing discrepancy (Section 1.1) — highest risk of looking like an error.
2. Add per-table seed/CI clarity for the repeated PIT-KS values (Section 1.2/1.3).
3. Decide on seasonality: implement a minimal structural fix, or soften the claim (Section 2.1).
4. Scope-qualify the RFM-sufficiency and demographic-null claims (Sections 2.2, 2.3).
5. Everything in Sections 3–4 is polish-level and can be handled in a final pass.
