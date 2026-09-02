---
title: "Ulrich (2026), *Dead Reckoning* — exhaustive deep-dive and comparison"
type: deep-read
created: 2026-08-11
updated: 2026-08-11
source: "Karl T. Ulrich (The Wharton School), *Dead Reckoning: Counting Your Customers Who Never Say
         Goodbye*, working draft v4, 6 Jul 2026, arXiv:2607.18623 [q-fin.GN], 39 pp. Data: an operating
         firm (MakerStock, which he co-founded) + the public CDNOW cohort. Thanks P. Fader."
purpose: A section-by-section read of the whole paper with clean notation, followed by a detailed
         compare-and-contrast with our manuscript (paper/manuscript_phase2.tex, v2.0.11): what he does,
         what is genuinely novel, how it differs from us, and how we use it to strengthen our paper.
companion: deep_dive.md §8 · corpus_critique.md §1a · [[ulrich-dead-reckoning]]
math: LaTeX ($...$ / $$...$$). No Unicode math glyphs — renders in any MathJax/KaTeX viewer (incl. GitHub).
---

# Ulrich (2026), *Dead Reckoning* — deep-dive & comparison

**Thesis in one line.** The summed "alive" customer count that BTYD dashboards report is (a) a
*category error* — an infinite-horizon quantity graded against finite-horizon outcomes — and (b)
*partially identified* — the data pin a lower bound but not the count itself. Fix: report a calibrated
finite-horizon return probability $R_H$ as the operating KPI, audit it out-of-time with reliability
diagrams on a grid of scoring-date $\times$ horizon cells, maintain it with a dynamic (loss-development)
recalibration layer, and report the count, if at all, as an *identified interval*.

---

## 0. TL;DR — Ulrich vs. our paper on one screen

| Axis | **Ulrich (2026)** | **Our paper** |
|---|---|---|
| **Question** | Is the BTYD *aliveness count* meaningful/identified, and is its probability calibrated? | Does structural BTYD or ML give better-*calibrated* customer forecasts, and why? |
| **Comparison axis** | *within* the structural family (6 BTYD specs) | **structural BTYD vs. machine learning** |
| **Targets** | churn / aliveness only ($R_H$, the count) | **counts, value, churn, timing** (all four) |
| **Central result** | the count is *partially identified*; most "miscalibration" is a horizon *category error* | calibration is governed by the shared *parametric count assumption*; invariant to estimator & variant; repairable |
| **Evaluation** | CORP reliability diagrams, Brier+decomp, AUC, aggregate bias, on an out-of-time $(v,H)$ grid | proper scoring (CRPS), randomized PIT, coverage, ECE, on a customer-split + walk-forward |
| **Data** | 1 operating firm (2 segments, 7 yrs) + CDNOW | **7 public cohorts** (1.6%–96% active) |
| **ML?** | **deliberately excluded** ("did not run the horse race … may be a feature") | **the whole point** — ML is a first-class comparator |
| **Fix offered** | dynamic loss-development recalibration layer + interval reporting | one-pass conformal recalibration + a richer structural model (Pareto/GGG) |
| **Relationship** | **complement, not competitor.** Overlap is only on the *churn* target and only "calibration matters for BTYD aliveness," where he is concurrent and we cite him. |

---

## 1. What the paper does (exhaustive)

### 1.1 The problem and the metaphor (§1)
Dead reckoning is how ships navigated between star sightings — extrapolating from the last known
position by assumed speed and heading; its defining feature is that *error is invisible from inside the
ship and accumulates until the next external fix*. The summed "number of live customers" is the same:
an extrapolated position logged as if observed.

The **key identity**, stated without machinery: in the BG/NBD family "alive" means "will purchase again
*eventually*," because dropout occurs only at a purchase. So the aliveness probability $A$ is the
finite-horizon question "will this customer order again within $H$ months?" taken to $H\to\infty$. Every
finite-$H$ member is a forecast of a verifiable event; the $H=\infty$ member is the one member of an
observable family *its own data can never fully grade*.

**Why levels (not rankings) matter (§1).** Many decisions consume probability *levels*: acquisition-
vs-retention budgets ("40,000" vs "18,000" prescribe different strategies), metrics with an
active-customer count in the denominator, customer equity / valuation weighting per-customer value by
aliveness, and breakeven winback rules that spend $c$ when (return probability $\times$ margin) $> c$
(profit-based churn targeting, Lemmens & Gupta 2020). *A score can rank customers well while overstating
levels threefold — passing a targeting audit while approving spend on customers who are gone.*

