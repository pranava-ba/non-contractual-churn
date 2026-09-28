"""
Gear 2, Stage A: the uplift/CATE estimator + metric harness over the smart factorial.

Runs the 12-family DGP grid (target x structure x assignment) from simulate_intervention.py, fits a
panel of CATE estimators -- meta-learners (econml + causalml, the per-library bake-off), causal-forest
DML -- plus predict-then-target baselines (risk-targeting, value-targeting, random), and scores each on:

  * PEHE            sqrt(mean (cate_hat - cate_true)^2)            [lower better]  -- effect recovery
  * rank            Spearman(cate_hat, cate_true)                 [higher better] -- targeting ranking
  * coverage90      P(cate_true in 90% CI)  (interval estimators) [~0.90 = calibrated] -- OUR lens
  * policy_pct      captured true-CATE at a 30% budget / oracle   [higher better] -- managerial value

Primary outcome = residual CLV (cate_clv); the harness also reports count for reference. Ground-truth
CATE comes from the simulator, so every metric is scored against truth. Writes
results/gear2_uplift_summary.csv and prints an aggregated table.

Run:  python src/run_uplift_study.py            (quick: 1 delta, 5 seeds)
      python src/run_uplift_study.py --full      (delta sweep, 10 seeds)
"""
from __future__ import annotations

import sys
import time
import warnings
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import DatasetParams                                   # noqa: E402
from simulate_intervention import InterventionConfig, simulate_intervention  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
RES.mkdir(exist_ok=True)

TARGETS = ["mu", "both"]
STRUCTURES = ["homogeneous", "heterogeneous", "sleeping_dogs"]
ASSIGNMENTS = ["randomized", "confounded"]
BUDGET = 0.30                       # target the top 30% by each policy's score
# fixed clear-signal regime: high enough purchase rate + horizon + N that the treatment effect is
# recoverable above Poisson noise (a low-lambda/small-N draw drowns the mu-shift). delta swept below.
BASE_PARAMS = dict(E_lambda=0.5, CV_lambda=1.2, E_mu=0.08, CV_mu=1.2, N=6000, T=72)
HORIZON = 52


def _rf_reg():
    # LightGBM (histogram GBDT) — much faster than sklearn RF; n_jobs=1 because we parallelise cells.
    from lightgbm import LGBMRegressor
    return LGBMRegressor(n_estimators=200, num_leaves=31, min_child_samples=20,
                         learning_rate=0.05, n_jobs=1, verbosity=-1, random_state=0)


def _rf_clf():
    from lightgbm import LGBMClassifier
    return LGBMClassifier(n_estimators=200, num_leaves=31, min_child_samples=20,
                          learning_rate=0.05, n_jobs=1, verbosity=-1, random_state=0)


def features(df: pd.DataFrame) -> np.ndarray:
    """Observable calibration-window RFM state (what an estimator sees)."""
    x = df["x"].to_numpy(float)
    t_x = df["t_x"].to_numpy(float)
    T_cal = df["T_cal"].to_numpy(float)
    rec = t_x / np.maximum(T_cal, 1e-6)
    return np.column_stack([x, t_x, T_cal, rec, x / np.maximum(T_cal, 1e-6)])


