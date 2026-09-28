---
title: "Dataset Hunt & Log — open transaction / uplift datasets"
type: reference
created: 2026-09-20
role: Running log of open-source datasets for (a) non-contractual churn/CLV by industry and (b) causal
      ML / uplift (treatment present). Tracks what we hold, what's worth adding, what other papers use,
      and access/licence. Feeds the F8 gap, Gear 1 robustness, and Gear 2 Stage-A/B data.
      Updated per session; status column is the live layer.
---

# Dataset hunt & log

**Legend — Status:** ✅ held & used · 📥 held, not yet used · ⬜ candidate (fetchable) · 🔒 login/manual ·
🧑 needs your decision. **Tx?** = customer-level transaction log (what BTYD needs). **T?** = carries a
marketing **treatment** variable (what causal ML needs).

---

## 1. What we already hold (`data/`)

| Dataset | Industry | Tx? | T? | Status | Notes |
|---|---|:--:|:--:|:--:|---|
| **CDNOW** | e-commerce (music) | ✅ | — | ✅ | the field benchmark; Gear 1 primary |
| **Online Retail II** | e-commerce (UK gifts) | ✅ | — | ✅ | ~95 MB; Gear 1 |
| **Grocery (groceryElog)** | grocery | ✅ | — | ✅ | from CLVTools |
| **Ta-Feng** | grocery (supermarket) | ✅ | — | ✅ | Gear 1 |
| **Olist** | e-commerce marketplace (Brazil) | ✅ | — | ✅ | multi-table; Gear 1 |
| ⭐ **Dunnhumby "Complete Journey"** | grocery retail | ✅ | ✅ | 📥 | **already on disk with `campaign_table.csv`, `campaign_desc.csv`, `coupon.csv`, `coupon_redempt.csv`, `causal_data.csv`** — i.e. household-level **campaign/coupon treatment**. **This is a real treatment variable we already have** → prime Gear 2 Stage-B candidate (targeted campaigns TypeA/B/C + redemptions over 2 years). |

**Immediate action:** promote Dunnhumby from "Gear 1 grocery cohort" to "**Gear 2 quasi-experimental**
uplift dataset" — build the BTYD state on `transaction_data.csv`, treat campaign exposure/coupon as T,
future spend as Y.

---

## 2. Causal-ML / uplift datasets  (treatment present — Gear 2 Stage B)

| Dataset | Domain | T design | Tx? | Access | Status | Priority |
|---|---|---|:--:|---|:--:|:--:|
| **Hillstrom (MineThatData)** | e-commerce email | **randomized** (men/women/none) | partial | `sklift.datasets.fetch_hillstrom` (auto) | ⬜ | 🔴 start here — small, clean, classic |
| **Criteo-Uplift v2** | online ads | **randomized** incrementality tests | ❌ (features only) | `sklift.datasets.fetch_criteo` (auto) | ⬜ | 🟡 huge (25M); scale test, no tx log |
| **Lenta** | grocery | promo campaign | partial | `sklift.datasets.fetch_lenta` (auto) | ⬜ | 🟡 grocery + treatment; good non-contractual fit |
| **X5 RetailHero** | retail loyalty | **randomized** SMS/promo | ✅ (has tx log) | `sklift.datasets.fetch_x5` | 🔒 | 🔴 **best transaction-log + treatment fit** — register at retailhero.ai |
| **MegaFon** | telecom offer | randomized | ❌ | `sklift.datasets.fetch_megafon` | 🔒 | ⚪ contractual-ish; low priority |
| **Starbucks Rewards** (Udacity) | coffee loyalty app | offer sent (BOGO/discount/info) | ✅ (offer + txn) | Kaggle / Udacity | ⬜ | 🟡 loyalty-app non-contractual + treatment |
| **Dunnhumby Complete Journey** | grocery | campaign/coupon | ✅ | **already held** | 📥 | 🔴 (see §1) |

> `sklift` gives one-call fetchers for Hillstrom/Criteo/Lenta/X5/MegaFon — the fastest Stage-B path.
> The `uplift-bench` repo bundles Hillstrom/Criteo/Lenta/RetailHero/MegaFon + a synthetic DGP.

---

## 3. Non-contractual transaction datasets by industry  (Gear 1 breadth / F8)

Mapped to INDUSTRIES_NONCONTRACTUAL.md rows. All open unless noted.

