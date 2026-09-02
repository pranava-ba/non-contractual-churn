# Plain-English Q&A — Explaining the Project & PPT

*A cheat sheet for talking through "Non-Contractual Churn: Are Customer-Purchase Forecasts
Calibrated?" to someone who isn't a statistics person. Every answer is written for a smart
non-expert. Jargon is defined the moment it appears. Part 8 explains every chart on the slides.*

---

## The whole thing in 30 seconds

Businesses use math models to predict customer behaviour — will this shopper come back, how
often, how much will they spend. Those models spit out a single number, and everyone trusts it.
**We asked two questions nobody had checked:** (1) when the model says "I'm 95% sure," is it
*actually* right 95% of the time (is its confidence honest)? and (2) do the fancy
machine-learning models really do this better than the classic statistical ones? We built a fair
test, ran it on 7 real datasets, found *exactly* where the honesty breaks and *why*, and offered
two fixes.

**One sentence to memorize:** *"Popular customer-churn forecasts are often over-confident, we
found the single reason why, and we fixed it two ways."*

---

## The story in six beats (the arc of the whole talk)

If you can tell this as a story, the slides explain themselves:

1. **The world.** In shops and e-commerce, customers leave *silently* — you never see them quit.
2. **The tool.** For 40 years, "Buy-Till-You-Die" models have guessed who's still alive and what
   they'll buy. Everyone trusts the single number they produce.
3. **The blind spot.** Nobody ever checked whether the *confidence* around that number is honest —
   only whether the number was close. And nobody checked whether modern machine-learning does it
   better.
4. **The test.** We built one fair "calibration lens" and ran both model families through it, on
   7 real datasets, across all four things a business forecasts (counts, value, churn, timing).
5. **The finding.** Honesty is decided by *one shared assumption* about how people buy — not by how
   clever the model is, how you fit it, or which family member you pick. When real data breaks that
   assumption, the forecasts get over-confident.
6. **The fix.** Two repairs: a cheap universal patch (conformal recalibration) and a better-fitting
   model for regular buyers (Pareto/GGG). Both work.

---

## Part 1 — The setting and the models

### What does "non-contractual" mean? (the frame for everything)
There are two kinds of customer relationships. **Contractual** = you can *see* people leave — a
gym membership or Netflix, where quitting is an event you observe. **Non-contractual** = retail,
groceries, e-commerce — customers just *stop showing up*. Nobody cancels; they go quiet. The hard
part is that you never actually see a customer quit — you have to *infer* it from the gaps in
their purchases. Everything in this project lives in that "silent churn" world.

### Why is this problem hard? Why not just look?
Because "stopped buying" and "hasn't bought *yet*" look identical in the data. A customer who
hasn't purchased in three months might be gone forever — or might just be a slow, loyal shopper
who buys every four months. You can't tell them apart by eye. The whole point of the models is to
weigh "how quiet is too quiet?" for each individual, given their personal buying rhythm.

### What is "Pareto"?
Here "Pareto" is **not** the 80/20 rule — it's the name of a probability curve. In the model it
describes **how long a customer stays active before silently quitting.** Its shape captures a
real pattern: lots of customers drift away early, while a few stick around for a very long time.
Each customer has their own hidden "lifetime," and the Pareto curve describes how those lifetimes
are spread across the whole customer base. **Pareto = the "when do they quit?" part of the model.**

### What is NBD?
**NBD = Negative Binomial Distribution.** It's the part of the model that describes **how often
customers buy while they're still active.** "Negative binomial" is just a flexible counting rule
that allows for the fact that some people buy constantly and others buy rarely — the buying rate
varies from person to person. **NBD = the "how often do they buy?" part.**

So **Pareto/NBD** = one model that stitches these together: *how often people buy* (NBD) and *when
they silently churn* (Pareto).

### What is a "Poisson" process? (you'll be asked, because it's the heart of the finding)
**Poisson** is the simplest possible rule for random arrivals: events happen at some steady average
rate, independently, with no memory of each other — like raindrops on a roof, or calls to a call
centre. In these models, each active customer is assumed to buy like raindrops fall: at their own
steady average rate, at completely random moments. It's a clean, convenient assumption — and, as
we'll see, it's *the* assumption that makes or breaks calibration. Real shoppers who buy in
predictable rhythms, or in bulk, or in seasonal waves, don't behave like raindrops.

### What is BTYD?
**BTYD = "Buy Till You Die."** It's the family name for this whole class of models. The story:
a customer keeps buying at their own pace ("buy") until, at some unseen moment, they lose interest
for good ("die") — and you're never told when the "death" happened. Pareto/NBD is the classic
BTYD model. ("Die" is just jargon for "churned.")

### How do you classify a customer as alive vs dead?
You never observe it — that's the whole challenge — so the model reasons like a detective from the
purchase record. Two clues do the work: **how often** someone used to buy (frequency) and **how
long ago** their last purchase was (recency), judged against **how long you've watched them**.

- A customer who bought *often* and *recently* → probably still alive.
- A customer who *used to* buy a lot but has gone *quiet for a long time* → probably gone.
- A customer who only ever bought once, a while ago → genuinely ambiguous.

The model turns these clues into a **probability, "P(alive)"** — e.g. *"82% chance this customer
is still active."* It's not a yes/no stamp but a degree of belief. The clever part: a two-month
silence means very different things for a weekly buyer (alarming) versus a twice-a-year buyer
(normal), and the model accounts for each customer's own rhythm.

