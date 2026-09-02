---
title: "The Four Forecasts & the 'Active Customer' Redefinition — Explained"
type: explainer-qa
created: 2026-09-01
answers: deep_research/goals_and_gaps.txt
source: "Simon (2025), *A generalised comparison of Pareto/NBD-based forecasts* (§1, Table 1, §5).
         Grounded in deep_research/simon2025_deep_dive.md."
role: "Plain-English explanation of Simon (2025)'s four forecast targets and — the heart of
       goals_and_gaps.txt — her redefinition of an 'active' customer from an unobservable dropout-based
       notion to a validatable, practically relevant one."
---

# The Four Forecasts & the "Active Customer" Redefinition

*Answers to [`goals_and_gaps.txt`](../goals_and_gaps.txt). The four forecast targets are summarized here
and treated quote-by-quote in [doc 2](02_simon2025_abstract_quote_by_quote.md); this doc's real job is
the passage `goals_and_gaps.txt` dwells on — **why Simon (2025) throws out the textbook definition of an
"active" customer and writes a new one.** Written for a smart non-specialist; terms defined on first use.*

---

## The whole thing in 30 seconds

A model can only be trusted if you can **check** its predictions against what actually happened. The old
textbook definition of an "active customer" — *"a customer the model thinks is still alive"* — **can never
be checked**, because in a non-contractual business you never observe who truly quit. Simon (2025)
replaces it with a definition you *can* check: **an active customer is one who actually makes a purchase
within a chosen time window** (e.g. the next 6 months). This small redefinition is a big deal: it makes
the forecast **validatable**, **practically meaningful**, and **fair to grade** — and it's the definition
our project inherits wholesale.

---

## Part 1 — The four forecast targets (recap)

> *"(1) predicting the individual number of purchases made in a given forecast period, (2) identifying
> customers which make at least one purchase within a given forecast period ("active" customers), (3)
> identifying the Top 10% and Top 20% of the customer base, (4) predicting the timing of the next
> purchase."*

| # | Target | The manager's question | Type of problem | How it's judged |
|---|---|---|---|---|
| 1 | **Counts** | *How many* purchases next period? | Regression (a number) | error size (MAE/RMSE) |
| 2 | **Active** | *Will they buy at all* (≥1) next period? | Classification (yes/no) | sensitivity / precision / accuracy |
| 3 | **Top 10% / 20%** | *Who are the future best customers?* | Ranking | how many true top-buyers you catch |
| 4 | **Timing** | *When* is the next purchase? | Time-to-event | deviation in days/weeks (fails — see doc 2) |

A couple of clarifications specific to `goals_and_gaps.txt`:

- **"forecast period"** (also "prediction window") = the future stretch of time you're forecasting over —
  Simon uses 13, 26, and 52 weeks. All four targets are "within this window."
- **"Top 10% and Top 20% of the customer base"** = rank every customer by their *predicted* future buying
  and take the top decile / top fifth. Businesses spend retention and loyalty budget on exactly these
  people, so getting the ranking right is worth money even if the exact counts are off.
- **"calibration length"** (its partner term, from the glossary) = the *past* stretch used to fit the
  model, as opposed to the future window you predict. Fit on the calibration period → forecast the
  forecast period.

> **Should there be a fifth target?** No — see the detailed answer in
> [doc 2, Part 1](02_simon2025_abstract_quote_by_quote.md). The four span *how much / whether / who /
> when*; monetary value (CLV) is an application built on target 1, not a new axis. The fertile move is a
> new **lens** (calibration) on the same four, which is our project.

---

## Part 2 — The "active customer" redefinition (the heart of this file)

This is the long passage `goals_and_gaps.txt` highlights. Simon calls it out as her sharpest
methodological point, so it's worth slowing down. Read the two definitions side by side:

| | **Old (dropout-based) definition** | **New (validatable) definition — Simon's** |
|---|---|---|
| "Active" means… | the model estimates the customer is **still alive** (hasn't silently dropped out) | the customer **actually makes ≥ 1 purchase** within a chosen window |
| Based on… | the hidden **dropout process** — `P(alive)` | **observed behavior** in the forecast window |
| Can you check it? | **No** — the truth is never observed | **Yes** — you just wait and see if they bought |
| Practically useful? | Not really (see the two failure cases below) | Yes — tied to the company's planning horizon |

### Quote — the two failure cases of the old definition
> *"Previous studies … define active customers solely based on their dropout process, regardless whether
> or when they are going to make another purchase in the future. However, even though this may be correct
> from a theoretical standpoint, this definition is misleading in practice."*

The old definition asks only *"is the customer still alive?"* and ignores *"will they actually **do**
anything?"* That produces two absurd classifications:

1. > *"If a customer drops out in a few months without making another purchase, he or she is still
   > classified as active."*

   A customer the model believes is *alive right now* is labeled "active" **even if they never buy again**
   before quitting. Alive-but-silent is still counted as active. Useless to a manager — you'd waste
   retention spend on someone who's about to ghost you.

2. > *"The same applies to a customer who makes his or her next purchase in the distant future, which is
   > outside the company's planning horizon."*

   A customer whose next purchase is *years away* — long past any window the company plans around — is
   also labeled "active." Technically alive, but irrelevant to this quarter's or this year's decisions.

> *"Neither of these two consumers corresponds to the common understanding of an active customer and
> should therefore not be treated as such."*

**The point:** "alive in the model" ≠ "active in any sense a business cares about." A useful notion of
active has to involve *actually buying, and soon enough to matter.*

### Quote — the supporting evidence (long lifetime ≠ profitable)
> *"This is supported by Reinartz and Kumar (2000), who have shown that customers with a long lifetime are
> not necessarily the profitable ones."*

A classic marketing finding, cited to reinforce the argument: **staying alive a long time doesn't make a
customer valuable.** Plenty of long-lived customers buy rarely and cheaply. So a definition of "active"
built purely on *lifetime / aliveness* (the old one) is anchored to the wrong thing. What matters is
*doing something valuable within your horizon* — which the new definition captures and the old one misses.

### Quote — the deeper problem: you can't validate the old definition
> *"As the lifetime is not observable, another problem arises as companies cannot validate how well this
> forecast works for their customer base."*

This is the killer objection, and it connects straight to doc 2's `P(alive)` quote:

- **"the lifetime is not observable"** = in a non-contractual setting nobody cancels, so you *never learn*
  the true moment a customer quit.
- **"cannot validate"** = therefore you can *never build the answer key* needed to grade an aliveness-based
  forecast. If "active = alive" and you never observe who's truly alive, you can **never score whether the
  classification was right.** The forecast is not just impractical — it's **unfalsifiable.**

A model whose predictions can't, even in principle, be checked against reality is scientifically stuck.
That alone is reason to redefine the target.

### Quote — the new, validatable definition
> *"Hence, this paper re-defines a customer as active if he or she makes a purchase within a given time
> period (e.g., the company's planning horizon) which is practically relevant and also allows
> validation."*

The fix, and why it solves all three problems at once:

- **"makes a purchase within a given time period"** = active is now defined by an **observable action**,
  not a hidden state. In symbols, active $\iff x^{*} > 0$, where $x^{*}$ is the number of purchases in the
  forecast window.
- **"the company's planning horizon"** = the window is chosen to match how far ahead the business actually
  plans (a quarter, a year) — so the label is **decision-relevant** by construction. This kills failure
  case 2 (distant-future buyers are correctly *not* active for a near horizon).
- **"practically relevant"** = it targets customers who will *actually buy and matter*, not merely exist.
  This kills failure case 1 (alive-but-silent customers are correctly *not* active).
- **"allows validation"** = you can **wait out the window and check**: did they buy or not? Now there's an
  answer key, so the forecast can be scored, compared, and improved. This kills the unfalsifiability
  problem.

```
  OLD:  active  :=  P(alive today) is high        →  hidden state,   NEVER checkable
  NEW:  active  :=  buys at least once in window   →  observed action, ALWAYS checkable
                    (x* > 0, window = planning horizon)
```

### Quote — and it lets you compare estimators fairly
> *"The analysis of this new type of classification also compares different ways of predicting the
> activity status based on MLE- and MCMC parameter estimates."*

Because the new target is checkable, Simon can now do the thing the old target made impossible: run
**MLE vs. MCMC** head-to-head on *"who will be active?"* and see which fitting method classifies better —
scored against real outcomes. (Her finding: MCMC tends to *under*-predict counts, so it calls fewer people
active — low **sensitivity** [it misses some true actives] but high **precision** [when it says active,
it's usually right]; on balance it assigns the largest fraction correctly. Terms in the glossary,
[doc 4](04_key_terms_glossary.md).)

---

## Part 3 — Why this matters for *our* project

The validatable active definition isn't just Simon's tidy-up — it's a load-bearing choice we build on:

1. **We inherit it directly.** Our project scores $P(x^{*} > 0)$ — "probability the customer buys at least
   once in the window" — *exactly* Simon's validatable definition, never the unobservable `P(alive)`.
2. **It's the bridge to the churn literature.** The same quantity is what Ulrich (2026) calls $R_H$
   (retention over a horizon) and what churn-classification papers predict. Simon's redefinition is the
   hinge that lets a "buy-till-you-die" model and a "churn classifier" be graded on the *same* target.
   (See [`../ulrich_deep_dive.md`](../ulrich_deep_dive.md).)
3. **It's what makes *calibration* even possible.** You can only ask "is the model's 70%-likely-to-buy
   claim honest?" if you can later observe whether they bought. The validatable definition supplies the
   ground truth our whole calibration lens needs.

> **One line to remember:** *Simon replaced an unobservable "is the customer alive?" with a checkable
> "will the customer buy in our window?" — turning an ungrade-able forecast into a scientifically testable
> one, and handing our project its ground truth.*

---

*Companion docs: [`02_simon2025_abstract_quote_by_quote.md`](02_simon2025_abstract_quote_by_quote.md)
(the abstract & intro in full), [`../simon2025_deep_dive.md`](../simon2025_deep_dive.md) (research-level
read), [`../ulrich_deep_dive.md`](../ulrich_deep_dive.md) (the aliveness-vs-validatable distinction,
formalized), [`04_key_terms_glossary.md`](04_key_terms_glossary.md) (every term defined).*