| Dataset | Industry (row) | Tx? | Access | Status | Why add |
|---|---|:--:|---|:--:|---|
| **Instacart Online Grocery** | grocery/e-comm (1,2) | ✅ | Kaggle (3M orders, 200k users) | ⬜ | large modern grocery basket log; strong repeat-purchase signal |
| **Retailrocket** | e-commerce (2) | ✅ (events) | Kaggle | ⬜ | view→addtocart→transaction events; e-comm CBA |
| **H&M Personalized Fashion** | apparel (5) | ✅ | Kaggle (2022; 2018–20 txns) | ⬜ | apparel/fashion — a thin cell in our coverage |
| **Acquire Valued Shoppers** | grocery/retail (1) | ✅ | Kaggle | ⬜ | **offers included** → also a light uplift set; repeat-buyer target |
| **Google Merchandise Store (GA4 sample)** | e-commerce (2) | ✅ | BigQuery public | ⬜ | clickstream + purchases; modern web-retail |
| **KKBox (WSDM 2018)** | music streaming (18) | ✅ (subs+logs) | Kaggle | 🧑 | *borderline*: subscription churn is dated → mostly contractual; use only for the usage-churn boundary |
| **UCI Online Retail (I)** | e-commerce (2) | ✅ | UCI | 📥 | predecessor of Online Retail II (already held) |
| **Brazilian E-Commerce (Olist)** | marketplace (14) | ✅ | held | ✅ | already used |
| **India non-contractual transaction log** | any (F8) | ✅ | — | 🧑 | **F8 still open** — no genuinely-Indian customer-level non-contractual tx dataset surfaced (Imani's "India" hits were conference venues). User decision. |

---

## 4. Cross-paper common datasets  (what the corpus keeps reusing)

From LITERATURE_MATRIX + the genealogy corpus — the datasets that recur across BTYD/CLV/ML papers:

| Dataset | Recurs in | We have? |
|---|---|:--:|
| **CDNOW** | Fader-Hardie (2001), Simon (2025), Xie (2020/22), Jasek (2018/19), most BTYD papers | ✅ |
| **Online Retail (I/II)** | many applied CLV/ML-CLV papers | ✅ (II) |
| **Grocery / supermarket panels** | Ehrenberg/Dirichlet line, Platzer (2016) | ✅ |
| **Telecom churn (IBM/UCI/Kaggle)** | the *contractual* ML-churn field (Imani, Manzoor, Sci Rep, ChurnNet, Mufti) | n/a — **contractual, out of scope by design** |
| **Uplift sets (Hillstrom/Criteo/X5/Lenta)** | the uplift/HTE field (Devriendt, Rößler, UpliftBench) | ⬜ (Gear 2) |

**Observation (feeds the coverage verdict):** the non-contractual/BTYD tradition and the uplift
tradition use **disjoint** datasets — BTYD papers use transaction logs *without* treatment; uplift
papers use treatment sets *without* a clean tx log. **Gear 2's data contribution** is precisely to
bridge them: build the BTYD state on a tx log that *also* carries a treatment (Dunnhumby, X5, Lenta,
Starbucks), or inject a known treatment into the validated simulator (Stage A).

---

## 5. Not-yet-used, free, worth adding  (prioritized shortlist)

1. 🔴 **Dunnhumby Complete Journey** — already on disk; promote to Gear 2 uplift (§1).
2. 🔴 **Hillstrom** — `sklift` one-liner; Gear 2 Stage-B smoke.
3. 🔴 **X5 RetailHero** — best tx-log + treatment fit (needs free registration).
4. 🟡 **Instacart** — Gear 1 breadth (modern grocery) + Gear 2 (no treatment, state only).
5. 🟡 **H&M / Retailrocket** — fill the apparel + e-comm-events coverage cells.
6. 🟡 **Lenta / Starbucks** — grocery + loyalty-app treatment.
7. ⚪ **Criteo, MegaFon** — scale/ads; lower fit.

---

## 6. Access / licence notes

- `sklift` auto-downloads Hillstrom, Criteo v2, Lenta; X5 & MegaFon are login-walled (free hackathon
  registration). Kaggle sets need the Kaggle API + accepting each competition's rules.
- Record every added dataset's **licence** and a `read_me` before committing loaders (`src/datasets.py`
  is the existing loader hub — extend it, mirror the `data/<name>/` layout).
- Keep raw data out of git per repo convention; add a loader + a small `read_me`, not the bytes.

*Tracking: tick Status here as datasets land; substance (schema, treatment definition, BTYD-fit notes)
goes in `src/datasets.py` docstrings + `docs/datasets.md`.*