def fit_estimators(Xtr, Ttr, Ytr, Xte):
    """Return {name: (cate_hat, ci_or_None)} for the CATE estimators."""
    out = {}
    # --- econml ---
    try:
        from econml.metalearners import TLearner, XLearner
        tl = TLearner(models=_rf_reg()); tl.fit(Ytr, Ttr, X=Xtr)
        out["econml_T"] = (tl.effect(Xte), None)
        xl = XLearner(models=_rf_reg(), propensity_model=_rf_clf()); xl.fit(Ytr, Ttr, X=Xtr)
        out["econml_X"] = (xl.effect(Xte), None)
    except Exception as e:
        out["econml_meta_ERR"] = (None, str(e))
    try:
        from econml.dr import DRLearner
        dr = DRLearner(model_propensity=_rf_clf(), model_regression=_rf_reg(),
                       model_final=_rf_reg(), cv=3)
        dr.fit(Ytr, Ttr, X=Xtr)
        out["econml_DR"] = (dr.effect(Xte), None)
    except Exception as e:
        out["econml_DR_ERR"] = (None, str(e))
    try:
        from econml.dml import CausalForestDML
        cf = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                             n_estimators=200, min_samples_leaf=20, random_state=0)  # n_est % 4 == 0
        cf.fit(Ytr, Ttr, X=Xtr)
        lb, ub = cf.effect_interval(Xte, alpha=0.10)
        out["econml_CausalForest"] = (cf.effect(Xte), (lb, ub))
    except Exception as e:
        out["econml_CF_ERR"] = (None, str(e))
    return out


def causalml_estimators(Xtr, Ttr, Ytr, Xte):
    out = {}
    try:
        from causalml.inference.meta import BaseTRegressor, BaseXRegressor
        tr = BaseTRegressor(learner=_rf_reg(), control_name=0)
        tr.fit(X=Xtr, treatment=Ttr.astype(int), y=Ytr)
        out["causalml_T"] = (tr.predict(Xte).ravel(), None)
        xr = BaseXRegressor(learner=_rf_reg(), control_name=0)
        xr.fit(X=Xtr, treatment=Ttr.astype(int), y=Ytr)
        out["causalml_X"] = (xr.predict(Xte).ravel(), None)
    except Exception as e:
        out["causalml_ERR"] = (None, str(e))
    return out


def baseline_scores(Xtr, Ttr, Ytr_clv, Yactive_tr, Xte):
    """Predict-then-target baselines: risk (high churn prob) and value (high predicted CLV),
    both trained on the CONTROL arm (the status quo the firm would observe)."""
    ctl = Ttr == 0
    out = {}
    # value-targeting: predicted residual value under status quo
    vreg = _rf_reg(); vreg.fit(Xtr[ctl], Ytr_clv[ctl])
    out["base_value"] = vreg.predict(Xte)
    # risk-targeting: predicted churn risk = 1 - P(active) under status quo
    if len(np.unique(Yactive_tr[ctl])) > 1:
        creg = _rf_clf(); creg.fit(Xtr[ctl], Yactive_tr[ctl].astype(int))
        out["base_risk"] = 1.0 - creg.predict_proba(Xte)[:, 1]
    else:
        out["base_risk"] = np.zeros(len(Xte))
    return out


def policy_pct_oracle(score, cate_true, budget=BUDGET):
    """Target the top-`budget` fraction by `score`; return captured true-CATE sum as % of the
    oracle (top-`budget` by true CATE). Can be <0 if a policy targets negative-CATE customers."""
    n = len(score); k = max(1, int(budget * n))
    sel = np.argsort(-score)[:k]
    captured = cate_true[sel].sum()
    oracle = np.sort(cate_true)[::-1][:k].sum()
    if oracle <= 1e-9:
        return np.nan
    return captured / oracle