### What is CLV?
**CLV = Customer Lifetime Value:** the total money you expect a customer to spend over their whole
remaining relationship with you. It's built from three guesses — **how long** they'll stay
(churn), **how often** they'll buy (counts), and **how much** per purchase (value). It's the
number marketing teams use to decide who's worth keeping.

### What are targeting and retention?
These are the business decisions the forecasts feed:
- **Targeting** — deciding *which* customers to spend marketing money on (e.g. the most valuable 10%).
- **Retention** — spending to *keep* existing customers from leaving (discounts, win-back emails, loyalty perks).

Both depend on trustworthy forecasts: mis-rank your customers or misjudge who's about to churn,
and you pour budget on the wrong people. And note — a forecast can be good enough to *rank*
customers yet still be over-confident about the *numbers*, which is exactly the gap we probe.

### The "Problem" statement, decoded
> *"Models are trusted for point predictions — but is the uncertainty they report trustworthy,
> and do ML models do better?"*

Two doubts in one sentence:
1. **The uncertainty doubt.** Businesses use a single number ("this customer will buy 4 times") —
   that's a *point prediction*. A good forecast should also say how sure it is ("4, give or take
   2"). Nobody had checked whether that stated confidence is *honest*.
2. **The ML doubt.** Everyone assumes flashy machine-learning models beat the old statistical
   ones. Has anyone actually *verified* that — especially on this honesty question? No. So we did.

---

## Part 2 — Forecasts and calibration (the core idea)

### What is a forecast?
A statement about the future built from past data. Here: predicting each customer's future
purchases — how many, how much, whether they'll still be around, and when.

### What is a *point prediction*?
The single best-guess number — "this customer will buy 4 times." It's what almost everyone reports
and what almost everyone has always been graded on. It throws away all information about how *sure*
the model is.

### What is a *predictive distribution*?
Instead of one number, a good model can output a **whole range of possibilities, each with a
probability**: *"most likely 3 purchases, but 2 or 4 are quite possible, and 0 or 8 are unlikely."*
That spread-of-outcomes-with-probabilities is the **predictive distribution.**
- **Point prediction** = the single best guess (the peak or average).
- **Predictive distribution** = the full picture, including how uncertain the model is.

Everything about calibration is about whether that *full picture* is honest — not just whether the
single best guess was close.

### What is a *calibrated* forecast? (the heart of the project)
**Calibration = the forecast's confidence matches reality.** The best analogy is a weather
forecaster. Look at every day they said *"70% chance of rain."* If it actually rained on about
70% of those days, they're **calibrated** — their confidence is honest. If it rained only 40% of
the time, they were **over-confident** — miscalibrated.

For our customer model: when it says *"95% sure this customer buys between 2 and 6 times,"* that
should come true about 95% of the time.

**Accuracy vs calibration** (the single most important distinction in the talk):
- **Accuracy** = "was the single guess close to the truth?"
- **Calibration** = "was the model's *confidence* honest?"

A model can be accurate on average yet badly over-confident — which is exactly why we measure
calibration *separately*. Imagine a doctor who is right on average but says "definitely fine" to
patients who turn out sick: accurate-ish, dangerously over-confident. That's the failure mode we
hunt.

### A tiny worked example of miscalibration
Say the model gives 100 customers each a "90% confident: they'll buy between 1 and 5 times" range.
If the model is honest, the truth should land inside that range for about **90** of them. If it
only lands inside for **70**, the model's ranges are too narrow — it's over-confident, and its "90%"
really means "70%." Nothing about the average guess tells you this; you only see it by checking the
ranges. That check is what the whole project industrialises.

### What is over-dispersion / under-dispersion? (the shape of the error)
**Dispersion** just means "spread." A forecast is **under-dispersed** when its ranges are too
*narrow* — it's too confident, reality keeps landing outside (the common failure here). It's
**over-dispersed** when ranges are too *wide* — needlessly wishy-washy. Good calibration is the
Goldilocks middle: ranges exactly as wide as the uncertainty warrants.

### What is zero-inflation, and why does it matter here?
Most customers in retail buy **zero** times in the future window — they never come back. So the
outcome data has a giant spike at zero. That spike can *hide* miscalibration: if you grade a model
on everybody, it looks great simply because "predict roughly zero" is right most of the time. This
is why the project is careful to also look at the customers who *do* come back (the "active"
subgroup), where the real test of the forecast lives. (It's also why one ML value model is called
**zero-inflated** — see ZILN in Part 5.)

### What is a *calibration check*?
Simply running the tests below on a model to see whether its stated uncertainty can be trusted.
The punchline of our literature review: for 40 years the field ran *accuracy* checks but almost
never a *calibration* check.

### What is a "proper scoring rule"?
A **scoring rule** grades a probabilistic forecast against what actually happened. It's called
**proper** if the only way to get your best possible score is to *report your true beliefs* —
you can't game it by exaggerating or hedging. That honesty guarantee is why proper scoring rules
(like CRPS below) are the gold standard in weather and energy forecasting, and why we bring them
to customer forecasting.

### The "calibration lens": CRPS, PIT, coverage
We call our three-part test the **calibration lens** — because it's a way of *looking* at any
model, statistical or ML, so every contestant is judged identically. The three parts:

**CRPS** *(Continuous Ranked Probability Score)* — a single **overall grade** for a whole
predictive distribution against what actually happened. It rewards putting high probability near
the true outcome *and* being confident (narrow) when the model can afford to be. **Lower = better.**
It's a *proper* scoring rule — you can't cheat it. Think of it as "how close was the *whole
distribution* to reality," not just the average.

**PIT** *(Probability Integral Transform)* — the **diagnostic that shows *how* a model is wrong.**
For each customer, ask: *"where did the real outcome land inside the model's predicted range —
low, middle, high?"* If the model is honest, outcomes should land **all over the range evenly**.
Collect these positions across all customers into a histogram: an honest model gives a **flat**
histogram. A **U-shape** (piled up at both ends) means the model's ranges are too narrow — reality
keeps surprising it (**under-dispersed / over-confident**). A hump in the middle means ranges too
wide.

**PIT-KS** — *how we turn that picture into one number.* We measure how far the PIT histogram is
from perfectly flat using a standard yardstick (the Kolmogorov–Smirnov distance). **PIT-KS = 0
means perfectly calibrated; bigger = more miscalibrated.** Almost every bar chart in the deck puts
**PIT-KS on the vertical axis, so shorter bars are better.** Memorize that one sentence and the
charts read themselves.

**Coverage** — checks the confidence intervals directly. If the model gives a **"95% interval"**
per customer, the truth should fall inside it about **95%** of the time across all customers. Only
80%? Intervals too narrow (over-confident). 99%? Too wide. **"95% should mean 95%."**

Together, CRPS + PIT + coverage tell you whether the *whole* forecast — not just its center — can
be trusted.

---

## Part 3 — Benchmarking (the comparison)

### What is benchmarking?
Putting different methods through the **exact same test, on the same data, judged by the same
yardstick**, so the comparison is fair. Here the yardstick is the calibration lens, and the
contestants are **classic statistical BTYD models vs machine-learning models.**

### What makes the comparison *fair*? (three safeguards)
1. **Same data, same split.** Every model sees the identical training window and is graded on the
   identical hidden future (see "rolling cut-point" in Part 4).
2. **Same yardstick.** Every model — statistical or ML — goes through the identical CRPS / PIT /
   coverage lens. No model gets a home-field metric.
3. **Real statistics, not eyeballing.** Earlier work compared methods by *looking at boxplots*. We
   run proper significance tests (see below) so "better" means *provably* better, not "looks
   better."

### What is a significance test (and TOST / equivalence)?
A **significance test** asks: "is this difference real, or could it be luck?" If two methods score
differently, a test (we use the **Wilcoxon** signed-rank test) tells you whether that gap would
survive re-running the experiment. The **p-value** is the "probability it's just luck" — small
means the difference is real.

**TOST (equivalence testing)** flips the question. Normally a test can only *fail to find* a
difference — which isn't the same as proving two things are *the same*. TOST is designed to
positively demonstrate **"these two are, for practical purposes, equivalent."** We use it to make
the strong claim that MCMC and MLE (two ways of fitting) give *the same* calibration — not merely
"we couldn't tell them apart."

### "Benchmark statistical BTYD vs machine-learning across counts, value, churn, timing"
This is our second objective. Run both model families side by side and grade them with the
calibration lens on the four questions a business actually cares about. **The novelty:** every
past comparison asked *"which is more accurate?"* — we're the first to ask *"which is better
calibrated?"*

### What are the four dimensions — counts, value, churn, timing?
The four things you might forecast about a customer:

| Dimension | The question | In one word | Graded with |
|---|---|---|---|
| **Counts** | *How many* times will they buy? | how many | CRPS · PIT · coverage |
| **Value**  | *How much* money will they spend? (feeds CLV) | how much | CRPS · PIT · coverage |
| **Churn**  | Are they *still active* / will they buy at all? (P(alive)) | still here? | Brier · ECE |
| **Timing** | *When* is the next purchase? | when | timing error · CRPS |

We check calibration on **all four**, because a model can behave well on one and be broken on
another. (Brier and ECE are the churn-specific calibration scores — see Part 8.)

---

## Part 4 — The data and how it's prepared

### What is a "transaction event log (7 cohorts)"?
A **transaction event log** is the raw data: **one row per purchase** — who bought, when (and how
much). It's the ground truth every model starts from. A **cohort** here just means one dataset /
one group of customers from one business. We use **7 cohorts** —
**Simulated, CDNow, Online Retail II, Grocery, Olist, Dunnhumby, and Ta-Feng** — deliberately
very different businesses, with the share of still-active customers ranging from **1.6% to 96%**.
Using 7 diverse cohorts is what makes a finding *general* rather than a fluke of one dataset.

| Cohort | What it is | Character |
|---|---|---|
| Simulated | Data we generated ourselves | The "clean lab" — obeys the model's assumptions perfectly |
| CDNow | Late-90s online music store | The classic BTYD benchmark; sparse |
| Grocery | Repeat grocery purchases | Regular, well-behaved buying |
| Online Retail II | UK gift retailer | Dense, bulk buying — the hardest case |
| Olist | Brazilian marketplace | Almost everyone buys once (1.6% active) |
| Dunnhumby | US grocery (+ demographics) | Dense; lets us test whether demographics help |
| Ta-Feng | Taiwan grocery, ~4 months | Short window, seasonal |

