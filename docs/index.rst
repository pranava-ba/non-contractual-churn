Pareto/NBD Extension Documentation
=====================================

Welcome to the documentation for the **Pareto/NBD Extension** — a Python framework for the
**probabilistic evaluation of customer-base forecasts**.

The project has two halves. The first asks whether classical Buy-Till-You-Die (BTYD)
forecasts are *calibrated*, and whether the estimation method matters: it evaluates
Pareto/NBD purchase forecasts with proper scoring rules (CRPS, log score), calibration
diagnostics (randomized PIT, coverage), MCMC and robust MLE estimation, Pareto/GGG
inter-purchase regularity, purchase-timing ($t_{x+1}$) and Gamma-Gamma CLV. The second half
asks whether **flexible machine learning produces better-calibrated forecasts than the
parsimonious structural model** — across counts, monetary value, churn and timing, on seven
public cohorts whose active rates span 1.6% to 96% — and, where the structural model breaks,
how to repair it. If you only read one page, read the :doc:`selection` guide.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   datasets
   selection

.. toctree::
   :maxdepth: 2
   :caption: Methods & Architecture

   ARCHITECTURE
   theory_variance_decomposition

.. toctree::
   :maxdepth: 2
   :caption: Statistical vs. Machine-Learned

   ml_benchmark
   conformal
   amortized
   bgnbd
   clv_benchmark
   churn

.. toctree::
   :maxdepth: 2
   :caption: Reference

   DEVELOPMENT
   api_reference

Interactive Web Application
---------------------------

An interactive, browser-based WebAssembly application powered by **Pyodide** is available:

- `Launch Pyodide Interactive WebApp <interactive.html>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
