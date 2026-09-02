---
title: "Why the Pareto/NBD Is 'Hard' and the BG/NBD Is 'Easy' — Explained"
type: explainer-qa
created: 2026-09-01
answers: deep_research/doubts_to_be_clarified.txt
source: "Fader, Hardie & Lee (2005), *Counting Your Customers the Easy Way* (BG/NBD).
         Grounded in deep_research/fader2005_deep_dive.md."
role: "Plain-English answers to the four doubts about the BG/NBD thesis: why the Pareto/NBD is
       hard to implement, what a 'difficult likelihood' means, what Gauss hypergeometric functions
       are, and what a 'closed-form expression' is."
---

# Why the Pareto/NBD Is "Hard" and the BG/NBD Is "Easy"

*Answers to [`doubts_to_be_clarified.txt`](../doubts_to_be_clarified.txt). Written for a smart
non-specialist: every piece of jargon is defined the moment it appears, with a concrete example.
Formulas are shown, but you can follow the argument without reading a single one.*

---

## The whole thing in 30 seconds

The **Pareto/NBD** is a 40-year-old model that predicts customer buying. It works well, but the
math you have to solve to *fit it to data* contains a nasty ingredient — a special infinite-series
function (the **Gauss hypergeometric function**) that can't be written as a simple formula and has
to be computed numerically for every customer. That makes it fiddly and slow to implement.

Fader, Hardie & Lee (2005) changed **one assumption** — *when* a customer is allowed to quit — and
that single change made the nasty ingredient vanish. The result, the **BG/NBD**, predicts almost
exactly as well but can be fitted with a plain formula in an Excel spreadsheet. That trade —
**same accuracy, far less pain** — is the thesis.

> **One sentence to remember:** *"The Pareto/NBD is accurate but its fitting math needs a hard
> special function; the BG/NBD swaps one assumption to kill that function and become spreadsheet-easy,
> with no real loss of accuracy."*

---

## Part 1 — The four doubts, answered

### Q1. Why is the Pareto/NBD said to be "hard to implement"?

"Implement" here means **write the code that fits the model to your data** — i.e. find the parameter
values that best explain a customer list. The Pareto/NBD is hard to implement for three linked
reasons:

1. **Its fitting formula contains a special function that has no simple form.** To fit the model you
   maximize its *likelihood* (see Q2). For the Pareto/NBD, that likelihood contains the **Gauss
   hypergeometric function** (see Q3) — a function defined by an infinite sum. You can't just type it
   into a calculator; you have to evaluate it numerically, carefully, for **each customer**.
2. **It's numerically delicate.** That special function has to be computed for many different inputs,
   some near values where it behaves badly (grows huge, or converges slowly). Naive code overflows or
   returns garbage. Getting a *stable, accurate* implementation across all customers takes real care —
   which is why robust versions were only published years later (e.g. the `BTYD` R package, Platzer's
   work).
3. **It's slow and unfriendly to non-programmers.** Because there's no plain formula, you can't do it
   in a spreadsheet, and it's not something a typical marketing analyst can code from scratch.

**Analogy.** Two recipes give an equally tasty cake. Recipe A (Pareto/NBD) needs an ingredient you
must synthesize yourself in a lab each time, watching the temperature so it doesn't explode. Recipe B
(BG/NBD) uses an ingredient you can buy at any shop. Same cake — one kitchen is a lab, the other is
your countertop.

> **Careful distinction:** the Pareto/NBD is not "hard" because the *idea* is complicated — the idea
> is intuitive (people buy at some rate, then silently quit at some point). It's hard because the
> *arithmetic of fitting it* runs into that special function.

---

### Q2. Why is it a "difficult likelihood"?

**What a likelihood is (plain English).** When you fit a model, you have a set of unknown dials
(parameters) and some observed data. The **likelihood** is a formula that answers: *"If the dials were
set to these values, how probable is the data I actually saw?"* Fitting the model =
**turning the dials until that probability is as high as possible** (this is Maximum Likelihood
Estimation, MLE — literally "pick the dial settings that make the observed data most likely").

So the likelihood is the *engine* of fitting. If the likelihood formula is clean, fitting is easy. If
it's ugly, fitting is hard. The Pareto/NBD's likelihood is ugly, and here's *why* it has to be:

- Each customer gives you three numbers: how many repeat purchases they made ($x$), when their last
  purchase was ($t_x$), and how long you've watched them ($T$).
- But two things are **hidden**: that customer's personal **buying rate** and the **moment they
  silently quit** (their unobserved "lifetime"). You never see either.
- To write the probability of the *visible* data, you must **average over every possible value of the
  hidden things** — every possible buying rate, and every possible quitting time. "Averaging over all
  possible values of a hidden quantity" is done with an **integral** (a continuous sum).
