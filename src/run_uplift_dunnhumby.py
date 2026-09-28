"""
Gear 2, Stage B — real-data external validity on Dunnhumby "Complete Journey".

Dunnhumby ships household-level marketing **campaign** assignments (campaign_table + campaign_desc) on
top of a 2-year transaction log — a genuine (observational, NON-randomized) retention treatment. We:
  * build the pre-treatment BTYD/RFM state from the feature window [1, 223] (before any campaign starts),
  * define T = household exposed to >=1 campaign starting in [224, 450],
  * take Y = total spend in the outcome window [451, 711],
  * fit the same uplift estimators, and — since there is NO ground-truth CATE and assignment is
    confounded (campaigns were TARGETED) — evaluate targeting policies by a **doubly-robust policy
    value** (adjusts for the propensity + outcome models), comparing uplift- vs value- vs random-
    targeting against treat-all / treat-none.

Identification caveat: assignment is observational; DR reduces but does not eliminate confounding bias
(unobserved drivers of both targeting and spend remain possible). This is an external-validity check
that the pipeline produces sensible, differentiated targeting on real data — not a causal proof.

Run:  python src/run_uplift_dunnhumby.py
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
from run_uplift_study import _rf_reg, _rf_clf, policy_pct_oracle  # noqa: E402  (reuse learners)

DATA = ROOT / "data" / "dunnhumby"
RES = ROOT / "results"
CAL_END, TREAT_START, TREAT_END, OUT_START, DAY_MAX = 223, 224, 450, 451, 711


def build_panel():
    tx = pd.read_csv(DATA / "transaction_data.csv", usecols=["household_key", "DAY", "SALES_VALUE"])
    hh = pd.Index(sorted(tx.household_key.unique()), name="household_key")
    cal = tx[tx.DAY <= CAL_END]
    g = cal.groupby("household_key")
    feat = pd.DataFrame(index=hh)
    feat["freq"] = g.DAY.nunique().reindex(hh).fillna(0)                    # distinct shopping days
    feat["last_day"] = g.DAY.max().reindex(hh).fillna(0)
    feat["first_day"] = g.DAY.min().reindex(hh).fillna(CAL_END)
    feat["recency"] = CAL_END - feat["last_day"]                            # days since last trip
    feat["tenure"] = CAL_END - feat["first_day"]
    feat["cal_spend"] = g.SALES_VALUE.sum().reindex(hh).fillna(0)
    feat["avg_spend"] = feat["cal_spend"] / feat["freq"].clip(lower=1)
    # treatment: campaign starting in the exposure window
    ct = pd.read_csv(DATA / "campaign_table.csv")
    cd = pd.read_csv(DATA / "campaign_desc.csv")
    ct = ct.merge(cd[["CAMPAIGN", "START_DAY"]], on="CAMPAIGN", how="left")
    treated = ct[(ct.START_DAY >= TREAT_START) & (ct.START_DAY <= TREAT_END)].household_key.unique()
    feat["T"] = feat.index.isin(treated).astype(int)
    # outcome: spend in the outcome window
    out = tx[tx.DAY >= OUT_START].groupby("household_key").SALES_VALUE.sum()
    feat["Y"] = out.reindex(hh).fillna(0.0)
    return feat.reset_index()


FEATURES = ["freq", "recency", "tenure", "cal_spend", "avg_spend"]


def dr_values(scores: dict, ehat, m1h, m0h, Tte, Yte, budget=0.30, cost=0.0):
    """Doubly-robust NET value (revenue minus per-contact cost) of each targeting policy on the
    SAME test customers the scores are for. Adds treat-all / treat-none references. Nuisances
    (ehat, m1h, m0h) are fit on the train fold. `cost` is a per-contacted-customer charge in the
    SAME units as Yte (Dunnhumby: raw sales dollars) -- treat-all pays it on 100% of customers,
    the budgeted score-based policies only pay it on their `budget` fraction, so a nonzero cost
    erodes treat-all's advantage (it was previously implicitly free) relative to a policy that
    concentrates spend on the customers actually worth contacting. Default cost=0.0 reproduces the
    original (uncosted) comparison exactly."""
    p_obs = np.where(Tte == 1, ehat, 1 - ehat)
    m_obs = np.where(Tte == 1, m1h, m0h)

    def value(pi):                     # pi in {0,1} per test customer
        mu_pi = np.where(pi == 1, m1h, m0h)
        match = (Tte == pi).astype(float)
        raw = float(np.mean(mu_pi + match / p_obs * (Yte - m_obs)))
        return raw - cost * float(np.mean(pi))

    n = len(Tte); k = max(1, int(budget * n))
    out = {"treat_all": value(np.ones(n, int)), "treat_none": value(np.zeros(n, int))}
    for name, s in scores.items():
        pi = np.zeros(n, int); pi[np.argsort(-np.asarray(s))[:k]] = 1
        out[name] = value(pi)
    return out


COSTS = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]   # per-contact $ (raw sales-dollar units)


def _fit_seed(panel, X, T, Y, seed):
    """Fit the uplift/value scores + DR nuisances once for a seed; reused across the cost sweep
    (cost only changes the post-hoc value calculation, not any model fit)."""
    from econml.dml import CausalForestDML
    from econml.metalearners import XLearner
    tr, te = train_test_split(np.arange(len(X)), test_size=0.4, random_state=seed, stratify=T)
    cf = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                         n_estimators=400, min_samples_leaf=25, random_state=seed)
    cf.fit(Y[tr], T[tr], X=X[tr]); uplift = cf.effect(X[te])
    xl = XLearner(models=_rf_reg(), propensity_model=_rf_clf()); xl.fit(Y[tr], T[tr], X=X[tr])
    uplift_x = xl.effect(X[te])
    vreg = _rf_reg(); vreg.fit(X[tr], Y[tr]); value_score = vreg.predict(X[te])
    rng = np.random.default_rng(seed)
    scores = {"uplift_CausalForest": uplift, "uplift_Xlearner": uplift_x,
              "target_value": value_score, "random": rng.random(len(te))}
    e = _rf_clf(); e.fit(X[tr], T[tr]); ehat = np.clip(e.predict_proba(X[te])[:, 1], 0.05, 0.95)
    m1 = _rf_reg(); m1.fit(X[tr][T[tr] == 1], Y[tr][T[tr] == 1]); m1h = m1.predict(X[te])
    m0 = _rf_reg(); m0.fit(X[tr][T[tr] == 0], Y[tr][T[tr] == 0]); m0h = m0.predict(X[te])
    return scores, ehat, m1h, m0h, T[te], Y[te]


def main(seeds=5):
    panel = build_panel()
    print(f"Dunnhumby panel: {len(panel)} households | treated {panel['T'].mean():.1%} | "
          f"mean outcome spend {panel['Y'].mean():.1f}")
    X = panel[FEATURES].to_numpy(float)
    T = panel["T"].to_numpy(int); Y = panel["Y"].to_numpy(float)

    fits = [_fit_seed(panel, X, T, Y, seed) for seed in range(seeds)]
    rows = []
    for seed, (scores, ehat, m1h, m0h, Tte, Yte) in enumerate(fits):
        vals = dr_values(scores, ehat, m1h, m0h, Tte, Yte)     # cost=0.0, the original comparison
        for pol, v in vals.items():
            rows.append(dict(policy=pol, dr_value=v, seed=seed))
    res = pd.DataFrame(rows)
    RES.mkdir(exist_ok=True)
    res.to_csv(RES / "gear2_dunnhumby_summary.csv", index=False)
    agg = res.groupby("policy").dr_value.mean().sort_values(ascending=False)
    base = agg.get("treat_none", 0.0)
    print("\n=== Dunnhumby DR policy value (mean over seeds) — incremental vs treat-none ===")
    for pol, v in agg.items():
        print(f"  {pol:22s} DR value={v:9.2f}   incremental={v-base:+8.2f}")
    print("\nwrote results/gear2_dunnhumby_summary.csv")

    # --- cost sweep: does a nonzero per-contact cost flip treat-all's "free" advantage? ---
    cost_rows = []
    for seed, (scores, ehat, m1h, m0h, Tte, Yte) in enumerate(fits):
        for c in COSTS:
            vals = dr_values(scores, ehat, m1h, m0h, Tte, Yte, cost=c)
            for pol, v in vals.items():
                cost_rows.append(dict(policy=pol, cost=c, dr_value=v, seed=seed))
    cres = pd.DataFrame(cost_rows)
    cres.to_csv(RES / "gear2_dunnhumby_cost_summary.csv", index=False)
    cagg = cres.groupby(["cost", "policy"]).dr_value.mean().unstack("policy")
    print("\n=== Cost sweep: NET DR value by policy (treat-all pays cost on 100%, "
         "budgeted policies on 30%) ===")
    print(cagg.round(1).to_string())
    best_budgeted = cagg.drop(columns=["treat_all", "treat_none"]).max(axis=1)
    crossover = cagg.index[best_budgeted > cagg["treat_all"]]
    if len(crossover):
        print(f"\nCrossover: at cost >= {crossover.min():.1f}, the best budgeted policy overtakes "
             f"treat_all's net value.")
    else:
        print("\nNo crossover within the swept cost range -- treat_all's raw revenue advantage "
             "(it touches more of the population) outweighs its cost even at the highest cost "
             f"tested (${COSTS[-1]:.0f}/contact).")
    print("wrote results/gear2_dunnhumby_cost_summary.csv")
    return res, cres


if __name__ == "__main__":
    main()
