# Contributing Guidelines

Thanks for your interest in improving the Pareto/NBD Extension. This is a research
codebase, so correctness and reproducibility matter more than features — a bug in a
scorer or estimator can silently invalidate a published number.

## Reporting issues

Open a GitHub issue with:

- a **minimal reproducer** (a short script or the exact command),
- expected vs. actual behaviour, and
- your environment (`python --version`, `numpy`/`scipy` versions).

For numerical bugs, include the offending values — e.g. a parameter estimate that is
orders of magnitude off, or a scorer returning an impossible value.

## Development workflow

1. **Fork** and create a topic branch: `feat/timing-crps`, `fix/clv-posterior`,
   `docs/architecture`.
2. Make focused changes; keep unrelated edits out of the PR.
3. Run the checks locally (see below) — they must pass.
4. Open a PR against `main` with a clear description of *what* and *why*.

## Commit messages — Conventional Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary>

feat(clv): add discounted CLV horizon
fix(clv): sample mean spend from Inverse-Gamma, not Gamma
docs(architecture): document the SPP predictive identity
test(estimate): add parameter-recovery check
refactor(score): vectorise the CRPS estimator
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`. This keeps the
[CHANGELOG](CHANGELOG.md) easy to assemble.

## Code standards

- **Formatting/linting** must pass (see [Developer Guide](docs/DEVELOPMENT.md#7-code-style)):

  ```bash
  black src/ tests/
  flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
  ```

- **Tests** must pass and must include a **numerical** assertion for any new estimator,
  scorer, or model — not just a shape/`> 0` smoke check:

  ```bash
  pytest tests/ -q
  ```

- **Style:** pure-`numpy` vectorisation over Python loops, explicit `seed` arguments,
  and docstrings that state the math a function implements. Match the surrounding code.

## PR checklist

- [ ] `black` and `flake8` clean
- [ ] `pytest` green, with a numerical test for new numerical code
- [ ] Docstrings/README/`docs/` updated if behaviour or the API changed
- [ ] `CHANGELOG.md` "Unreleased" updated
- [ ] If a published figure/table number changes, the regenerating script is noted in the PR

## Adding an extension or model

New models plug into the existing pipeline: emit per-customer predictive draws of the
target quantity, then score them with `score.py`. Add a `__main__` self-test (a recovery
or unit check), a `tests/` numerical test, and a short entry in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## The upload bundle

`github_upload_bundle/` and its `.zip` are **build artifacts** — do not hand-edit them.
Regenerate after changes:

```bash
cd github_upload_bundle && zip -rq ../github_upload_bundle.zip . -x '*/__pycache__/*' '*.pyc'
```