The **Simulated** cohort is a deliberate control: because we built it to obey the model's rules, a
well-behaved model *must* be calibrated on it — and it is. When the same model breaks on Online
Retail II or Dunnhumby, we know the problem is *those data don't obey the assumption*, not a bug.

### What is an "RFM summary" — Recency, Frequency, T?
Models don't read the giant raw log directly; they **compress each customer into a tiny summary.**
**RFM:**
- **R — Recency:** when their last purchase was (how long ago).
- **F — Frequency:** how many repeat purchases they made.
- **T:** how long you've been *observing* that customer (the window since their first purchase).

Those three numbers are essentially all a Pareto/NBD needs to forecast a customer. (For *value*/CLV
you add **M — Monetary**, the average spend, making it "RFM" in the fuller sense.)

### What is a "per-customer RFM summary"?
The table you get *after* preprocessing: **one row per customer** holding their R, F, T (and M for
value). Millions of raw purchase rows get collapsed into this compact table — and *that* table is
what every model is trained and scored on.

### What is "hold-out split by rolling cut-point"?
To test a forecast honestly, you must predict a future you haven't peeked at. So you pick a
**cut-point in time:** everything *before* it is used to fit the model; everything *after* it is
**hidden** and used only to check the prediction (the **hold-out**). **"Rolling"** means you slide
that cut-point to several different dates and repeat — to confirm the result isn't a quirk of one
particular split. It's the customer-data version of *"train on the past, test on the future."*

> ⚠️ **Word-clash warning for the viva:** in BTYD jargon the training window is confusingly called
> the *"calibration period."* That's a *different* use of the word from *calibration* (forecast
> honesty). If someone asks, flag it: "calibration period = training window; calibration = whether
> the confidence is honest."

### What are "multi-seed results"?
Anything with randomness — a random train/test split, a random simulation, a model's random
starting point — gives a slightly different answer each run. A **seed** fixes that random draw so a
run is exactly reproducible. **Multi-seed** = repeating the *whole* experiment with many different
seeds (we use 10–15) and reporting the average and the spread. It proves a finding is **stable and
real, not luck** from one fortunate draw — and it's what lets us run proper significance tests. In
the charts, the small error bars (the "± " on each number) come from this multi-seed spread.

---

## Part 5 — The specific models and papers on the slides

### Point-error evaluation (the 1987 Colombo paper)
**Schmittlein, Morrison & Colombo (1987), "Counting Your Customers"** is the paper that
*introduced* the Pareto/NBD model. Like almost everyone who followed, it judged forecasts only by
**point error** — how far the single-number prediction landed from the truth (average miss, etc.).
It never checked calibration. **That 40-year blind spot is the gap our project walks into.**

### What is "tractable"?
**Tractable = practical to actually compute** without heroic math or huge run-times. The BG/NBD
model became popular precisely because it was *more tractable* — easier and faster to fit — than
the original Pareto/NBD, while giving similar answers. On the slides, "tractable" is *why* people
adopted a slightly different assumption.

### What is MCMC / Gibbs sampling (Abe 2009), in plain terms?
**MCMC** (Markov-chain Monte Carlo) is a way to fit a model by **exploring** rather than solving.
Instead of computing one best answer, the computer takes thousands of guided random guesses at the
model's settings, spending more time on settings that fit the data well. The cloud of guesses it
leaves behind *is* the uncertainty — a whole range of plausible models, not one. **Gibbs sampling**
(the flavour Abe introduced for this model in 2009) is one recipe for taking those guesses. The
payoff is built-in uncertainty; the cost is it's slow. A big part of our finding is that this extra
cost **doesn't buy better calibration** here.

### What is a "dropout," and "geometric dropout" (Fader 2005)?
**Dropout = the moment a customer churns** — silently gone for good. Every BTYD model needs an
assumption about *how* dropout happens:
- **Pareto/NBD** assumes a customer can drop out at **any instant**, continuously in time.
- **BG/NBD** (Fader, Hardie & Lee, 2005) instead assumes dropout can only happen **right after a
  purchase**, with a fixed probability each time — like flipping a weighted coin after every order
  to decide *"was that their last one?"* That "keep flipping until it comes up 'quit'" pattern is
  the **geometric distribution** — hence **"geometric dropout."** It was chosen because it makes
  the model more **tractable** (easier to fit) while barely changing the forecasts.

### What is Pareto/GGG (Platzer 2016)?
**Pareto/GGG** (Platzer & Reutterer, 2016) is a **richer** BTYD model — and our *second repair*.
Classic models assume purchases arrive **completely at random** (the Poisson "raindrops"
assumption — very irregular spacing). GGG lets purchases be **regular** — e.g. someone who reliably
shops every ~2 weeks. The extra "G"s stand for the added *Gamma* flexibility on the timing. Because
it captures regular buying, it **fixes the *timing* forecast** the classic model got badly wrong.
(Simon 2025 called timing "too inaccurate to use"; GGG rebuts that wherever buying is regular.)

### What is ZILN, and a "value distribution" (Wang 2019)?
**ZILN = Zero-Inflated LogNormal**, a deep-learning model for customer **value** (Wang, Liu &
Miao, 2019). Two facts about spending it captures:
1. **Zero-inflated:** lots of customers spend **nothing** (they never come back) — a big spike at $0.
2. **Lognormal:** among those who *do* spend, a few spend a lot and most spend a little — a skewed shape.