### 1.2 The three quantities and the closed form (§2.1)
For a customer with sufficient statistics $(x,t_x,T)$ at vintage $v$ (the scoring date), a fitted model
emits three things practice conflates:

- $A = P(\text{alive}\mid x,t_x,T)$ — the **aliveness probability**.
- $E[X_H]$ — **expected transactions** in the window $(v,\,v+H]$ (a count, not a probability).
- $R_H = P(X_H \ge 1)$ — the **horizon-return probability**, the *observable* one that Fader, Hardie &
  Shang (2010) recommend reporting *because* it is verifiable.

For the BG family these are linked in closed form (conditional on being alive, the purchase rate has a
Gamma posterior, and zero purchases means zero dropout opportunities):

$$R_H \;=\; A \times \left[\,1 - \left(\frac{\alpha+T}{\alpha+T+H}\right)^{\,r+x}\,\right].$$

So $R_H$ is $A$ times a purchase-timing factor in $(0,1)$, giving the structural inequality

$$\boxed{\,A \;\ge\; R_H \ \text{ always},\ \text{the wedge largest for slow buyers.}\,}$$

Summed over the base: $\sum R_H = N_H$ (expected returners within the window); $\sum A = N_\infty$ (the
"dead-reckoned customer count" dashboards report). **Dashboards treat $A$ as if it were $R_H$**, which
*overstates activity by construction, before any question of misspecification arises*.

### 1.3 The limit and partial identification (§2.2, Appendix A1)
Because a BG-family customer alive at $v$ returns with probability one given unlimited time,

$$A = \lim_{H\to\infty} R_H, \qquad N_\infty = \lim_{H\to\infty} N_H.$$

(For the **Pareto/NBD**, death can occur *between* purchases, so the limit sits strictly below $A$ and
$A$ upper-bounds every observable member — the results hold *a fortiori*.)

**Formal proposition (Appendix A1, BG family).** With $a_j\in\{0,1\}$ = customer $j$ alive at $v$,
$Y_j(W)\in\{0,1\}$ = at least one purchase in $(v,v+W]$, estimand $N^{*}=\sum_j a_j$ (realized alive
count), and model report $\hat N_\infty=\sum_j \hat A_j$:

1. **Limit identity:** $a_j = \lim_{W\to\infty} Y_j(W)$ a.s.
2. **Accumulating lower bound:** $L_v(W)=\sum_j Y_j(W) \le N^{*}$ a.s., nondecreasing in $W$, and
   $\to N^{*}$ as $W\to\infty$. The count is point-identified only at $W=\infty$.
3. **Sharp nonparametric bounds:** absent restrictions on the purchase-rate distribution, the identified
   set for $N^{*}$ given data through $v+W$ is $\big[L_v(W),\,n\big]$. *Sketch:* augment the population
   with alive-but-arbitrarily-slow customers ($\lambda\to 0^{+}$); each contributes one unit to $N^{*}$
   yet is observationally indistinguishable from a dead customer on any finite window.
4. **Convention dependence:** a parametric mixing family restricts the set only through its *tail*
   assumptions. When the log-likelihood is nearly flat along a direction $u$ that moves tail mass
   (empirically true, §4.3/§4.8), structure, prior, or the numerical penalty select the point *the data
   cannot audit*. The vocabulary is Manski's (2003); **the application to latent-attrition counts is new.**

**Practical remark (A1).** The upper bound $n$ is informative only with a maintained assumption bounding
living customers' return rate away from zero (a "saturation horizon"). Adopting one converts the interval
to $\big[L_v(W),\ L_v(W)/q(W)\big]$, where $q(W)$ is the assumed minimum probability a living customer
returns within $W$. *The assumption, not the data, supplies the upper bound — and should be stated.*
Human/firm lifespans bound "eventually" in practice, so the count is *unanswerable on managerial
timescales*, not metaphysically.

**The identification intuition (§1.1).** A transaction record reveals, to a close approximation, the
*product* of two things — how many are alive $\times$ how fast the living buy. "300 living buying at rate
4 and 200 living buying at rate 6 both generate 1,200 purchases, near-identical histories, nearly the
same likelihood." Recency loosens the tie but does not break it. Abe's (2009) simulations recover
purchase rates at correlation $0.80$ with truth but dropout rates at $0.18$; Jerath, Fader & Hardie
(2011) showed near-identical fits imply dramatically different death quantities — "fit is not sufficient
to judge the suitability of a model for inferential purposes."

