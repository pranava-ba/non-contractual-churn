# Security Policy

This is a research codebase for probabilistic forecasting — it does not control physical
hardware, handle credentials, or process personal data. "Security" here means
**dependency safety, safe execution, and responsible disclosure**. Please read the scope
below before reporting.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.0.x | ✅ |
| < 1.0 | ❌ |

Fixes are applied to the latest release line.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** — do not open a public issue for a
security report.

- Email: **pranavabaascaran@gmail.com** with the subject `SECURITY: pareto-nbd-extension`.
- Include a description, a reproducer, affected versions, and the potential impact.
- Expect an acknowledgement within **7 days** and a status update within **30 days**.
  Please allow a reasonable window for a fix before public disclosure.

## Scope

**In scope**
- Vulnerabilities in this repository's own code (`src/`, `tests/`, `docs/`).
- Insecure or vulnerable pinned dependencies in `pyproject.toml`.
- Issues in the Pyodide app (`docs/interactive.html`) that could execute unintended code
  in a visitor's browser beyond the intended in-page simulation.

**Out of scope**
- Vulnerabilities in third-party packages themselves (report upstream), though we will
  bump affected version pins.
- Numerical/statistical *bugs* — these are correctness issues; please file a normal
  [issue](CONTRIBUTING.md#reporting-issues).

## Safe-use notes

- **Trusted inputs only.** The library ingests transaction event logs and cohort
  summaries; run it on data you trust. It performs no network I/O and executes no code
  from input files.
- **Data privacy.** The repository ships only the public CDNow and Grocery benchmarks and
  synthetic data — no personal or proprietary data. If you apply the code to real customer
  data, treat that data according to your own privacy and retention obligations; do not
  commit it.
- **The interactive app** runs Python in your browser via WebAssembly (Pyodide) and loads
  Pyodide, Chart.js, and fonts from public CDNs. It runs in the browser sandbox and sends
  no data anywhere, but it does require a network connection to load those assets.

## Dependencies

Runtime dependencies are limited to `numpy`, `scipy`, `pandas`, and `matplotlib`. Keep
them current; a `pip install -e ".[dev]"` in a fresh virtual environment picks up patched
versions.