A **value distribution** is just the *predictive distribution for money*: not "they'll spend $50"
but "*probably ~$40, could be $0, could be $200.*" ZILN is the ML challenger on the **value**
dimension — and in our results it's **better-calibrated on money** than the classic structural
model wherever the count assumption fails.

---

## Part 6 — The findings and the fixes

### What is the "parametric count assumption"? (the heart of the finding)
**"Parametric"** = the model assumes purchases follow a specific, rigid mathematical formula (the
Poisson "raindrops" counting law). **Every** model in the BTYD family — Pareto/NBD, BG/NBD, and the
rest — **shares this same assumption** about how purchase *counts* are generated.

Our key discovery: **that one shared assumption is what decides calibration.**
- When the assumption **matches** the real data → forecasts are **well-calibrated.**
- When it **doesn't** (e.g. dense, bulk-buying data) → calibration **breaks.**
- And it's **this assumption** — *not* how you fit the model, *not* which BTYD variant you pick —
  that's the lever.

That's exactly why the two repairs target the assumption: **relax it structurally** (Pareto/GGG)
or **patch its symptoms** (conformal).

### What is "conformal recalibration"? (Repair #1)
A simple **add-on correction** that fixes a model's confidence intervals **without changing the
model itself.** You hold back some data the model didn't train on, **measure how wrong its
intervals actually were** (e.g. "its 95% intervals only caught 80%"), then **widen/adjust them by
exactly that amount** so 95% really means 95% from then on. **"Model-agnostic"** = it works as a
wrapper around *any* model — you don't need to understand or rebuild it. It's cheap, one-pass, and
restores honesty wherever the model was over-confident. *(Example from our results: Online Retail
II's miscalibration score drops 0.212 → 0.044 after this one step — lower is better.)*

### What is an "estimator," and a "variant"? (two different knobs)
People confuse these; keep them separate:
- **Estimator = *how you fit* the model** (the method for finding its numbers from data). Three appear here:
  - **MLE** (maximum likelihood) — fast; finds the single best-fit numbers.
  - **MCMC** — a Bayesian sampler; slower; explores a whole *range* of plausible numbers.
  - **Amortized** — see below.
- **Variant = *which model* in the family you pick** — Pareto/NBD vs BG/NBD vs Pareto/GGG.

We turn each knob independently and show that flipping *either* one barely moves calibration — the
assumption they all share is what governs it.

### What is "amortized" inference, and "invariant to estimator"?
- **Amortized** — you train a neural network **once**, on a mountain of simulated data, to learn
  the shortcut from *"customer summary → fitted parameters."* After that one big upfront cost,
  fitting any *new* dataset is a **single instant step**. The cost is "amortized" (spread out) over
  all future uses — like paying once for a tool you then reuse forever.
- **"Invariant to estimator"** — our finding that **it doesn't matter which fitting method you
  use.** MLE, MCMC, and amortized all give essentially the **same, equally-calibrated** forecasts.
  This *refutes* the popular belief that the expensive Bayesian method (MCMC) buys you better
  uncertainty. The estimator is immaterial; the **count assumption** is what matters.

### Why can't better fitting fix the calibration? (the deep reason)
Because most of the forecast's uncertainty is **irreducible** — it's the inherent randomness of
"will this specific person buy 3 or 5 times," which no amount of clever fitting removes. The part of
the error that *better estimation could* remove shrinks to almost nothing once you have a few
hundred customers. So MLE, MCMC, and amortized all bump into the same floor — which is why they tie.
(This is exactly what the "noise-floor" figure in Part 8 shows.)

---

## Part 7 — The three headline claims (memorize these)

These three lines *are* the paper. If you remember nothing else, remember these.

**1. The count assumption governs calibration.**
Whether a forecast is trustworthy is decided by that one shared Poisson-count assumption — **not**
by how sophisticated the model is. Data matches the assumption → calibrated. Data doesn't → broken.

**2. Two validated repairs.**
- **Conformal recalibration** — a *model-agnostic* patch that re-sizes the intervals so "95% means 95%."
- **Pareto/GGG** — a *structural* upgrade that fixes timing for regular buyers.

Both are tested across the cohorts and shown to work.

**3. Invariance: MLE ≈ MCMC ≈ amortized; Pareto/NBD ≈ BG/NBD.**
How you *fit* it (estimator) and which family member you *pick* (variant) barely matter. This
clears away the two things people *thought* mattered — leaving the count assumption as the real
lever.

---

## Part 8 — Reading the graphs (every figure in plain English)

### First, the one rule that unlocks almost every chart
Most of our figures are **bar charts with `PIT-KS` on the vertical axis**, one cluster of bars per
dataset. Remember just this:

> **PIT-KS is a "dishonesty score." 0 = perfectly honest/calibrated. Taller bar = more
> over-confident. So SHORTER BARS ARE BETTER.**

A handy mental line: **below ~0.05 the bar is "trustworthy"; up around 0.15–0.21 it's "badly
over-confident."** Once you can read one bar, you can read them all. A couple of charts swap in a
different score (CRPS for sharpness, ECE/Brier for churn, "weeks of error" for timing) — each is
flagged below, and in every case **lower/shorter is still better.**

### The reflex reading of any of our bar charts
1. Find the **short bars** → those models are honest on that dataset.
2. Find the **tall bars** → those are over-confident there.
3. Notice **which datasets** make the classic model's bar shoot up → that's where its assumption
   breaks (always the dense / bulk-buying ones: Online Retail II, Dunnhumby).
4. That pattern *is* the paper.

---

### The four "dimension" figures (the core results — slides 12–15)

#### 📊 The calibration map — counts *(`fig_p2_calibration_map.png`, slide 12)*
- **What you're looking at:** seven dataset-clusters, each with four bars — the classic **BTYD**
  model against three machine-learning forecasters (Poisson-GBM, Hurdle-GBM, Quantile-GBM). Height =
  PIT-KS (dishonesty). Datasets are sorted so BTYD goes best→worst left to right; a shaded band
  labels "structure calibrated" on the left and "structure breaks" on the right.
- **The one thing to notice:** BTYD's bars are **tiny** on the left (Simulated ≈ 0.04, Grocery ≈
  0.05, CDNow ≈ 0.06) and **shoot up** on the right (Dunnhumby ≈ 0.17, Online Retail II ≈ 0.21).
  And the distribution-free **Quantile-GBM stays short exactly where BTYD spikes** (Dunnhumby ≈
  0.06 vs BTYD 0.17).