### 1.4 Choosing the horizon (§2.3)
Anchoring on $R_H$ requires a horizon, trading coverage against verification latency (validating an
$H$-month forecast needs vintages at least $H$ months old). On his panel $H=18$ captures 75% of the
customers who return by month 60. **The calibration target, the validation grid, and the KPI must use
the same $H$.** Seasonality on the *fitting* side "remains an omitted covariate for every model in the
comparison" — a reason to grade *deployed* forecasts with an audit agnostic to what the model omits.

### 1.5 The audit and its discipline (§3.1, Appendix A2)
For each fully-observed cell $(v,H)$: fit the model on transactions *through $v$ only*, compute native
$R_H$ for every customer, record outcomes on $(v,v+H]$, and grade with the **CORP isotonic reliability
diagram + consistency bands (Dimitriadis, Gneiting & Jordan 2021)**, aggregate bias $B$ (predicted /
realized returners), the Brier score with its **Murphy (1973) decomposition**, and AUC. Under correct
specification, true parameters, and a stable environment, forecasts are calibrated at every cell (his
simulations verify the machinery passes when nothing is wrong), so a failure *rejects the joint
hypothesis* (classical goodness-of-fit, Cox 1958 → Andrews 1988). Three properties discipline the test:

1. **Power only out of time** — estimation approximately enforces calibration on the training window.
2. **Nearly powerless against the tail** — observationally-equivalent specs share finite-horizon
   forecasts; only deep-horizon grid members, where realized returners accumulate against each model's
   asymptote, discipline the tail.