- The Pareto/NBD assumes the quitting time is **continuous** — a customer can drop out at *any instant*,
  including in the long silent gap after their last purchase. Integrating over "quit at any instant,
  weighted by how likely each instant is" is exactly the step that produces the **Gauss hypergeometric
  function** (Q3). That's where the difficulty is born.

**In one line:** the likelihood is difficult because it must integrate over a *continuous* hidden
dropout time, and that integral doesn't collapse to a simple formula — it collapses to a hard special
function.

---

### Q3. What are Gauss hypergeometric functions?

**Short version:** a **hypergeometric function** is a function defined by an **infinite sum** with a
very particular, self-similar pattern in its terms. The **Gauss** hypergeometric function is the most
famous one, written

$$\,_2F_1(a,b;c;z) \;=\; \sum_{n=0}^{\infty} \frac{(a)_n\,(b)_n}{(c)_n}\,\frac{z^n}{n!}.$$

Don't be scared by the symbols — here is all it says:

- It's a **sum of infinitely many terms** ($n = 0, 1, 2, 3, \dots$).
- Each term is built from the numbers $a, b, c$ (its "shape parameters") and a value $z$.
- The $(a)_n$ notation just means "multiply a rising chain of numbers" — e.g. $(a)_3 = a(a{+}1)(a{+}2)$.
  It's a cousin of the factorial.

**Why it matters here:** because it's an *infinite* sum, there is **no way to write it as a finite,
plain formula** using only $+, -, \times, \div$, powers, exp, and log. To get a number out of it you
must **add up terms numerically until they stop mattering** — and do that for every customer, for every
trial setting of the dials while fitting. That is the concrete source of the "hard to implement" and
"slow" complaints.

**Where does it come from?** Hypergeometric functions are what you get when you integrate certain
products of powers and exponentials — precisely the shape of the Pareto/NBD's "average over the hidden
continuous dropout time" step (Q2). They're not chosen for fun; they *fall out of the math* the moment
you assume a continuous lifetime.

**A familiar cousin, for intuition.** You already trust one function defined by an infinite sum:
$e^z = 1 + z + \tfrac{z^2}{2} + \tfrac{z^3}{6} + \cdots$. The Gauss hypergeometric is the same *kind* of
object — an infinite series — but with a more complicated term pattern and, unlike $e^z$, no friendly
button on your calculator and nastier numerical behavior near certain inputs.

```
 "Closed form"  (elementary):   e^x, √x, Γ(a), B(a,b)   ← one clean expression, evaluate directly
 "Special fn"   (series):       ₂F₁(a,b;c;z)            ← infinite sum, must be computed term by term
```

---

### Q4. What is a "closed-form expression"?

A **closed-form expression** is a formula you can **write down and evaluate in a finite number of
standard steps** — using only "everyday" operations and functions: $+\ -\ \times\ \div$, powers and
roots, $\exp$, $\log$, and a small set of well-behaved standard functions (like the Gamma function
$\Gamma$ and the Beta function $B$, which are just smooth generalizations of the factorial).

The defining feature: **no infinite process is left for you to carry out.** No "sum forever," no "run a
numerical integration routine." You plug in numbers and turn the crank a fixed number of times.

| | Closed-form? | Why |
|---|:--:|---|
| $3x^2 + \sqrt{x} - 7$ | ✅ | finite arithmetic |
| $e^{-\lambda t}$ | ✅ | $\exp$ is a standard function |
| $\dfrac{B(a,\,b+x)}{B(a,b)}$ (a BG/NBD term) | ✅ | Beta function, evaluated directly |
| $\displaystyle\int_0^\infty \! f(\mu)\,d\mu$ leading to $\,_2F_1(\dots)$ (Pareto/NBD) | ❌ | leaves an infinite series to sum |

**Why the fuss?** A closed-form likelihood is one you can type into **Excel** — a cell formula — and
maximize with Solver, or code in ten lines. That is exactly the practical prize the BG/NBD wins, and
the exact thing the Pareto/NBD denies you.

> **Nuance worth knowing.** "Closed form" is a soft convention, not a hard law: it depends on which
> functions you agree to call "standard." Almost everyone counts $\Gamma$ and $B$ as standard (so the
> BG/NBD *likelihood* is closed-form), while $\,_2F_1$ is usually treated as a "special function" that
> takes you *outside* closed form. That convention is exactly why the BG/NBD gets to claim "closed-form"
> and the Pareto/NBD doesn't.

---

## Part 2 — The thesis, sentence by sentence

> **Thesis.** *"The Pareto/NBD is powerful but hard to implement (a difficult likelihood, Gauss
> hypergeometric functions). Swap its continuous exponential lifetime for a beta-geometric dropout that
> fires after each purchase, and you get the BG/NBD — near-identical predictive performance with
> closed-form expressions simple enough to estimate in a spreadsheet."*

Let's unpack it clause by clause.

