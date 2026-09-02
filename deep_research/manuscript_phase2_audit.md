# Audit of `manuscript_phase2_review_notes.md` against `paper/manuscript_phase2.tex`

Every review-note claim traced to source (v2.0.1, 1617 lines). Verdicts:
**✅ confirmed** · **🟡 confirmed but already (partly) addressed** · **🔶 overstated / mis-attributed** · **⬜ editorial (nothing to verify)**.

## Numbering key (resolved)

The notes' float/section numbers **do** match this file, given two facts that weren't obvious:
- **"Table 2" = `tab:counts`** (the count PIT–KS table, [paper/manuscript_phase2.tex:536](paper/manuscript_phase2.tex#L536)). It's easy to miss because the *visual* map right after it (`fig:map`) is a figure. With `tab:counts` counted, every later table number lines up: Table 4 = `tab:amortized`, Table 7 = `tab:variant`, Table 8 = `tab:conformal`, Table 13 = `tab:timing`, Table 14 = `tab:mltiming`, Table 15 = `tab:stack`.
- **"Section 7.x" = the Results subsections** (`\section{Results}` is §7). So 7.3 = `sec:estinv`, 7.6 = `sec:clv`, 7.8 = `sec:topa`, 7.12 = `sec:robust`.

## 1. Critical — numerical inconsistencies

| Item | Claim | Verdict | Source |
|---|---|---|---|
| 1.1 | Timing MdAE differs across Tables 13/14: Sim-k2 5.33 vs 9.50, Sim-k3 4.49 vs 5.83, Grocery 3.89 vs 4.25, CDNow 107.08 vs 106.03 | ✅ **all four rows confirmed** | `tab:timing` [L990–994](paper/manuscript_phase2.tex#L990); `tab:mltiming` [L1018–1022](paper/manuscript_phase2.tex#L1018) |
| 1.2 | Dunnhumby PIT–KS reported as 0.169 / 0.166 / 0.164 | ✅ confirmed (+ 0.168 in `tab:amortized`) | 0.169 [L547](paper/manuscript_phase2.tex#L547); 0.166 [L753](paper/manuscript_phase2.tex#L753); 0.164 [L790](paper/manuscript_phase2.tex#L790); 0.168 [L645](paper/manuscript_phase2.tex#L645) |
| 1.3 | Online Retail II PIT–KS reported as 0.211 / 0.207 / 0.210 / 0.212 | ✅ **all four confirmed** | 0.211 [L548](paper/manuscript_phase2.tex#L548); 0.207 [L644](paper/manuscript_phase2.tex#L644); 0.210 [L754](paper/manuscript_phase2.tex#L754); 0.212 [L791](paper/manuscript_phase2.tex#L791) |

**Refinements the audit adds:**
- **1.1** is the real issue: on the common split *both* models shift, and the **Sim-k2 anomaly is substantive, not cosmetic** — Pareto/GGG's win (4.39 < 5.33) *vanishes* (9.40 ≈ 9.50) and the ML hazard wins (9.03). A footnote is the right fix; rerunning Table 13 on the common split (as the note's alt-suggestion) would force the whole timing narrative onto the weaker numbers. **Footnote, don't rerun.**
- **1.2 / 1.3 are partly pre-addressed.** `tab:counts`'s caption ([L537](paper/manuscript_phase2.tex#L537)) already states its PIT–KS is on the 30% held-out split and "read slightly higher than … Table [amortized] … comparisons should be made within, not across, a fixed sample." That covers the *Table 2 vs Table 4* gap. What's still unexplained is the tiny **0.164 / 0.166 / 0.168** cluster across the full-cohort tables (4/7/8) — genuine seed/run noise, low severity. A one-line "canonical value per cohort" footnote or shared-seed note would close it, but this is not a submission blocker.

## 2. Major gaps

- **2.1 Seasonality — ✅ confirmed, highest-value open item.** `r=+0.94 → +0.43` (not zero) verified at [L1148](paper/manuscript_phase2.tex#L1148) and `tab:seasconf` [L1166–1168](paper/manuscript_phase2.tex#L1166); the text explicitly says a "genuinely time-aware structural model (seasonal terms in the intensity, or per-quarter refitting) is the cleaner long-run fix" [L1157–1158](paper/manuscript_phase2.tex#L1158) — **diagnosed and gestured at, not built.** Decision needed: implement a minimal seasonal-rate extension, or soften to "identified, only partially repaired."
- **2.2 Valendin RNN never run — ✅ confirmed.** Cited **3×** as the natural benchmark ([L164](paper/manuscript_phase2.tex#L164), [L215](paper/manuscript_phase2.tex#L215), [L1350](paper/manuscript_phase2.tex#L1350)) and deferred to future work ([L1350](paper/manuscript_phase2.tex#L1350)). The note's point stands: the one non-RFM sequence model that could test the RFM-sufficiency claim is the one left out. Fix = run a lightweight version, or scope the RFM claim to non-sequence comparators.
- **2.3 Demographic null on 801 households — ✅ confirmed.** [L829](paper/manuscript_phase2.tex#L829). Nuance: the manuscript already *extends* the null to the count target on the same households ([L833–835](paper/manuscript_phase2.tex#L833)), which strengthens it — but it is still **one cohort**. Scope-qualify ("on the one cohort with demographics…"). Valid.
- **2.4 Multiple-comparison correction under-specified — ✅ confirmed.** [L448–451](paper/manuscript_phase2.tex#L448): Holm–Bonferroni is asserted narratively for "headline effects" only; table captions (`tab:conformal`, `tab:timing`, `tab:stack`) report **raw** paired-Wilcoxon *p*. Per-table correction status is genuinely ambiguous. Fix = one footnote per *p*-bearing table.

## 3. Moderate

- **3.1 §7.8 (`sec:topa`) underweighted — ⬜ editorial.** Section exists ([L918](paper/manuscript_phase2.tex#L918)); promoting the "when calibration *doesn't* matter for targeting" finding toward the contributions is a fair call.
- **3.2 Discount-rate tangent (10–100%) — ✅ confirmed.** [L838–844](paper/manuscript_phase2.tex#L838): "annual rates from 10% to 100% … 2–28% reduction," ranking unchanged. It is a ~7-line aside inside `sec:clv`. Trim to appendix or justify the 100% bound.
- **3.3 Companion-paper delta in §7.3 — 🟡 mostly pre-addressed / slightly overstated.** `sec:estinv` does **not** re-derive MLE≈MCMC; it **credits `[phase1]`** for it and frames the new contribution as extension to amortized/HMC/Laplace/BG-NBD ([L625](paper/manuscript_phase2.tex#L625)). The "one sentence stating reused vs new" the note asks for essentially exists there — it could just move earlier in the subsection. Low priority.
- **3.4 Classic non-BTYD churn literature absent — ✅ confirmed.** No `Buckinx`, no `Miguéis` anywhere; "survival" appears only as an ML *timing* competitor, not as a churn baseline or the classical churn-survival tradition. **Directly closed by the reading-order additions already staged** (Buckinx & Van den Poel 2005; Miguéis et al. 2012) — add them to `refs_phase2.bib` + one related-work sentence.

## 4. Minor / polish

- **4.1 Novelty claim — 🔶 mis-attributed, and its own advice is already satisfied.** The claim is in **§1 (contributions list), [L164–167](paper/manuscript_phase2.tex#L164)** — *not* §2 as the note says. And the hedge the note wants kept ("The novelty is the evaluation lens … not the existence of a BTYD-versus-ML comparison") **already exists** at [L166–167](paper/manuscript_phase2.tex#L166). Action: fix the section ref in the notes; nothing to change in the manuscript.
- **4.2 Garbled sub/superscripts (`Rb`, `λˆi`, `T*`) — ⬜ non-issue in source.** The `.tex` uses clean `$\widehat{R}$`, `$\hat\lambda_i$`, `$T^*$`; the garbling is PDF text-extraction, exactly as the note suspects. No source change.
- **4.3 Table 12 bolding — ⬜ non-issue in source.** Table 12 = `tab:topa`; `\textbf` is applied correctly ([L947](paper/manuscript_phase2.tex#L947)). Only verify it *renders* in the compiled PDF.

## Bottom line

The review notes are **reliable** — every numeric claim checks out and the priorities in their §5 are sound. Three adjustments from the audit:
1. **Two items need no manuscript change** — 4.1 (hedge already present; wrong section cited) and 4.2 (extraction artifact).
2. **Two are lighter than stated** — 1.2/1.3 (partly covered by the `tab:counts` caption) and 3.3 (delta already credited to `[phase1]`).
3. **The real work is unchanged:** 1.1 timing footnote, 2.1 seasonality decision, 2.2 Valendin, 2.3/2.4 scope-and-correction clarity, 3.4 add the two churn citations.

### Suggested v2.0.2 fix order
1. 1.1 timing-table footnote (highest "looks-like-an-error" risk).
2. 3.4 add Buckinx & Van den Poel (2005) + Miguéis et al. (2012) to `refs_phase2.bib` + a related-work sentence (cheap, closes a real gap).
3. 2.4 per-table correction footnotes; 1.2/1.3 canonical-value note.
4. 2.1 seasonality: **decide** — minimal structural fix vs. soften the claim.
5. 2.2 / 2.3 scope-qualifications.
6. 3.1 / 3.2 editorial; fix 4.1's section ref in the notes file.
