# Installation & Quickstart Guide

## Prerequisites
- Python >= 3.9
- `numpy`, `scipy`, `pandas`, `matplotlib`, `seaborn`

## Local Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/pranava-baascaran/pareto-nbd-extension.git
cd pareto-nbd-extension
pip install -e .
```

To install development dependencies (testing and documentation):

```bash
pip install -e ".[dev]"
```

## Running Unit Tests

Run the full pytest suite:

```bash
pytest tests/ -v
```

## Reproducing Paper Results

Run the simulation study and generate figures:

```bash
python src/run_study.py
python src/analyze.py
python src/empirical.py
```