### "The Pareto/NBD is powerful …"
It captures real customer behavior with just four parameters: people buy at personal rates that vary
across the base, and each silently quits at some personal time. From that it predicts future purchases,
who's still "alive," and who your best customers will be — accurately, on real data, for 40 years. That's
the "powerful."

### "… but hard to implement (a difficult likelihood, Gauss hypergeometric functions)."
Exactly Q1–Q3: fitting it means maximizing a likelihood (Q2) that contains the Gauss hypergeometric
function (Q3), a hard-to-compute infinite series. Powerful engine, painful to build.

### "Swap its continuous exponential lifetime …"
This names the *one assumption being changed*. In the Pareto/NBD a customer's lifetime is
**continuous and exponential**: they can drop out at **any instant**, and the chance of "quitting now"
is constant through time (the "exponential"/memoryless assumption). Allowing dropout at *any instant* is
precisely what forced the hard integral (Q2).

### "… for a beta-geometric dropout that fires after each purchase …"
The replacement. Instead of quitting at any instant, the customer only gets a chance to quit **right
after each purchase** — like flipping a coin after every transaction: *heads, I'm done; tails, I'll buy
again.* This is **discrete**: dropout can happen only at a purchase, not in the silent gaps.

- **"geometric"** = the "flip a coin after each purchase until you quit" process (the number of
  purchases until you quit follows the *geometric* distribution).
- **"beta"** = customers differ in how quit-prone they are; that personal coin-bias is spread across the
  base by a **Beta distribution** (a flexible curve for a probability between 0 and 1).
- Together: **beta-geometric dropout.**

**Why this kills the hard function:** dropout can now happen only at a *finite* list of moments (the
purchases), so the "average over the hidden quitting time" becomes a **short finite sum instead of a
continuous integral** — and a finite sum of elementary terms *is* closed-form (Q4). The Gauss
hypergeometric function never appears in the fitting step.

```
 Pareto/NBD:  can quit at ANY instant  ──►  integrate over a continuum  ──►  ₂F₁  (hard)
   x───┬───────┬──────────┬───────────────────────────►  (quit possible anywhere on the line)

 BG/NBD:      can quit only AFTER a purchase  ──►  sum over a few points  ──►  elementary (easy)
   x───●───────●──────────●                          (● = the only moments a quit can happen)
```

### "… and you get the BG/NBD …"
**BG/NBD = Beta-Geometric / Negative-Binomial-Distribution.** Same buying process as before
(the "NBD" part — buying rates vary across people); new, discrete dropout process (the "BG" part). Hence
the paper's title, *"Counting Your Customers the **Easy Way**."*

### "… near-identical predictive performance …"
The punchline that makes the swap worthwhile: despite the different dropout story, the BG/NBD's forecasts
match the Pareto/NBD's very closely on real data. You give up almost **nothing** in accuracy. (Our own
project confirms this from a new angle: Pareto/NBD and BG/NBD are *interchangeable for forecast
calibration* — see [`../fader2005_deep_dive.md`](../fader2005_deep_dive.md) and
[`../../docs/bgnbd.md`](../../docs/bgnbd.md).)

### "… with closed-form expressions simple enough to estimate in a spreadsheet."
The prize (Q4): the BG/NBD likelihood is elementary — Gamma and Beta functions and powers, no infinite
series — so you can literally fit it in **Excel**. That accessibility is why the BG/NBD became the
field's workhorse.

---

## Part 3 — Two footnotes worth knowing

**1. The one-time-buyer quirk (and its fix).** In the plain BG/NBD, dropout requires a purchase — so a
customer who *never repeats* can never have "dropped out," and the model insists they're still alive
($P(\text{alive}) = 1$). That's clearly wrong for someone who bought once and vanished. The **modified
BG/NBD (MBG/NBD)** patches it by adding a dropout opportunity **at time zero** (a chance to quit even
before the first repeat), so one-and-done customers can be counted as gone. *This is the "(modified) beta
geometric dropout process — what is modified and why" question from `key_terms.txt`; see also the
glossary,* [`04_key_terms_glossary.md`](04_key_terms_glossary.md).

**2. "Closed-form" applies to the *fitting*, with one honest caveat.** The BG/NBD *likelihood* — the
thing you maximize to fit the model — is fully elementary; that's the spreadsheet claim, and it's true.
Its *aggregate* forecast formula for the expected number of transactions over time, $E[X(t)]$, does still
contain a single Gauss hypergeometric term. But that's **one** well-behaved call for a whole-cohort
curve, computed **once**, not a delicate per-customer integral evaluated thousands of times inside an
optimizer. The hard part — fitting — is where the BG/NBD wins, and it wins cleanly.

---

*Companion docs: [`../fader2005_deep_dive.md`](../fader2005_deep_dive.md) (the research-level read),
[`04_key_terms_glossary.md`](04_key_terms_glossary.md) (every term defined),
[`../../docs/bgnbd.md`](../../docs/bgnbd.md) (what our project finds about the BG/NBD variant).*