- **What it proves:** there's **no universal winner** — the lens *localises* where each model's
  assumption fails. Structure wins on sparse, well-behaved data; flexible ML wins on dense data.
- **Number to quote:** *"On dense Online Retail II, BTYD's dishonesty score is 0.21 — the flexible
  ML forecaster gets it to 0.04."*

#### 🔧 Repair I — Conformalized BTYD *(`fig_p2_conformal.png`, slide 13)*
- **What you're looking at:** two bars per dataset — **BTYD raw** (grey) vs **Conformalized BTYD**
  (blue) — with a little arrow drawn wherever the fix makes a real dent.
- **The one thing to notice:** every tall grey bar gets **pulled down** to the trustworthy zone,
  and the already-short bars **don't move** (no harm).
- **What it proves:** one cheap, one-pass recalibration **fixes the intervals wherever they were
  broken and leaves the good cases alone** — without touching the model's fit.
- **Numbers to quote:** Online Retail II **0.212 → 0.044**, Ta-Feng **0.072 → 0.027**, Dunnhumby
  **0.164 → 0.097**, CDNow **0.056 → 0.034**; Grocery **0.036 → 0.036** (untouched — the "does no
  harm" case). Coverage tells the same story: on Dunnhumby the 95% intervals go from catching **79%**
  to **88%**.

#### 💰 Value — structural CLV vs deep ZILN *(`fig_p2_clv.png`, slide 14)*
- **What you're looking at:** two side-by-side panels. **Left = calibration** (PIT-KS, lower
  better); **right = accuracy** (nMAE, lower better). In each, **Pareto/NBD + Gamma-Gamma**
  (structural CLV) vs the **deep ZILN** value model, on the three money datasets.
- **The one thing to notice:** on the **left** panel the ZILN bars are dramatically shorter — it's
  far better *calibrated* on money — while on the **right** panel the accuracy bars are about
  **level**. Better honesty at no accuracy cost.
- **What it proves:** the **same count assumption that breaks the counts forecast also poisons the
  money forecast** — structural CLV *inherits* the miscalibration, and the deep model avoids it.
- **Numbers to quote:** PIT-KS Online Retail II **0.212 → 0.031**, Ta-Feng **0.082 → 0.020**,
  Dunnhumby **0.143 → 0.073** — all with accuracy essentially unchanged.

#### 🚪 Churn — P(active) calibration *(`fig_p2_churn.png`, slide 14 alt)*
- **What you're looking at:** two bars per dataset — **BTYD's P(active)** vs an **ML classifier** —
  with height = **ECE (Expected Calibration Error)**, the churn-world version of PIT-KS. (**ECE**:
  when the model says "70% likely still active," is it right 70% of the time? Lower = better.
  **Brier** is a companion overall score.)
- **The one thing to notice:** the **same left/right split** as everywhere else. BTYD's bar is short
  on well-behaved data (Simulated, Grocery — it even *beats* ML there) and tall on dense/misspecified
  data (Online Retail II, Ta-Feng, Dunnhumby), where ML wins.
- **What it proves:** the finding isn't about counts specifically — **the very same assumption governs
  the churn/"is-this-customer-alive" question too.** It's the whole thesis, echoed in the
  classification dimension.
- **Numbers to quote:** churn dishonesty (ECE) on Online Retail II **0.185 (BTYD) vs 0.051 (ML)**;
  Ta-Feng **0.085 vs 0.013**. But on Simulated BTYD wins **0.027 vs 0.047** — proof it's the *data*,
  not the model, that decides.

#### ⏱️ Repair II — timing, Pareto/NBD vs Pareto/GGG *(`fig_p2_timing.png`, slide 15)*
- **What you're looking at:** two bars per dataset — **Pareto/NBD** vs the richer **Pareto/GGG** —
  with height = **median error of the predicted next-purchase time (in weeks)**, lower better. A
  little `*` marks a statistically real win. Datasets run from irregular buyers (Sim k=1, CDNow) to
  regular ones (Sim k=3, Grocery). *(k is a "regularity dial": k=1 is pure randomness — literally
  Pareto/NBD — and higher k means more clockwork buying.)*