3. **Within one cell, structural error and regime change are confounded** — a single calibration/holdout
   split (the field's convention) sees one number and cannot decompose it, "which is how a misspecified
   model with compensating bias gets crowned." The *grid* separates the components by their signatures.

Inference is vintage-level: a moving-block bootstrap over the quarterly cell-bias series; incompletely
observed windows are excluded.

### 1.6 Remedies, and what each is worth (§3.2)
A theme runs through: *every remedy disciplines observable members of the family; none rescues the count,
which stays interval-identified.*
- **The category fix (free).** Report $R_H$ at a stated horizon instead of $A$. No new estimation;
  accounts for most of the headline discrepancy (§4.2).
- **Respecification** repairs structural signatures only (e.g. plain BG/NBD's forced $P(\text{alive})=1$
  for one-time buyers gives inverted+inflated scores, AUC 0.32). Beyond such clear cases the equivalence
  class binds — the hard-core-spike spec and the MBG/NBD fit near-identically, profile likelihood over
  the spike share is nearly flat, and the shared ML tail is falsified by the five-year audit anyway.
- **The dynamic layer** (§1.1, §4.7). A loss-development recalibration: acquisition cohorts mature along
  a *stable shape* while differing in *level*; estimate the shape from pooled history and the level from
  the freshest partially-observed cohorts. Causal cousin: surrogate-index targeting (Huang & Ascarza
  2024). It repairs a failure mode static maps have (worse than no correction when trained on a distorted
  vintage), is best in drift quarters, and emits a **drift statistic $D$** that flagged a regime change
  two quarters before full-horizon validation could.

### 1.7 Empirical evidence (§4) — the numbers, in full

| # | Result | Numbers |
|--:|---|---|
| §4.2 | **Category error** (2024 consumer vintage: 31,683 custs, 2,319 realized 18-mo returners) | summed $A$ overshoots realized returners **2.25$\times$** (MBG/NBD; CI 2.17–2.33) and **11.99$\times$** (BG/NBD; ranking *inverted*, AUC 0.32). The *same* MBG/NBD's own 18-mo $R_H$ forecast: off **1.18$\times$** (1.14–1.22), ECE 0.013, AUC 0.80. Two outputs of one fitted object. |
| §4.3 | **The dial** — auditable band vs. unidentified count (six specs: BG/NBD, MBG/NBD, hard-core spike, Pareto/NBD, Jerath-Fader-Hardie PDO, + MBG/NBD at software-default ridge $\rho=0.01$) | $N_{18}\in[2433,\,3047]$, AUC 0.79–0.81 **for all six** (everything the data can grade agrees); $N_\infty\in[3654,\,27734]$ — a **7.6$\times$ span, entirely in the unidentifiable count.** The ridge alone moves $N_\infty$ from 3,660 → 5,211 (**+42%**). |
| §4.4 | **Five-year audit** (June-2021 vintage, 2,967 custs, 60 mo) | realized cumulative returners 313 (18-mo) → 419 (60-mo, *still rising*). ML tail (MBG/NBD 213, spike 207) **crossed from below within 30 months → the ML count is falsified by the firm's own data.** BG/NBD's 2,711 absurd; Pareto/NBD 876 and PDO 1,089 unfalsified; penalized production 474 tracks closely — "an accident of where the penalty landed." Identified set: bounded below by 419 and rising, ML point refuted, 2,711 excluded. |
| §4.5 | **Drift & the impostor** | native-forecast bias rises with vintage recency for every spec (MBG/NBD 1.00, 1.10, 1.18 across 2022–24), so drift is environment/composition, not structure. **Impostor:** the best-calibrated 2024 forecasts belong to the spike & Pareto/NBD (1.05$\times$, 1.08$\times$) — the *same spike the five-year audit refutes*; its structural harshness cancels the contemporaneous softening. *A single-cell validation selects the refuted model.* |
| §4.6 | **CDNOW replication** (full master cohort, 23,570 custs, 69,659 txns) | count spread **8,446 → 19,981 (2.4$\times$)** on identical AUC; software default worth **22%**. |
| §4.7 | **The payoff** (>200,000 out-of-time forecast-outcome pairs) | dynamically-calibrated $R_H$: 12-mo bias 1.06$\times$/ECE 0.004; 18-mo 1.05$\times$/0.007; 24-mo 1.00$\times$/0.018 — on the diagonal at every auditable horizon, through regime changes, using only information available at each date. The grey "aliveness-as-activity" line drifts 2$\times$+. |
| §4.8 | **Mechanism (known-truth sims)** | audit passes when nothing's wrong (recovers 2,573 vs true 2,584, calibrated decile-by-decile); a genuine 0.6 spike is absorbed by the smooth model at a log-likelihood cost of **0.003 per obs** (profile ~flat); refitting at $\rho=0.01$ moves the count **+53% above known truth while leaving every observable forecast unchanged to rounding.** |

### 1.8 The managerial operating system (§5)
Three instruments for three questions. **Detection:** the reliability diagram on the newest fully-
observed vintage (standing health check) + the drift statistic $D$ (between-audit alarm).
**Decomposition:** the cohort triangle separates a macro "world" shift (moves all cohorts off their own
development curve at once) from a composition "mix" shift (entering-cohort level changes against stable
shapes). **Attribution:** interventions have *no observational answer* — a winback rule is a breakeven on
the *level*; an unrandomized rollout destroys the audit (assignment by score removes the variation
identification needs and bakes the treatment into the next recalibration). Fix = a randomized 15–20%
holdout stratified by score decile; the dashboard grows to three dials: environment, mix, efficacy.
Boundary (Ascarza 2018; Ascarza, Iyengar & Schleicher 2016; Huang & Ascarza 2024): a calibrated return
probability identifies *who is likely to return*, not *who returns because of intervention*.
Disclosure-grade: extends CBCV (McCarthy & Fader 2018) discipline to the count — "an acquirer and a
seller can currently both be right about 'how many customers' to within a factor of several."

---

## 2. What is genuinely novel in Ulrich (his stated contributions, §6)

**Conceptual (the load-bearing one).** Identify $P(\text{alive})$ as the *infinite-horizon limit of an
observable forecast family* (exact for BG, an upper bound for Pareto/NBD) and prove the implied customer
count is *partially identified* — bounded below by an accumulating observable, selected inside the bounds
by conventions the data cannot audit. *Applying Manski-style partial identification to latent-attrition
counts is, to his knowledge, new.*

**Methodological.** Reframe the model's own $R_H$ as an auditable forecast and grade it *out of time on a
$(v,H)$ grid* rather than a single split — surfacing (i) the category error, (ii) the impostor problem
(single-split validation can crown a refuted model), and (iii) a **dynamic loss-development recalibration
layer** with a drift alarm.

**Empirical.** Measure the consequences in a live firm and replicate on CDNOW: a **7.6$\times$** (2.4$\times$
on CDNOW) count spread across observationally-interchangeable specs; **42%** (22%) count movement from a
software default alone; **falsification of the ML count by five years of patience**; and a category error
that accounts for most of what practice calls "miscalibration."

**What he is careful *not* to claim as new.** "The category error is known in principle; the contribution
here is to measure its magnitude and document it in the wild." The most direct antecedent is Fader, Hardie
& Shang (2010) — P(alive) "is a prediction of something that is, by definition, unobservable," "alive"
(a latent state) must not be conflated with "active" (observable behavior), and the *conditional
penetration* (discrete-time $R_H$) is the observable companion. Wünderlich (2015) had the same instinct in
HB. Ulrich's addition is *taking those warnings to their conclusion*: the identification result, the
audit, the maintenance layer — plus the documentation that practice adopted the P(alive) output while
shelving the accompanying advice.

---

## 3. How it differs from our paper (compare & contrast)

The two papers share a diagnosis vocabulary (finite- vs infinite-horizon; calibration of a probability
forecast) and one tool (CORP reliability diagrams) but answer *different questions on different objects*.

### 3.1 Different question, different axis
- **Ulrich audits *one* construct within *one* paradigm.** He keeps the structural BTYD model and asks
  whether its *aliveness* output is a meaningful, identified, calibrated number. His comparison set is six
  *structural* specifications; the "winner" question is which structural spec to trust and how to maintain
  it.
- **We compare *two paradigms* across *four targets*.** We ask whether structural BTYD or machine learning
  produces better-*calibrated* forecasts of counts, value, churn, *and* timing — and we localize the
  answer to a single mechanism (the shared parametric count assumption). Our "winner" is a *decision rule*
  (which model class, when), not a maintenance protocol for one model.

### 3.2 He deliberately excludes ML — which is precisely our territory
His §6 Limitation 4, verbatim in spirit: *"We did not run the horse race against discriminative machine
learning, because our claims concern auditing structurally interpreted models rather than ranking
predictors; the audit is model-agnostic and would grade a boosted challenger identically, and the
challenger reports no alive count at all (Valendin et al. 2022), which under this paper's findings may be
a feature."* And in §1.2 he brackets the ML-CLV stream as evaluating **by discrimination** (AUC), not
calibration (Martínez 2020; Neslin 2006; the exception being Chamberlain 2017, who recalibrates), adding
that *"redefining the target dissolves the latent aliveness construct rather than auditing it."*

That boundary is the hinge:
- **He audits the latent construct.** We are exactly the ML horse race he declines — but on *calibration*
  ground, not discrimination. We do not try to audit his latent aliveness; we compare structural and ML
  forecasts of *observable* finite-horizon quantities by proper scoring and PIT.
- His remark that ML "reports no alive count at all" is, for us, not a defect but a *design choice*: we
  never need the unidentified count because we forecast the observable target directly. Our churn target
  $P(x^{*}>0)$ **is** his identified $R_H$.

### 3.3 Different objects, methods, data (summary)

| | **Ulrich** | **Ours** |
|---|---|---|
| Object graded | the model's native $R_H$ (and the count $N_\infty$) | the full predictive distribution of counts/value/churn/timing |
| Split | out-of-time $(v,H)$ grid, one firm's calendar | out-of-sample *customer* split + walk-forward cut-points |
| Metrics | CORP reliability, Brier+Murphy, AUC, aggregate bias | CRPS (proper score), **randomized PIT** for counts (Czado 2009), coverage, ECE, PIT–KS with a parametric-bootstrap null |
| Non-stationarity fix | dynamic loss-development layer + drift alarm $D$ | per-window conformal recalibration; a structural seasonal term where a calendar cycle dominates |
| Identification stance | the *count* is set-identified (his core theorem) | calibration is *governed* by the count assumption (our core mechanism); we cite his identification, never claim it |
| Scope of generality | mechanism, verified in sim + CDNOW; magnitudes idiosyncratic to one firm | seven public cohorts spanning a 50$\times$ activity range, all replicable |

### 3.4 Where they touch (the only overlap)
On the **churn/aliveness target**, both say "the calibration of a BTYD probability forecast matters, and
you must use the finite-horizon version." He is concurrent and independent; his novelty sentence is "no
prior work scores the probability calibration of BTYD-implied aliveness quantities." Our §1 claim is
scoped to *BTYD-vs-ML by calibration across all four targets*, which he does not attempt — so the claims
coexist. We cite him at the churn target and give the category error its name.

### 3.5 Convergent findings (independent corroboration — a strength, not a clash)
1. **Finite-horizon is the right target.** His $A=\lim_H R_H$ identity is the formal version of our
   manuscript's own line that P(alive) and $P(x^{*}>0)$ "coincide only as the horizon grows."
2. **Static recalibration fails under drift.** His "a frozen map is a bet the past persists" is our
   frozen-warp result ($r$ stays $0.94$; per-window conformal flattens it).
3. **Single-split validation misleads.** His "impostor" (a single cell crowns a refuted model) is the
   theory-side twin of our walk-forward robustness (rolling cut-points, not one split).
4. **Same reliability-diagram tool.** We independently adopted CORP (Dimitriadis–Gneiting–Jordan 2021) for
   `fig:reliability`; it is his audit's core instrument.

---

## 4. How we use it to improve our paper

### 4.1 Already folded in (v2.0.3 → v2.0.11, five cite sites)
| Site | Use |
|---|---|
| §1 "first" claim | one clause scoping our novelty to the ML comparison + value/timing reach (he is BTYD-only, aliveness-only) |
| Related Work | introduce him as the most recent BTYD development; forward-pointer to §churn |
| §churn (category error) | our $P(x^{*}>0)$ = his identified $R_H$; name the "category error"; state we sit on its correct side |
| §churn (partial ID) | acknowledge the count is set-identified (his result, attributed to him); interval reporting = future work |
| §churn (identified band) | our finite-horizon target sits on the *well-identified* part of the model, where his §4.3 dial shows all specs agree even as the count spans 7.6$\times$ |
| §churn (`fig:reliability`) | our CORP reliability diagrams use the *same* standard he adopts |
| §robust (drift) | per-window conformal = lightweight cousin of his dynamic layer; frozen warp = his "bet the past persists" |

### 4.2 Defensive positioning it hands us
His Limitation 4 is our opening paragraph in miniature: *he did not run the ML horse race; we did.* If a
referee raises Ulrich as prior art, the reply writes itself — he audits one structural construct on one
firm; we compare two paradigms on calibration across four targets and seven public cohorts, and he
explicitly declines the comparison we make.

### 4.3 Concrete future extensions his work licenses (map, not required now)
1. **Report the aliveness count as an identified interval** $[L_v(W),\,L_v(W)/q(W)]$ with a stated
   saturation assumption — a clean, honest upgrade to any place we (or a practitioner) would report a
   single alive count.
2. **Adopt the out-of-time $(v,H)$ grid** as a validation standard beside our customer-split — our
   walk-forward is a partial version; a full vintage $\times$ horizon grid would strengthen the timing and
   churn evaluations and directly guard against the impostor.
3. **A dynamic loss-development recalibration layer** as a richer non-stationarity fix than per-window
   conformal, for cohorts where a stable cohort *shape* holds — with his drift statistic $D$ as a
   deployable alarm. (Our seasonality §robust already gestures at this; his layer is the heavier cousin.)
4. **Murphy-decompose our Brier scores** on the churn target (reliability + resolution) to match his audit
   granularity — cheap, and it separates calibration from discrimination explicitly.

---

## 5. Verdict

**Complement, not competitor — reinforced by the full read.** The two papers are near-orthogonal:
Ulrich goes *deep* on one target (aliveness), one paradigm (structural BTYD), one firm, with a formal
identification theorem and a maintenance protocol; we go *broad* across four targets, two paradigms,
seven public cohorts, with a single-mechanism diagnosis and two repairs. He hands us (i) the identity that
justifies our finite-horizon target, (ii) the citation for why churn calibration matters, (iii) the same
evaluation instrument, (iv) an out-of-time validation argument our walk-forward already embodies, and
(v) — in his own Limitation 4 — the explicit statement that the ML comparison we make is the one he did
not. There is no residual scoop risk; the overlap is a single, properly-cited, concurrent point on the
churn target.

---
*Companion to [`deep_dive.md`](deep_dive.md) §8, [`corpus_critique.md`](corpus_critique.md) §1a, and
[[ulrich-dead-reckoning]]. Notation is standard LaTeX; every empirical number is quoted from Ulrich
(2026) v4 with its section.*
