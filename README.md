# Pareto/NBD Extension: Probabilistic Forecasting & Calibration

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Documentation Status](https://readthedocs.org/projects/pareto-nbd-extension/badge/?version=latest)](https://pareto-nbd-extension.readthedocs.io/)
[![Interactive Pyodide WebApp](https://img.shields.io/badge/WebAssembly-Pyodide_App-emerald.svg)](docs/interactive.html)

Official implementation and extensions for **"Non-contractual churn with MCMC: are Pareto/NBD purchase forecasts calibrated?"** (Pranava BA & Vyasa R Rajesawaran).

This repository evaluates continuous-time Buy-Till-You-Die (BTYD) forecasts using **proper scoring rules (CRPS, Log Score)**, **randomized PIT diagnostics**, and **TOST equivalence tests**. It includes implementations for **Pareto/NBD**, **Pareto/GGG** (Gamma renewal regularity), **Purchase Timing ($t_{x+1}$)** forecasting, and **Gamma-Gamma Probabilistic Customer Lifetime Value (CLV)**.

It then runs a second, larger study — **statistical vs. machine-learned** — bringing gradient-boosted and neural forecasters into the *same* calibration lens across counts, value, churn and timing, on **seven public cohorts** (active rates 1.6%→96%). The finding: calibration is governed by the **parametric count assumption** the BTYD family shares — not by the estimation method or the model variant — and where it breaks it can be repaired model-agnostically (**Conformalized BTYD**) or structurally (**Pareto/GGG**). New here? Start with the **[selection guide](docs/selection.md)**.

---

## Key Features

- **Robust Parameter Estimation**:
  - `src/estimate.py`: Pure NumPy/SciPy Abe (2009) MCMC Gibbs sampler & robust multi-start bounded Maximum Likelihood Estimator (MLE).
  - `src/estimate_ggg.py`: Common-$k$ Pareto/GGG sampler for inter-purchase regularity.
- **Probabilistic Scoring Suite**:
  - `src/score.py`: Sample-based CRPS, Laplace-smoothed discrete Log Score, Czado et al. (2009) randomized PIT, coverage, and sharpness diagnostics.
- **Extensions**:
  - `src/timing.py` *(Extension B)*: Posterior-predictive wait-time distributions ($t_{x+1}$) for active customers.
  - `src/clv.py` *(Extension E)*: Gamma-Gamma spend process combined with purchase-count forecasts for probabilistic CLV.
- **Statistical vs. machine-learned** *(the calibration benchmark)*:
  - `src/ml_benchmark.py`: Poisson / hurdle / **distribution-free quantile** gradient-boosted RFM forecasters, scored under the same CRPS/PIT engine. → [docs](docs/ml_benchmark.md)
  - `src/conformal.py`: **Conformalized BTYD** — a one-pass held-out recalibration that restores interval coverage without changing the model. → [docs](docs/conformal.md)
  - `src/amortized.py`: A one-forward-pass **amortized neural estimator** for the Pareto/NBD (matches MCMC calibration). → [docs](docs/amortized.md)
  - `src/estimate_bgnbd.py`: **BG/NBD** variant under the same lens (interchangeable with Pareto/NBD). → [docs](docs/bgnbd.md)
  - `src/clv_benchmark.py` + `src/clv_data.py`: Structural CLV vs. a **deep zero-inflated-lognormal (ZILN)** value model. → [docs](docs/clv_benchmark.md)
  - `src/churn.py`: Calibration of the active-customer probability $P(\text{active})$ (ECE / Brier). → [docs](docs/churn.md)
  - `src/datasets.py`: Loaders for four public benchmarks (Online Retail II, Olist, Dunnhumby, Ta-Feng). → [docs](docs/datasets.md)
- **Interactive WebAssembly Dashboard**:
  - `docs/interactive.html`: No-server-required, dark-mode Pyodide WebAssembly single-page web app running live MCMC/MLE simulations in the browser (loads Pyodide, Chart.js and fonts from CDNs, so it needs a network connection).

---

## 📖 Documentation Directory

- 🧭 [Selection Guide](docs/selection.md): **Start here.** Which forecaster to use, when, and why — the practitioner decision table distilling the whole statistical-vs-ML study.
- 🤖 Statistical vs. machine-learned: [ML benchmark](docs/ml_benchmark.md) · [Conformalized BTYD](docs/conformal.md) · [Amortized inference](docs/amortized.md) · [BG/NBD](docs/bgnbd.md) · [Probabilistic CLV](docs/clv_benchmark.md) · [Churn calibration](docs/churn.md) · [Datasets](docs/datasets.md).
- 📐 [Technical Architecture](docs/ARCHITECTURE.md): Deep dive into the probabilistic model math, the Abe MCMC and Pareto/GGG samplers, the SPP predictive identity, the proper-scoring evaluation framework, the statistical-vs-ML extension, pipeline data flow, and data schemas.
- 💻 [Developer Guide](docs/DEVELOPMENT.md): Workspace setup, running the study, building the Springer Nature paper, `pytest`, linting rules (`black`/`flake8`), and reproducibility conventions.
- 🤝 [Contributing Guidelines](CONTRIBUTING.md): PR workflow, Conventional Commit requirements, issue reporting, and the numerical-test standard for new estimators and scorers.
- 🗺️ [Project Timeline & Roadmap](TIMELINE.md): Milestone progression, release history, and the feature roadmap (model/ML benchmark, heterogeneous-`k` Pareto/GGG, covariates).
- 📜 [Changelog](CHANGELOG.md): Formal release logs adhering to Keep a Changelog.
- 🔒 [Security Policy](SECURITY.md): Dependency safety, safe-execution notes, and responsible disclosure.

---

## Repository Structure

```
pareto-nbd-extension/
├── data/                       # Public event logs: CDNow, Grocery, Online Retail II,
│                               #   Olist, Dunnhumby, Ta-Feng
├── docs/                       # ReadTheDocs Sphinx documentation & Pyodide app
│   ├── index.rst
│   ├── selection.md            # ← the decision guide (start here)
│   ├── ARCHITECTURE.md
│   ├── ml_benchmark.md  conformal.md  amortized.md  bgnbd.md
│   ├── clv_benchmark.md  churn.md  datasets.md
│   ├── interactive.html        # Pyodide WebAssembly App
│   └── theory_variance_decomposition.md
├── src/                        # Core Python library
│   ├── simulate.py  estimate.py  estimate_ggg.py  estimate_bgnbd.py
│   ├── score.py  timing.py  clv.py           # scoring + Extensions B/E
│   ├── ml_benchmark.py  conformal.py  amortized.py     # statistical vs. ML
│   ├── clv_benchmark.py  clv_data.py  covariate_benchmark.py  churn.py
│   ├── datasets.py  empirical.py             # cohort loaders
│   ├── run_*.py                              # experiment runners (one per study)
│   └── analyze.py  make_tables*.py  convergence.py
├── results/                    # Confirmed multi-seed *_summary.csv outputs
├── tests/                      # Automated pytest suite (test_*.py)
├── Makefile                    # `make reproduce` / test / lint / docs
├── pyproject.toml              # PEP 621 Python package configuration
├── LICENSE                     # MIT License
└── README.md
```

---

## Installation & Quickstart

```bash
# Clone repository
git clone https://github.com/pranava-baascaran/pareto-nbd-extension.git
cd pareto-nbd-extension

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

$$\mathrm{Var}(x^*_i \mid \text{data}) = \mathbb{E}_{\theta \mid \text{data}}\!\left[\mathrm{Var}(x^*_i \mid \theta, \text{data})\right] + \mathrm{Var}_{\theta \mid \text{data}}\!\left(\mathbb{E}[x^*_i \mid \theta, \text{data}]\right)$$

The first term (individual stochasticity in $\lambda_i, \mu_i, \tau_i$ compounded with Poisson count noise) is $\mathcal{O}(1)$ and dominates. The second term (population parameter uncertainty) shrinks as $\mathcal{O}(1/N)$ with cohort size $N \ge 100$.

---

## Citation

If you use this codebase or paper in your research, please cite:

```bibtex
@article{pranava2026pareto,
  title={Non-contractual churn with MCMC: are Pareto/NBD purchase forecasts calibrated?},
  author={BA, Pranava and Rajesawaran, Vyasa R},
  journal={Springer Nature},
  year={2026}
}
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