- **The one thing to notice:** GGG's bar is shorter **precisely on the regular-buyer datasets**, and
  **level with Pareto/NBD when buying is irregular** (k=1) — exactly as theory predicts.
- **What it proves:** the timing forecast that a prior paper wrote off as "too inaccurate to use" is
  **fixable** — you just need a model that admits some customers buy on a rhythm.
- **Numbers to quote:** Grocery next-purchase median error **3.89 → 2.98 weeks**; Sim k=3
  **4.49 → 3.23 weeks** (both statistically significant). On Sim k=1 (no rhythm) they tie — the
  honest null.

---

### The "invariance" figures (why estimator & variant don't matter — slide 11 / methods)

#### 🧠 Amortized neural estimator vs MCMC *(`fig_p2_amortized.png`)*
- **What you're looking at:** two bars per dataset — slow **MCMC (Gibbs)** vs the **one-pass
  amortized MLP** — height = PIT-KS.
- **The one thing to notice:** the two bars are **practically the same height** on every dataset;
  on the hardest one the instant method is even a touch better.
- **What it proves:** calibration is **estimation-method-agnostic** — a network that fits in a
  single instant matches a sampler that takes minutes. Estimator is immaterial.
- **Number to quote:** on held-out simulated data MCMC vs amortized PIT-KS is **0.036 vs 0.035**
  (statistically indistinguishable, p ≈ 0.85).
- **Companion table (BG/NBD, the *variant* knob):** swapping Pareto/NBD for BG/NBD moves the overall
  grade (CRPS) by **under 0.5%** everywhere, and both stay equally broken on the dense data — so the
  *model variant* doesn't matter either. (Reported as a table rather than a figure.)

---

### The "diagnostic / robustness" figures (the honesty of our own claims)

#### 🛡️ Robustness — what actually breaks calibration *(`fig_p2_robustness.png`)*
- **What you're looking at:** a line chart, not bars. Three stress tests are cranked up left→right,
  with PIT-KS on the vertical axis and a green "well-calibrated" band along the bottom: **dependence**
  between buying-rate and dropout, **transaction censoring** (losing some records), and **seasonality**.
- **The one thing to notice:** two lines **stay down in the green band** no matter how hard you push;
  **only the seasonality line climbs out of it.**
- **What it proves:** the model is **robust to most messiness** — the one thing that genuinely breaks
  it is **time-varying demand (seasonality/promotions)**. Honest disclosure of the single real weak
  spot, which motivates the seasonal work.

#### 📉 The noise floor — why better fitting can't help *(`fig_p2_noisefloor.png`)*
- **What you're looking at:** stacked bars that split the total forecast error into three layers:
  **irreducible counting noise** (grey), **individual-level uncertainty** (blue), and the sliver that
  **better estimation could remove** (red), across growing cohort sizes.
- **The one thing to notice:** the red "fixable by estimation" sliver is **essentially zero**, and
  shrinks further as the cohort grows.
- **What it proves:** the mechanism behind the invariance result — almost all the uncertainty is
  inherent, so **no fitting method can meaningfully beat another.** This is the picture behind
  "MLE ≈ MCMC ≈ amortized."

#### 🌦️ Seasonality on real data *(`fig_p2_seasonality_real.png`)*
- **What you're looking at:** a scatter plot. Horizontal = how much busier the forecast window is
  than the training window (seasonal intensity); vertical = **forecast ratio** = what actually
  happened ÷ what the model predicted. A dashed line marks "1.0 = unbiased."
