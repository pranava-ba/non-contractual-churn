"""
Gear 2, Stage B — Hillstrom (MineThatData) randomized email experiment.

Unlike Dunnhumby (observational), Hillstrom is a RANDOMIZED trial (men's / women's / no email), so the
Qini coefficient is a valid, unbiased targeting metric — no DR needed. We binarize treatment
(any email vs none), take the standard `visit` outcome, map the recency/history fields to our RFM
state, fit the uplift estimators, and score each by Qini AUC + uplift@30% against value-targeting and
random. This is the clean-experiment counterpart to the Dunnhumby DR check.

Run:  python src/run_uplift_hillstrom.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from run_uplift_study import _rf_reg, _rf_clf   # noqa: E402
RES = ROOT / "results"


def load():
    from sklift.datasets import fetch_hillstrom
    d = fetch_hillstrom()
    X, y, t = d.data.copy(), d.target, d.treatment
    T = (t != "No E-Mail").astype(int).to_numpy()          # any email vs none (randomized)
    Y = y.to_numpy(float)                                  # 'visit' (binary)
    X = pd.get_dummies(X, columns=["history_segment", "zip_code", "channel"], drop_first=True)
    return X.to_numpy(float), T, Y, list(X.columns)


def main(seeds=3):
    from econml.dml import CausalForestDML
    from econml.metalearners import TLearner, XLearner
    from sklift.metrics import qini_auc_score, uplift_at_k
    X, T, Y, cols = load()
    print(f"Hillstrom: N={len(X)} | treated {T.mean():.1%} | visit rate {Y.mean():.1%} | {X.shape[1]} feats")
    rows = []
    for seed in range(seeds):
        tr, te = train_test_split(np.arange(len(X)), test_size=0.3, random_state=seed, stratify=T)
        scores = {}
        cf = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                             n_estimators=200, min_samples_leaf=50, random_state=seed)
        cf.fit(Y[tr], T[tr], X=X[tr]); scores["uplift_CausalForest"] = cf.effect(X[te])
        tl = TLearner(models=_rf_reg()); tl.fit(Y[tr], T[tr], X=X[tr]); scores["uplift_Tlearner"] = tl.effect(X[te])
        xl = XLearner(models=_rf_reg(), propensity_model=_rf_clf()); xl.fit(Y[tr], T[tr], X=X[tr])
        scores["uplift_Xlearner"] = xl.effect(X[te])
        vreg = _rf_reg(); vreg.fit(X[tr], Y[tr]); scores["target_value"] = vreg.predict(X[te])   # P(visit) status-quo
        scores["random"] = np.random.default_rng(seed).random(len(te))
        yte = pd.Series(Y[te]); tte = pd.Series(T[te])
        for name, s in scores.items():
            s = pd.Series(np.asarray(s).ravel())
            q = qini_auc_score(yte, s, tte)
            u30 = uplift_at_k(yte, s, tte, strategy="overall", k=0.3)
            rows.append(dict(method=name, qini_auc=q, uplift_at_30=u30, seed=seed))
    res = pd.DataFrame(rows)
    RES.mkdir(exist_ok=True); res.to_csv(RES / "gear2_hillstrom_summary.csv", index=False)
    agg = res.groupby("method")[["qini_auc", "uplift_at_30"]].mean().sort_values("qini_auc", ascending=False)
    print("\n=== Hillstrom targeting quality (mean over seeds; randomized => Qini valid) ===")
    print(agg.round(4).to_string())
    print("\nwrote results/gear2_hillstrom_summary.csv")
    return res


if __name__ == "__main__":
    main()
