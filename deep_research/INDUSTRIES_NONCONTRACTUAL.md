---
title: "Industries with non-contractual churn"
type: reference
updated: 2026-09-20
role: Taxonomy of the settings where customer "death" is *unobserved* (no cancellation
      event) — the domain of BTYD / customer-base analysis. Feeds the coverage check in
      FIELD_GENEALOGY.md and the tracker's category scope.
---

# Industries & settings with non-contractual churn

## The defining criterion

A setting is **non-contractual** when the firm **never observes the moment a customer
leaves**. There is no subscription to cancel, no contract to let lapse, no explicit
"I'm done" signal. The customer simply *stops buying* — and the firm can only **infer**
whether they are still "alive" from the pattern of their past transactions (recency and
frequency). This unobserved-dropout problem is exactly what the Pareto/NBD (Schmittlein,
Morrison & Colombo 1987) and its descendants (BG/NBD, Pareto/GGG, BG/BB, …) were built
to solve.

Contrast with the **contractual** setting (postpaid telecom, insurance, gym, most SaaS),
where churn is a *dated, observed event* (the cancellation) and the problem reduces to a
survival / classification task. Most of the applied "churn-prediction ML" literature
lives in the contractual world (telecom/UCI datasets); the customer-base-analysis / BTYD
tradition lives in the non-contractual world. Our manuscript sits squarely in the latter.

Two sub-flavours matter:

- **Pure non-contractual** — no membership at all (walk-in retail, e-commerce guest
  checkout, catalog buyers, donors). Dropout is fully latent.
- **"Opportunity-to-observe" / membership-without-obligation** — the customer enrolls
  (loyalty card, free account, prepaid SIM) but has *no obligation to transact*, so
  usage/purchase can silently cease. Enrollment is observed; **dropout is not**. These
  are still non-contractual for forecasting purposes.

Discrete-time vs continuous-time is an orthogonal axis (Fader & Hardie 2010, BG/BB):
donations arrive on a yearly grid (discrete), grocery trips arrive in continuous time.

---

## The industry map

Legend — **Signal**: the observable transaction stream the model reads.
**Contractual?** N = pure non-contractual · N* = membership/usage (dropout still latent).
**Canonical work / dataset** anchors each row in the literature or in our own cohorts.

### A. Retail & consumer goods (the historical heartland)

| # | Industry / setting | Contractual? | Signal | Canonical work / dataset |
|---|---|---|---|---|
| 1 | **FMCG / grocery supermarkets** | N* (loyalty card) | basket trips, category purchases | Buckinx & Van den Poel (2005) — the canonical non-contractual FMCG defection paper; Dunnhumby, Ta-Feng (our cohorts) |
| 2 | **E-commerce / online retail** | N | orders, guest + account purchases | Fader & Hardie CDNOW (2001); Online Retail II, Olist (our cohorts); Wang ZILN (2019) |
| 3 | **Catalog / mail-order / direct marketing** | N | order recency-frequency-monetary | the RFM roots (Cullinan, direct-marketing practice) → Fader, Hardie & Lee (2005) iso-value |
| 4 | **Consumer packaged goods (branded repeat-buy)** | N | panel purchases, brand choice | Ehrenberg NBD (1959) & Dirichlet (Goodhardt–Ehrenberg–Chatfield 1984) — the repeat-buying bedrock |
| 5 | **Apparel / fashion / specialty retail** | N | store + online purchases | applied BTYD; retail cohorts |
| 6 | **Pharmacy / drugstore** | N* | refill & OTC purchases | applied CBA |

### B. Services & hospitality

| # | Industry / setting | Contractual? | Signal | Canonical work / dataset |
|---|---|---|---|---|
| 7 | **Airlines — frequent-flyer usage** | N* | flights flown, miles earned | loyalty-program CBA; "opportunity to observe" |
| 8 | **Hotels / hospitality** | N* | stays, bookings | hospitality churn (2025 refs in phase1) |
| 9 | **Restaurants / QSR / coffee chains** | N* (loyalty app) | visits, app orders | loyalty-app CBA |
| 10 | **Car wash & recurring local services** | N | visit recency/frequency | Mufti et al. (2026) rolling-window carwash churn |
| 11 | **Salons, gyms (pay-per-visit), clinics** | N* | visit stream | applied CBA |

