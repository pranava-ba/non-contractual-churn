# Pareto/NBD Extension: Probabilistic Forecasting & Calibration

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Documentation Status](https://readthedocs.org/projects/pareto-nbd-extension/badge/?version=latest)](https://pareto-nbd-extension.readthedocs.io/)
[![Interactive Pyodide WebApp](https://img.shields.io/badge/WebAssembly-Pyodide_App-emerald.svg)](docs/interactive.html)

Official implementation and extensions for **"Non-contractual churn with MCMC: are Pareto/NBD purchase forecasts calibrated?"** (Pranava BA & Vyasa R Rajesawaran).

This repository evaluates continuous-time Buy-Till-You-Die (BTYD) forecasts using **proper scoring rules (CRPS, Log Score)**, **randomized PIT diagnostics**, and **TOST equivalence tests**. It includes implementations for **Pareto/NBD**, **Pareto/GGG** (Gamma renewal regularity), **Purchase Timing ($t_{x+1}$)** forecasting, and **Gamma-Gamma Probabilistic Customer Lifetime Value (CLV)**.

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
- **Interactive WebAssembly Dashboard**:
  - `docs/interactive.html`: Standalone, dark-mode Pyodide WebAssembly single-page web app running live MCMC/MLE simulations in the browser.

---

## Repository Structure

```
pareto-nbd-extension/
├── data/                       # CDNow & Grocery benchmark event logs
├── docs/                       # ReadTheDocs Sphinx documentation & Pyodide app
│   ├── index.rst
│   ├── conf.py
│   ├── interactive.html        # Pyodide WebAssembly App
│   └── theory_variance_decomposition.md
├── paper/                      # Springer Nature manuscript (.tex, .pdf, figures)
│   ├── manuscript.tex
│   └── figures/                # Vector (PDF/EPS) and PNG figures
├── src/                        # Core Python library
│   ├── estimate.py
│   ├── estimate_ggg.py
│   ├── score.py
│   ├── timing.py               # Extension B
│   ├── clv.py                  # Extension E
│   ├── simulate.py
│   ├── analyze.py
│   └── empirical.py
├── tests/                      # Automated pytest unit testing suite
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

```bash
python src/run_study.py
python src/analyze.py
python src/empirical.py
```

---

## Analytical Variance Decomposition

The paper proves why MCMC and MLE produce statistically equivalent forecast distributions via the law of total variance:

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