- **The one thing to notice:** points drift **above 1.0 as intensity rises** — busy/seasonal windows
  are **systematically under-forecast** (the model didn't see the surge coming).
- **What it proves:** the seasonality weakness is **real on actual cohorts, not just a lab artifact**
  — and it's a bias conformal recalibration then absorbs.

---

### The Phase-1 figures (the original calibration paper — background, if asked)

These belong to the first paper and are less likely to be on the review slides, but here's how to
read each in a sentence:

| Figure | What it shows | One-line takeaway |
|---|---|---|
| `fig1_coverage_vs_N.png` | 95% interval coverage vs cohort size, all vs active customers | Grading on *everyone* looks perfect (~0.98) because of the zero-spike — a trap; the real test is the active subgroup |
| `fig2_crps_vs_N.png` | CRPS vs cohort size, MCMC vs MLE | The two fitting methods' lines sit on top of each other → estimator immaterial |
| `fig3_pit_histograms.png` | PIT histograms | **Flat = calibrated**; the correctly-conditioned forecast is flat, the mis-conditioned one is U-shaped (the second trap) |
| `fig4_misspecification.png` | Fit the model to data that breaks its rules (regular timing, mixed populations) | Calibration is **robust**; only very regular buying (k≥3) nudges one subgroup |
| `fig5_ggg_vs_pnbd.png` | PIT-KS vs regularity `k`, Pareto/NBD vs Pareto/GGG | As buying gets regular, Pareto/NBD loses calibration and **GGG restores it** — the structural-repair story |
| `fig6_convergence.png` | MCMC "trace" plots, 4 chains | A sanity check that the Bayesian sampler settled down (chains overlap) — not a result, just due diligence |

---

### One-glance summary — figure → takeaway → number

| Figure | Dimension / role | Takeaway | Headline number |
|---|---|---|---|
| Calibration map | Counts | No universal winner; structure breaks on dense data | BTYD 0.04 → 0.21 across cohorts |
| Conformal | Repair #1 | One patch fixes it, does no harm | Online Retail II 0.212 → 0.044 |
| CLV (ZILN) | Value | Structural CLV inherits the miscalibration | 0.212 → 0.031 (money) |
| Churn | Churn | Same pattern in "is-alive?" | ECE 0.185 → 0.051 (Online Retail II) |
| Timing | Repair #2 | GGG fixes timing for regular buyers | Grocery 3.89 → 2.98 weeks |
| Amortized | Invariance | Instant fit = slow fit | 0.036 ≈ 0.035 (p ≈ 0.85) |
| Robustness | Diagnostic | Only seasonality breaks it | seasonality line leaves the green band |
| Noise floor | Diagnostic | Fitting can't help; error is inherent | fixable share ≈ 0 |

---

## Quick glossary (one-liners for a fast scan)

| Term | One-line meaning |
|---|---|
| Non-contractual | Customers leave silently; you never see them quit |
| Pareto/NBD | Classic model: *how often* people buy (NBD) + *when* they quit (Pareto) |
| BTYD | "Buy Till You Die" — the model family |
| Poisson | The "raindrops" assumption: buying at a steady random rate |
| P(alive) | The model's probability a customer hasn't churned |
| CLV | Total money a customer will spend over their remaining life |
| Point prediction | A single best-guess number |
| Predictive distribution | The full range of outcomes, each with a probability |
| Accuracy | Was the single guess close? |
| Calibration | Is the model's *confidence* honest? ("95% should mean 95%") |
| Under-dispersed | Ranges too narrow → over-confident (the common failure) |
| Zero-inflation | A big spike of customers who buy zero times; can hide miscalibration |
| Proper scoring rule | A grade you can only win by being honest |
| CRPS | Overall grade for a whole distribution (lower = better) |
| PIT | Diagnostic showing *how* a model is miscalibrated (should look flat) |
| PIT-KS | PIT turned into one "dishonesty" number (0 = perfect); the y-axis of most charts |
| Coverage | Do the 95% intervals actually catch 95%? |
| ECE / Brier | The calibration / overall scores for the churn (yes-no) forecast |
| Calibration lens | Our name for judging every model with CRPS + PIT + coverage |
| Four dimensions | Counts (how many) · Value (how much) · Churn (still here?) · Timing (when) |
| Benchmarking | Same test, same data, same yardstick — fair comparison |
| Significance test / Wilcoxon | Is a difference real or just luck? |
| TOST / equivalence | Positively proving two methods are *the same* |
| Transaction event log | Raw data: one row per purchase |
| Cohort | One dataset / one business's customers (we use 7) |
| RFM summary | Recency, Frequency, T — the compact per-customer summary |
| Rolling cut-point | Slide the train/test time-split to several dates to be sure |
| Multi-seed | Repeat with many random seeds to prove it's not luck |
| Point-error evaluation | Judging only by how far the single guess missed (the old way) |
| Tractable | Practical to actually compute |
| MCMC / Gibbs | Fit by exploring thousands of plausible models (slow; gives uncertainty) |
| Dropout | The moment a customer churns |
| Geometric dropout | BG/NBD's "coin-flip after each purchase" churn assumption |
| Pareto/GGG | Richer model for *regular* buyers; fixes timing |
| Regularity `k` | The "rhythm dial": k=1 is pure randomness, higher = more clockwork |
| ZILN | Deep model for customer *value* (spike at $0 + skewed spend) |
| Value distribution | Predictive distribution for money |
| Parametric count assumption | The rigid Poisson-type buying rule all BTYD models share |
| Estimator | *How* you fit the model (MLE / MCMC / amortized) |
| Variant | *Which* model in the family (Pareto/NBD / BG/NBD / Pareto/GGG) |
| Amortized inference | Train a net once → instant fitting forever after |
| Conformal recalibration | Model-agnostic patch that re-sizes intervals to be honest |
| nMAE | A normalized average-miss (accuracy) score; lower better |

---

## Likely viva/audience questions (and the slide each maps to)

- **"What's the difference between accuracy and calibration?"** → Part 2. *Accuracy = was the guess
  close; calibration = was the confidence honest.*
- **"Why does the count assumption cause miscalibration?"** → Part 6. *All BTYD models assume a
  rigid Poisson buying rule; when real data (bulk buying, dense purchasing) doesn't obey it, the
  intervals come out too narrow.*
- **"What does conformal recalibration actually do?"** → Parts 6 & 8. *Measures how wrong the
  intervals were on held-out data and re-sizes them — no change to the model.*
- **"Why compare against ML at all?"** → Parts 1 & 3. *Everyone assumes ML is better; we're the
  first to test that on calibration, and the answer is "only where the count assumption fails."*
- **"How do I read your main chart?"** → Part 8. *Bars are a dishonesty score; shorter is better;
  the classic model's bar spikes on dense datasets — that spike is the whole story.*
- **"Isn't the Bayesian (MCMC) method better because it gives uncertainty?"** → Parts 6 & 8.
  *We tested it — MCMC, MLE, and an instant neural fit are equally calibrated, because the
  uncertainty is mostly irreducible.*
- **"What's the one thing that actually breaks your model?"** → Part 8 robustness figure.
  *Seasonality / time-varying demand — and conformal recalibration absorbs even that.*
