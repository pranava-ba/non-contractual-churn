# pareto-nbd-extension — developer entry points.
# `make reproduce` regenerates every result, table and figure from scratch.

.PHONY: help install test lint format docs paper reproduce clean

help:
	@echo "install    - editable install with dev + ml extras"
	@echo "test       - run the pytest suite"
	@echo "lint       - flake8 style check"
	@echo "format     - black auto-format"
	@echo "docs       - build the Sphinx documentation site"
	@echo "paper      - compile the Springer Nature manuscript (latexmk)"
	@echo "reproduce  - run the full study pipeline (long-running: MCMC over many cohorts)"
	@echo "clean      - remove caches and LaTeX/docs build artifacts"

install:
	pip install -e ".[dev,ml]"

test:
	pytest -q

lint:
	flake8 src tests --max-line-length=100 --extend-ignore=E203,W503

format:
	black src tests

docs:
	sphinx-build -b html docs docs/_build/html

paper:
	cd paper && latexmk -pdf manuscript.tex

# Full reproduction. Each step writes to results/; the table/figure steps read those CSVs.
reproduce:
	python src/run_study.py   --grid smallsample --reps 15 --out main_results.csv
	python src/run_study.py   --grid extreme --reps 15 --cvlo 1.8 --cvhi 2.5 --out extreme_results.csv
	python src/empirical.py
	python src/run_ggg.py     --reps 15
	python src/run_misspec.py --reps 15
	python src/run_mixture.py --reps 15
	python src/convergence.py
	python src/run_ml_study.py
	python src/analyze.py
	python src/make_tables.py
	python src/make_tables_sn.py
	python src/pit_figures.py
	python src/ggg_report.py
	@echo "Reproduction complete: tables in paper/tables/, figures in results/figures/ and paper/figures/."

clean:
	rm -rf .pytest_cache docs/_build
	find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} +
	cd paper && rm -f manuscript.aux manuscript.log manuscript.out manuscript.fls \
	                  manuscript.fdb_latexmk manuscript.bbl manuscript.blg