def run_cell(target, structure, assignment, delta, seed):
    import warnings as _w; _w.filterwarnings("ignore")  # quiet joblib worker processes
    rng = np.random.default_rng(1000 + seed)
    params = DatasetParams(**BASE_PARAMS)
    cfg = InterventionConfig(target=target, structure=structure, delta=delta,
                             assignment=assignment, horizon=HORIZON)
    df = simulate_intervention(params, cfg, rng=rng)
    X = features(df)
    T = df["T"].to_numpy(int)
    Yclv = df["y_clv"].to_numpy(float)
    Yact = df["y_active"].to_numpy(float)
    cate = df["cate_clv"].to_numpy(float)
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=0.3, random_state=seed)

    ests = fit_estimators(X[tr], T[tr], Yclv[tr], X[te])
    ests.update(causalml_estimators(X[tr], T[tr], Yclv[tr], X[te]))
    # novelty-bearing estimators (structural BTYD-CATE + conformal-ITE repair)
    try:
        from uplift_estimators_ext import structural_btyd_cate, conformal_ite
        ests["structural_BTYD"] = structural_btyd_cate(df.iloc[tr], df.iloc[te], HORIZON, outcome="clv")
        ests["conformal_ITE"] = conformal_ite(X[tr], T[tr], Yclv[tr], X[te], _rf_reg, seed=seed)
    except Exception as e:
        ests["ext_ERR"] = (None, str(e))
    ests = {k: v for k, v in ests.items() if not k.endswith("ERR") and v[0] is not None and len(v[0])}

    rows = []
    cate_te = cate[te]
    for name, (chat, ci) in ests.items():
        chat = np.asarray(chat, float).ravel()
        pehe = float(np.sqrt(np.mean((chat - cate_te) ** 2)))
        rank = float(spearmanr(chat, cate_te).correlation) if np.std(chat) > 0 else np.nan
        cov = np.nan
        if ci is not None:
            lb, ub = np.asarray(ci[0]).ravel(), np.asarray(ci[1]).ravel()
            cov = float(np.mean((cate_te >= lb) & (cate_te <= ub)))
        pol = policy_pct_oracle(chat, cate_te)
        rows.append(dict(estimator=name, kind="cate", pehe=pehe, rank=rank,
                         coverage90=cov, policy_pct=pol))
    # baselines (scores only -> policy metric; no CATE so PEHE/rank N/A)
    bs = baseline_scores(X[tr], T[tr], Yclv[tr], Yact[tr], X[te])
    for name, score in bs.items():
        rows.append(dict(estimator=name, kind="baseline", pehe=np.nan, rank=np.nan,
                         coverage90=np.nan, policy_pct=policy_pct_oracle(score, cate_te)))
    rows.append(dict(estimator="random", kind="baseline", pehe=np.nan, rank=np.nan,
                     coverage90=np.nan, policy_pct=policy_pct_oracle(rng.random(len(te)), cate_te)))
    for r in rows:
        r.update(target=target, structure=structure, assignment=assignment, delta=delta, seed=seed)
    return rows


def main(full=False):
    deltas = [0.2, 0.35, 0.5, 0.65] if full else [0.5]
    seeds = range(10 if full else 5)
    cells = list(product(TARGETS, STRUCTURES, ASSIGNMENTS, deltas, seeds))
    print(f"Running {len(cells)} cells "
          f"({len(TARGETS)}x{len(STRUCTURES)}x{len(ASSIGNMENTS)} families x "
          f"{len(deltas)} delta x {len(list(seeds))} seeds)...")
    t0 = time.time()
    from joblib import Parallel, delayed
    results = Parallel(n_jobs=-1, verbose=5)(
        delayed(run_cell)(tg, st, asg, d, s) for (tg, st, asg, d, s) in cells)
    all_rows = [r for cell in results for r in cell]
    res = pd.DataFrame(all_rows)
    out = RES / "gear2_uplift_summary.csv"
    res.to_csv(out, index=False)
    print(f"\nWrote {out}  ({len(res)} rows, {time.time()-t0:.0f}s)\n")

    # aggregate: mean over families+seeds by estimator
    agg = (res.groupby("estimator")[["pehe", "rank", "coverage90", "policy_pct"]]
           .mean().sort_values("policy_pct", ascending=False))
    print("=== Overall (mean across all families) ===")
    print(agg.round(3).to_string())
    print("\n=== policy_pct by effect structure (the headline: uplift vs baselines) ===")
    piv = res.pivot_table(index="estimator", columns="structure", values="policy_pct", aggfunc="mean")
    print(piv.round(3).to_string())
    return res


if __name__ == "__main__":
    main(full="--full" in sys.argv)
