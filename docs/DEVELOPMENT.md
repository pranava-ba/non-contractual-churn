# Developer Guide

Everything you need to set up a workspace, run the study, build the paper, and keep the
code clean.

## 1. Prerequisites

- **Python ≥ 3.9** (developed on 3.13)
- A C-capable toolchain is *not* required — the stack is pure `numpy`/`scipy`/`pandas`/
  `matplotlib`.
- For the paper: a LaTeX distribution with `latexmk` (the Springer Nature `sn-jnl` class
  and `bst/` styles ship in `paper/`; the class additionally needs the `sttools`/`cuted`
  package).

## 2. Environment setup

```bash
git clone https://github.com/pranava-baascaran/pareto-nbd-extension.git
cd pareto-nbd-extension

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"          # editable install + pytest/sphinx/myst
```

## 3. Repository layout

```
src/        core library (estimation, scoring, extensions, runners)
tests/      pytest suite
docs/        Sphinx + Pyodide app + this guide
paper/       Springer Nature manuscript (single-file .tex, figures, tables)
data/        CDNow & Grocery public benchmarks
results/     generated CSVs, logs, and figures
```

## 4. Running the study

Scripts are runnable directly (they add `src/` to `sys.path`) and are **resumable** and
**time-budgeted** where the run is long.

```bash
python src/run_study.py --grid smallsample --reps 15   # main simulation grid
python src/run_ggg.py --reps 15                         # Pareto/NBD vs Pareto/GGG loop
python src/run_misspec.py ; python src/run_mixture.py   # misspecification stress-tests
python src/empirical.py                                 # CDNow + Grocery validation

python src/analyze.py                                   # aggregate + Wilcoxon + figs 1–2
python src/make_tables.py ; python src/make_tables_sn.py# LaTeX tables + TOST numbers
python src/pit_figures.py ; python src/ggg_report.py    # figs 3, 5
python src/convergence.py                               # R-hat / ESS + fig 6
```

Self-tests: most modules have a `__main__` block (e.g. `python src/estimate.py` runs a
parameter-recovery check; `python src/estimate_ggg.py` runs the `k=1` unit test).

## 5. Building the paper

```bash
cd paper
latexmk -pdf manuscript.tex          # -> manuscript.pdf (23 pp)
```

Notes: the manuscript is a **single self-contained `.tex`** per Springer Nature rules
(no `\input`) — regenerate table bodies with `make_tables*.py` and paste. Tables use the
class's rules (`\toprule/\midrule/\botrule`, `booktabs` for `\cmidrule`). Author the
`.tex` with an editor, not shell heredocs (they mangle `\\`).

## 6. Testing

```bash
pytest tests/ -q          # full suite
pytest tests/ -k clv -v   # a subset
```

Tests must cover **numerical correctness**, not just shapes — e.g. `test_extensions.py`
asserts posterior spend tracks observed spend, and `test_estimate.py` asserts parameter
recovery. Add a numerical assertion for any new estimator or scorer.

## 7. Code style

- **Formatting:** [`black`](https://black.readthedocs.io/) (line length 100).
- **Linting:** [`flake8`](https://flake8.pycqa.org/) (configure `max-line-length = 100`,
  ignore `E203, W503` for `black` compatibility).

```bash
black src/ tests/
flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
```

Keep the house style: pure-`numpy` vectorisation over Python loops, docstrings that state
the *math* a function realises, and explicit RNG seeding.

## 8. Reproducibility

- Every stochastic routine takes a `seed`; runners derive per-cell seeds deterministically
  (e.g. `seed = 1000*N + 7*T + rep`).
- Numerical guards are explicit: `np.seterr(over="ignore", invalid="ignore",
  divide="ignore")` in runners, and overflow rejection in `fit_mle`.
- Long runs write incremental CSVs and can `--resume`.

## 9. Building the docs

```bash
pip install -e ".[dev]"
sphinx-build -b html docs docs/_build/html
```

`myst_parser` renders the `.md` files (including this one) into the Sphinx site;
`docs/interactive.html` is the standalone Pyodide app.

## 10. Debugging tips

- **MCMC mixing:** the dropout parameters `(s, β, μ)` are weakly identified and mix
  slowly; use dispersed `init` and long chains (see `convergence.py`) when diagnosing.
- **MLE divergence:** if `E(λ)` looks 10× off, check for a spurious positive
  log-likelihood — the bounded/rejecting optimiser in `fit_mle` prevents it.
- **GGG quadrature:** `fit_ggg(..., n_quad=)` controls the alive-probability integral
  accuracy; it must reproduce the Pareto/NBD closed form at `k=1`.
