---
title: "Reading path + tooling — non-contractual churn / BTYD"
type: reference
updated: 2026-09-20
role: The minimum you must read (and in what order) to understand the field, plus the
      software people actually use. Two SEPARATE diagrams — a paper reading-path
      (reading_path.mmd) and a code/tooling map (tooling_map.mmd) — over the 127-paper
      Tier-A spine (CORE_READING_LIST.md).
---

# What to read, in what order — and what tools people use

You do **not** read 127 papers. This splits into two views, kept deliberately separate:

- **§3 the reading path** — ~30 *papers* wired by "read-X-before-Y", with an 8-paper
  critical path (`reading_path.mmd`).
- **§4 the tooling map** — the *code / packages / solutions*, mapped to the models they
  implement (`tooling_map.mmd`).

---

## 1. Tools, packages & solutions people actually use

The field has mature, standard implementations — you rarely code a Pareto/NBD from scratch.

### R (the field's native habitat — most models originate here)
| Package | What it gives you | Notes |
|---|---|---|
| **`BTYD`** | Pareto/NBD, BG/NBD, BG/BB | the original CRAN package (Dwyer, Wadsworth et al.); paired with McCarthy & Wadsworth's walkthrough |
| **`BTYDplus`** (Platzer 2021) | MBG/NBD, MBG/CNBD-*k*, **Pareto/GGG**, Pareto/NBD (Abe HB) | the research-grade superset; timing-regularity + HB models live here |
| **`CLVTools`** | Pareto/NBD, BG/NBD, GGompertz/NBD, **Gamma-Gamma spending**, time-varying covariates | actively maintained (Bachmann, Meierer, Näf); the modern go-to for applied CLV in R |

### Python
| Package | What it gives you | Notes |
|---|---|---|
| **`lifetimes`** (Davidson-Pilon) | BG/NBD, Pareto/NBD, MBG/NBD, Gamma-Gamma | *the* classic Python BTYD lib — **now unmaintained/archived**; huge install base |
| **`PyMC-Marketing`** (CLV module) | BG/NBD, Pareto/NBD, Gamma-Gamma, Shifted-Beta-Geo, **full Bayesian/MCMC** | the maintained **successor** to `lifetimes` (PyMC Labs); covariates + posterior uncertainty |

### Reference math
- **Bruce Hardie's technical notes + Excel spreadsheets** (brucehardie.com) — the canonical,
  citable derivations for BG/NBD, Pareto/NBD, BG/BB, Gamma-Gamma. Most packages implement
  these notes. **Start here for the equations.**

### Evaluation / calibration (this project's toolkit — the lens the BTYD packages *don't* give you)
| Tool | Use |
|---|---|
| **`scoringRules`** (R) / **`properscoring`** (Python) | CRPS, log score, proper scoring rules |
| **`uncertainty-toolbox`**, sklearn `calibration`, **`MAPIE`/`crepes`** (conformal) | reliability, ECE, PIT, calibrated/conformal prediction |

### ML / DL for CLV & churn
- **ZILN** (zero-inflated lognormal) loss — Wang et al. 2019, in TensorFlow Probability.
- **RNN / seq2seq** customer-base models — Valendin 2022, Bauer & Jannach 2021 (custom).
- **Gradient boosting** (XGBoost / LightGBM) — the workhorse for churn *classification*.

> **The gap this project fills:** BTYD packages give you *forecasts*; ML libs give you
> *point accuracy*; **none** ship a *probability-calibration* evaluation of customer
> forecasts. That is the manuscript's contribution (the purple node in §4).

---

## 2. The critical path — read these 8, in order

If you read nothing else, read this spine top-to-bottom:

1. **Fader & Hardie (2009), "Probability Models for Customer-Base Analysis"** — the tutorial. Orientation.
2. **Ehrenberg (1959), NBD** — why purchasing = Poisson-Gamma. The statistical root.
3. **Schmittlein, Morrison & Colombo (1987), Pareto/NBD** — the founding paper: latent (unobserved) dropout.
4. **Fader, Hardie & Lee (2005), BG/NBD** — the closed-form variant that put it in every toolkit.
5. **Abe (2009), HB Pareto/NBD** — how it's estimated by MCMC (+ covariates).
6. **Simon (2025)** — the source paper you extend: MCMC vs MLE vs heuristics.
7. **Gneiting & Raftery (2007) + Czado, Gneiting & Held (2009)** — proper scoring rules & PIT: the evaluation lens.
8. **Phase 1 → Phase 2 (this project)** — the calibration reframing, then BTYD-vs-ML by calibration.

Everything else deepens one branch of this spine.

---

## 3. Reading diagram — *papers only* (`reading_path.mmd`)

