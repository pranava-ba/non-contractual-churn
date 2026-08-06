<div align="center">

<h1>Pareto/NBD Extension: Probabilistic Forecasting &amp; Calibration</h1>

<p><em>Are non-contractual customer-purchase forecasts calibrated? — a statistical vs. machine-learned benchmark.</em></p>

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square"></a>
  <a href="https://non-contractual-churn.readthedocs.io/en/latest/"><img alt="Documentation Status" src="https://readthedocs.org/projects/non-contractual-churn/badge/?version=latest&amp;style=flat-square"></a>
  <a href="https://github.com/pranava-ba/non-contractual-churn"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-repository-181717.svg?style=flat-square&amp;logo=github"></a>
</p>

</div>

Implementation and extensions for **"Non-contractual churn with MCMC: are Pareto/NBD purchase forecasts calibrated?"** (Pranava BA & Vyasa R Rajesawaran).

This repository evaluates continuous-time Buy-Till-You-Die (BTYD) forecasts using **proper scoring rules (CRPS, Log Score)**, **randomized PIT diagnostics**, and **TOST equivalence tests**. It includes implementations for **Pareto/NBD**, **Pareto/GGG** (Gamma renewal regularity), **Purchase Timing ($t_{x+1}$)** forecasting, and **Gamma-Gamma Probabilistic Customer Lifetime Value (CLV)**.

It then runs a second, larger study — **statistical vs. machine-learned** — bringing gradient-boosted and neural forecasters into the *same* calibration lens across counts, value, churn and timing, on **seven public cohorts** (active rates 1.6%→96%). The finding: calibration is governed by the **parametric count assumption** the BTYD family shares — not by the estimation method or the model variant — and where it breaks it can be repaired model-agnostically (**Conformalized BTYD**) or structurally (**Pareto/GGG**).

📖 **Full documentation:** **<https://non-contractual-churn.readthedocs.io/en/latest/>**

---

## Key Features

| Area | Module(s) | What it does |
|---|---|---|
| Parameter estimation | `estimate.py`, `estimate_ggg.py` | Abe (2009) MCMC Gibbs sampler + robust multi-start MLE; common- $k$ Pareto/GGG sampler for inter-purchase regularity |
| Probabilistic scoring | `score.py` | Sample-based CRPS, discrete log score, Czado et al. (2009) randomized PIT, coverage, sharpness |
| Timing *(Ext. B)* | `timing.py` | Posterior-predictive next-purchase wait-time distribution $t_{x+1}$ for active customers |
| Probabilistic CLV *(Ext. E)* | `clv.py` | Gamma-Gamma spend process combined with purchase-count forecasts |
| Statistical vs. ML | `ml_benchmark.py` | Poisson / hurdle / distribution-free **quantile** gradient-boosted RFM forecasters, same CRPS/PIT engine |
| Conformalized BTYD | `conformal.py` | One-pass held-out recalibration that restores interval coverage without changing the model |
| Amortized inference | `amortized.py` | One-forward-pass neural Pareto/NBD estimator (matches MCMC calibration) |
| BG/NBD variant | `estimate_bgnbd.py` | Interchangeable variant scored under the same lens |
| Deep CLV | `clv_benchmark.py`, `clv_data.py` | Structural CLV vs. a deep **zero-inflated-lognormal (ZILN)** value model |
| Churn calibration | `churn.py` | Calibration of the active-customer probability $P(\text{active})$ (ECE / Brier) |
| Datasets | `datasets.py`, `empirical.py` | Loaders for public cohorts (CDNow, Online Retail II, Olist, Dunnhumby, Ta-Feng, Grocery) |

---

## Installation & Quickstart

```bash
# Clone repository
git clone https://github.com/pranava-ba/non-contractual-churn.git
cd non-contractual-churn

# Install in editable mode
pip install -e .

# Install with development & test dependencies
pip install -e ".[dev]"
```

### Running Unit Tests

```bash
pytest tests/ -v
```

### Running Analysis & Generating Figures

The core calibration study (Phase 1):

```bash
python src/run_study.py
python src/analyze.py
python src/empirical.py
```

The statistical-vs-ML benchmark (Phase 2) — each runner writes a confirmed multi-seed
`results/*_summary.csv`:

```bash
python src/run_ml_study.py          # BTYD vs. gradient-boosted RFM forecasters
python src/run_conformal_study.py   # Conformalized BTYD (interval repair)
python src/run_amortized_check.py   # amortized neural estimator vs. MCMC
python src/run_bgnbd_study.py       # BG/NBD variant
python src/run_clv_study.py         # structural CLV vs. deep ZILN
python src/run_churn_study.py       # P(active) calibration
python src/run_timing_study.py      # Pareto/NBD vs. Pareto/GGG next-purchase timing
```

Or reproduce everything end-to-end:

```bash
make reproduce
```

---

## Analytical Variance Decomposition

The paper shows why MCMC and MLE produce statistically equivalent forecast distributions via a law-of-total-variance scaling argument:

$$
\mathrm{Var}(x^{\ast}_{i} \mid \text{data}) = \mathbb{E}_{\theta \mid \text{data}}\left[\mathrm{Var}(x^{\ast}_{i} \mid \theta, \text{data})\right] + \mathrm{Var}_{\theta \mid \text{data}}\left(\mathbb{E}[x^{\ast}_{i} \mid \theta, \text{data}]\right)
$$

The first term (individual stochasticity in $\lambda_i, \mu_i, \tau_i$ compounded with Poisson count noise) is $\mathcal{O}(1)$ and dominates. The second term (population parameter uncertainty) shrinks as $\mathcal{O}(1/N)$ with cohort size $N \ge 100$.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ by **Pranava BA** & **Vyasa R Rajesawaran** · Department of CSE (AI & ML), Easwari Engineering College.

</div>
