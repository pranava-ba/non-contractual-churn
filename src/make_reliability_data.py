"""CORP reliability-diagram data for the churn target (Dimitriadis, Gneiting & Jordan 2021).

For four contrasting cohorts (two where the count law fits, two where it breaks), pool per-customer
P(active) predictions across a few seeds for BTYD vs the ML classifier, then estimate the conditional
event probability by isotonic regression (PAV) -- the CORP reliability curve. Saves
results/reliability_curves.csv (dataset, method, x, y) and results/reliability_meta.csv.

Run:  python src/make_reliability_data.py
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.isotonic import IsotonicRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ml_study import build_providers            # noqa: E402
from churn import compare_churn, ece                # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
COHORTS = ["Simulated", "Grocery", "OnlineRetailII", "Dunnhumby"]  # 2 fit, 2 break
SEEDS = 4
MCMC_DRAWS = 800
GRID = np.linspace(0.0, 1.0, 101)


def corp_curve(p, o):
    """CORP reliability curve: isotonic (PAV) regression of outcomes on forecasts."""
    p = np.clip(np.asarray(p, float), 0, 1)
    o = np.asarray(o, float)
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, o)
    lo, hi = p.min(), p.max()
    xs = GRID[(GRID >= lo - 1e-9) & (GRID <= hi + 1e-9)]
    if len(xs) < 2:
        xs = np.array([lo, hi])
    return xs, iso.predict(xs)


def main():
    provs = build_providers()
    curves, meta = [], []
    for name in COHORTS:
        t = time.time()
        pool = {"BTYD": ([], []), "ML": ([], [])}
        for seed in range(SEEDS):
            df, h = provs[name](seed)
            res = compare_churn(df, h, seed=4000 + seed, mcmc_draws=MCMC_DRAWS, return_curves=True)
            c = res["_curves"]
            pool["BTYD"][0].append(c["p_btyd"]); pool["BTYD"][1].append(c["o"])
            pool["ML"][0].append(c["p_ml"]);     pool["ML"][1].append(c["o"])
        for method in ("BTYD", "ML"):
            p = np.concatenate(pool[method][0]); o = np.concatenate(pool[method][1])
            xs, ys = corp_curve(p, o)
            for x, yv in zip(xs, ys):
                curves.append(dict(dataset=name, method=method, x=float(x), y=float(yv)))
            meta.append(dict(dataset=name, method=method, n=int(len(p)),
                             ece=float(ece(np.clip(p, 0, 1), o)),
                             p_mean=float(p.mean()), o_mean=float(o.mean())))
        print(f"[{name}] pooled {SEEDS} seeds ({time.time()-t:.0f}s)", flush=True)
    pd.DataFrame(curves).to_csv(RES / "reliability_curves.csv", index=False)
    pd.DataFrame(meta).to_csv(RES / "reliability_meta.csv", index=False)
    print("[saved] reliability_curves.csv + reliability_meta.csv")
    print(pd.DataFrame(meta).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