Edges mean **"read the source before the target"**. Bold blue = the 8-paper critical path;
orange = the founding paper; green = this project; red = screen against the novelty claim.

```mermaid
flowchart TD
  classDef crit fill:#dbeafe,stroke:#1a56db,stroke-width:3px,color:#111827;
  classDef found fill:#ffedd5,stroke:#c2410c,stroke-width:2px,color:#111827;
  classDef ours fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#111827;
  classDef screen fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#111827;

  subgraph ORI["1. Orientation - start here"]
    FH09["Fader and Hardie 2009<br>Probability Models (tutorial)"]
    MC14["McCarthy and Wadsworth 2014<br>BTYD R walkthrough"]
  end
  subgraph FND["2. Statistical foundations"]
    EHR59["Ehrenberg 1959<br>NBD (purchase counts)"]
    DIR84["Goodhardt et al 1984<br>NBD-Dirichlet (context)"]
    SMC87["Schmittlein-Morrison-Colombo 1987<br>Pareto/NBD - FOUNDING"]
  end
  subgraph VAR["3. BTYD model variants"]
    BGN05["Fader-Hardie-Lee 2005<br>BG/NBD (closed form)"]
    RFM05["Fader-Hardie-Lee 2005<br>RFM and CLV iso-value"]
    BGBB10["Fader-Hardie 2010<br>BG/BB (discrete, donations)"]
    GG12["Bemmaor-Glady 2012<br>Gamma/Gompertz sudden death"]
    GGG16["Platzer-Reutterer 2016<br>Pareto/GGG (timing)"]
  end
  subgraph EST["4. Estimation and benchmarking"]
    ABE09["Abe 2009<br>HB Pareto/NBD (MCMC)"]
    WUB08["Wubben-von Wangenheim 2008<br>heuristics baseline"]
    SIM25["Simon 2025<br>MCMC vs MLE - SOURCE"]
  end
  subgraph CLV["5. CLV terrain"]
    RK00["Reinartz-Kumar 2000<br>noncontractual profitability"]
    GUP06["Gupta et al 2006<br>Modeling CLV (the map)"]
  end
  subgraph MLC["6. ML / deep learning for CLV"]
    CHA17["Chamberlain et al 2017<br>CLV embeddings"]
    WANG19["Wang et al 2019<br>ZILN deep CLV"]
    VAL22["Valendin et al 2022<br>RNN customer-base"]
    BAU21["Bauer-Jannach 2021<br>seq2seq CLV"]
    XIE20["Xie 2020<br>Pareto/NBD vs neural net"]
  end
  subgraph CHU["7. Non-contractual churn classification"]
    BUCK05["Buckinx-Van den Poel 2005<br>partial defection (FMCG)"]
    MIG12["Migueis et al 2012<br>partial churn"]
  end
  subgraph EVA["8. Forecast evaluation and calibration"]
    GR07["Gneiting-Raftery 2007<br>proper scoring rules"]
    GBR07["Gneiting et al 2007<br>calibration and sharpness"]
    CGH09["Czado et al 2009<br>PIT for count data"]
    KUL18["Kuleshov et al 2018<br>calibrated regression"]
  end
  subgraph FRT["9. Frontier and this project"]
    ULR26["Ulrich 2026<br>aliveness calibration"]
    P1["Phase 1<br>calibration lens (ours)"]
    P2["Phase 2<br>BTYD vs ML by calibration (ours)"]
  end

  FH09 --> SMC87
  MC14 --> BGN05
  EHR59 --> SMC87
  DIR84 --> SMC87
  SMC87 --> BGN05
  SMC87 --> ABE09
  SMC87 --> GG12
  SMC87 --> GGG16
  BGN05 --> RFM05
  BGN05 --> BGBB10
  BGN05 --> GGG16
  RFM05 --> GUP06
  ABE09 --> SIM25
  BGN05 --> SIM25
  WUB08 --> SIM25
  RK00 --> GUP06
  GUP06 --> CHA17
  CHA17 --> WANG19
  CHA17 --> VAL22
  BGN05 --> VAL22
  VAL22 --> BAU21
  SMC87 --> XIE20
  WANG19 --> P2
  VAL22 --> P2
  XIE20 --> P2
  BUCK05 --> MIG12
  BUCK05 --> P2
  GR07 --> GBR07
  GR07 --> CGH09
  GBR07 --> CGH09
  CGH09 --> P1
  KUL18 --> P2
  SIM25 --> P1
  P1 --> P2
  GGG16 --> P2
  ULR26 --> P2

  class SMC87 found
  class FH09 crit
  class EHR59 crit
  class BGN05 crit
  class ABE09 crit
  class SIM25 crit
  class GR07 crit
  class CGH09 crit
  class P1 ours
  class P2 ours
  class XIE20 screen
```