### C. Mobility & platforms

| # | Industry / setting | Contractual? | Signal | Canonical work / dataset |
|---|---|---|---|---|
| 12 | **Ride-hailing / taxi** | N | trips taken | platform churn |
| 13 | **Car-sharing / micromobility** | N* (account) | rentals/rides | Wachwanakijkul et al. (2024) car-sharing churn |
| 14 | **Two-sided marketplaces / gig platforms** | N | buyer & seller activity | platform CBA (buyer + supplier churn) |

### D. Digital, gaming & media (à la carte)

| # | Industry / setting | Contractual? | Signal | Canonical work / dataset |
|---|---|---|---|---|
| 15 | **Free-to-play / mobile games** | N* (free account) | sessions, in-app purchases | player-churn / LTV modelling |
| 16 | **Casinos & gambling / betting** | N* | wagers, visits | player-value CBA |
| 17 | **À-la-carte digital content / micro-transactions** | N | pay-per-item purchases | digital-goods CLV |
| 18 | **App engagement / freemium (usage churn)** | N* | active-use events | usage- vs subscription-churn distinction |

### E. Financial & B2B

| # | Industry / setting | Contractual? | Signal | Canonical work / dataset |
|---|---|---|---|---|
| 19 | **Retail banking — transactional usage** | N* (account open, usage latent) | card spend, txn count | usage-attrition CBA |
| 20 | **Credit-card spend / co-brand cards** | N* | monthly spend | spend-based CLV |
| 21 | **Brokerage / trading activity** | N* | trades placed | activity-churn |
| 22 | **B2B industrial / wholesale reordering** | N | purchase orders | Schmittlein & Peterson (1994) industrial purchase — the first B2B CBA application |
| 23 | **Distribution / dealer networks** | N | reorder stream | applied B2B CBA |

### F. Non-profit & public

| # | Industry / setting | Contractual? | Signal | Canonical work / dataset |
|---|---|---|---|---|
| 24 | **Charitable giving / donor retention** | N (discrete) | annual/periodic gifts | Fader & Hardie (2010) BG/BB donations — the canonical discrete-time non-contractual case |
| 25 | **Membership orgs / associations (lapse)** | N* | renewal-optional activity | donor/lapse models |
| 26 | **Blood/organ donation, volunteering** | N | donation events | discrete-time BTYD analog |

### G. Adjacent / boundary (contractual — where BTYD does *not* natively apply)

Kept explicitly to mark the boundary the field polices:

| # | Setting | Why it's the *other* world |
|---|---|---|
| — | **Postpaid telecom** | cancellation is observed → contractual; dominates the ML-churn/UCI literature (Imani 2025, Manzoor 2024) |
| — | **Insurance, utilities, gym contracts, most B2B SaaS** | dated renewal/cancellation event → survival/classification, not latent-dropout inference |
| — | **Prepaid telecom** | *borderline*: no contract, but activity + top-ups make dropout partly observable |

---

## Why this matters for the paper / tracker

1. **Scope discipline.** The tracker's non-contractual scope should *keep* rows in A–F and
   treat G as out-of-scope comparators (this is exactly what `tools/curate.py` already does
   when it strips contractual telecom/SaaS). This taxonomy is the rubric for that call.
2. **Coverage check.** Cross-referencing this map against the corpus (see
   `FIELD_GENEALOGY.md` §coverage) shows the field — and our cohorts — cluster in
   **retail/e-commerce/grocery** (rows 1–5) with strong anchors in **donations** (24) and
   **B2B** (22). The thinner tails (gaming 15–16, mobility 12–14, financial usage 19–21)
   are where applied BTYD is still expanding and where new tracker hits tend to land.
3. **The "membership-without-obligation" insight.** Many settings marketed as
   subscriptions (loyalty programs, freemium, prepaid) are *forecasting*-non-contractual
   because dropout stays latent. Classifying by the **observability of dropout**, not by
   the presence of an account, is what puts them in this map.