---

## 4. Tooling map — *code / packages* (`tooling_map.mmd`)

Which package implements which model, and where the evaluation/ML stack sits. Green =
maintained; red = archived (`lifetimes`); orange = the reference math; purple = the gap
this project fills.

```mermaid
flowchart TD
  classDef maint fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#111827;
  classDef dep fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#111827;
  classDef math fill:#ffedd5,stroke:#c2410c,stroke-width:2px,color:#111827;
  classDef gap fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#111827;

  MATH["Bruce Hardie technical notes + Excel<br>(brucehardie.com) - canonical math"]
  subgraph MODELS["Models (what you estimate)"]
    PNBD["Pareto/NBD"]
    BGNBD["BG/NBD"]
    BGBB["BG/BB (discrete)"]
    PGGG["Pareto/GGG (timing)"]
    GGOM["Gamma/Gompertz-NBD"]
    HBP["HB Pareto/NBD (MCMC)"]
    GGSP["Gamma-Gamma (spending)"]
  end
  subgraph RPKG["R packages"]
    BTYD["BTYD"]
    BTYDPLUS["BTYDplus"]
    CLVTOOLS["CLVTools (maintained)"]
  end
  subgraph PYPKG["Python packages"]
    LIFETIMES["lifetimes (archived)"]
    PYMC["PyMC-Marketing (maintained)"]
  end
  subgraph EVAL["Evaluation / calibration (BTYD packages lack this)"]
    SCORING["scoringRules / properscoring<br>CRPS, log score"]
    CONF["MAPIE / crepes<br>conformal prediction"]
    SKCAL["sklearn calibration<br>uncertainty-toolbox (ECE, PIT)"]
  end
  subgraph MLST["ML for CLV / churn"]
    ZILN["ZILN loss<br>(TensorFlow Probability)"]
    RNN["RNN / seq2seq (custom)"]
    GBM["XGBoost / LightGBM"]
  end

  MATH --> BTYD
  MATH --> BTYDPLUS
  MATH --> CLVTOOLS
  MATH --> LIFETIMES
  MATH --> PYMC
  BTYD --> PNBD
  BTYD --> BGNBD
  BTYD --> BGBB
  BTYDPLUS --> PNBD
  BTYDPLUS --> PGGG
  BTYDPLUS --> HBP
  CLVTOOLS --> PNBD
  CLVTOOLS --> BGNBD
  CLVTOOLS --> GGOM
  CLVTOOLS --> GGSP
  LIFETIMES --> BGNBD
  LIFETIMES --> PNBD
  LIFETIMES --> GGSP
  PYMC --> BGNBD
  PYMC --> PNBD
  PYMC --> GGSP
  PYMC --> HBP
  ZILN --> GGSP
  RNN --> PNBD
  GBM --> BGNBD

  GAP["This project's contribution:<br>evaluate these forecasts by<br>PROBABILITY CALIBRATION<br>(PIT / CRPS / coverage)"]
  PNBD --> GAP
  ZILN --> GAP
  SCORING --> GAP

  class CLVTOOLS maint
  class PYMC maint
  class LIFETIMES dep
  class MATH math
  class GAP gap
```

---

## 5. Per-track order (with the one-line "why")

- **① Orientation:** FH09 tutorial → (Hardie notes for the math) → MC14 for hands-on R.
- **② Foundations:** EHR59 (why Poisson-Gamma) → SMC87 (latent dropout — the whole idea).
- **③ Variants:** BG/NBD (easy) → then pick by need: BG/BB (discrete/donations), Pareto/GGG
  (timing), Gamma/Gompertz (flexible dropout); RFM05 adds the Gamma-Gamma **spending** model.
- **④ Estimation:** ABE09 (MCMC) + WUB08 (the heuristics baseline you must beat) → SIM25 (source).
- **⑤ CLV terrain:** RK00 (noncontractual profitability myth-busting) → GUP06 (the field map).
- **⑥ ML:** CHA17 → WANG19 (ZILN) / VAL22 (RNN, the closest ML-vs-BTYD) → BAU21; **screen XIE20**.
- **⑦ Churn classification:** BUCK05 (canonical non-contractual) → MIG12.
- **⑧ Calibration lens:** GR07 → GBR07 → CGH09 (PIT for counts) → KUL18 (recalibration).
- **⑨ Frontier/ours:** ULR26 (BTYD aliveness calibration, concurrent) → Phase 1 (reframing)
  → Phase 2 (BTYD vs ML by calibration).

> Depth control: the **critical path (§2)** is the trunk; each numbered track is a branch you
> read only as deep as your question needs. The other ~600 Tier-B papers
> (`genealogy_triage.csv`) are for citation-chasing, not cover-to-cover reading.
