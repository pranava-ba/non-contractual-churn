"""
Gear 2, Stage B — X5 RetailHero uplift-modeling competition (https://ods.ai/competitions/
x5-retailhero-uplift-modeling/data). Login-walled (free registration required), so this cannot be
auto-fetched -- `sklift.datasets.fetch_x5(download_if_missing=True)` hangs on the login redirect
(confirmed 2026-09-21). This script is ready to run the moment the raw files are placed manually.

Like Hillstrom (`run_uplift_hillstrom.py`), the SMS communication was **randomized** among eligible
clients, so we evaluate by Qini AUC (no DR needed) -- the clean-experiment counterpart to
Dunnhumby's observational DR check, at a third, larger scale.

--- Setup (manual, one-time) ---
1. Register at https://ods.ai/competitions/x5-retailhero-uplift-modeling/data (free) and download
   the competition's raw data (a zip containing at least clients.csv, purchases.csv, and
   uplift_train.csv / train.csv).
2. Unzip into `data/x5/` at the project root, so this script sees:
     data/x5/clients.csv        -- customer_id, first_issue_date, first_redeem_date, age, gender
     data/x5/purchases.csv      -- customer_id, transaction_id, transaction_datetime,
                                    purchase_sum, product_quantity, trn_sum_from_iss, ... (large)
     data/x5/uplift_train.csv   -- customer_id (or client_id), treatment_flg, target
   (Column names vary slightly by competition-data revision; `build_panel()` below tries the
   common aliases and raises a clear error naming what it found if none match.)
3. Run:  python src/run_uplift_x5.py

Everything downstream (feature engineering, estimators, Qini scoring, results CSV) mirrors
`run_uplift_hillstrom.py` exactly, so the two are directly comparable in the paper.
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
DATA = ROOT / "data" / "x5"

# common column-name aliases across competition-data revisions
_ID_ALIASES = ["customer_id", "client_id"]
_TREAT_ALIASES = ["treatment_flg", "treatment"]
_TARGET_ALIASES = ["target", "response_att"]


def _pick_col(df: pd.DataFrame, aliases: list[str], what: str) -> str:
    for a in aliases:
        if a in df.columns:
            return a
    raise ValueError(f"couldn't find a {what} column among {aliases}; "
                     f"found columns: {list(df.columns)}")


def build_panel() -> pd.DataFrame:
    """RFM features from the full purchase history (it predates the campaign by construction in
    this competition's data) + the randomized treatment/target from uplift_train."""
    for f in ("clients.csv", "purchases.csv"):
        if not (DATA / f).exists():
            raise FileNotFoundError(
                f"{DATA / f} not found. See the setup instructions in this file's docstring: "
                f"download the X5 RetailHero data (login required) and unzip into {DATA}/.")
    train_path = DATA / "uplift_train.csv"
    if not train_path.exists():
        train_path = DATA / "train.csv"
    if not train_path.exists():
        raise FileNotFoundError(
            f"neither {DATA/'uplift_train.csv'} nor {DATA/'train.csv'} found; see this file's "
            f"docstring for the expected layout.")

    train = pd.read_csv(train_path)
    id_col = _pick_col(train, _ID_ALIASES, "customer id")
    t_col = _pick_col(train, _TREAT_ALIASES, "treatment")
    y_col = _pick_col(train, _TARGET_ALIASES, "target")
    train = train.rename(columns={id_col: "customer_id", t_col: "T", y_col: "Y"})[
        ["customer_id", "T", "Y"]]

    clients = pd.read_csv(DATA / "clients.csv")
    cid_col = _pick_col(clients, _ID_ALIASES, "customer id")
    clients = clients.rename(columns={cid_col: "customer_id"})

    purch = pd.read_csv(DATA / "purchases.csv", usecols=lambda c: c.lower() in (
        "customer_id", "client_id", "transaction_id", "transaction_datetime",
        "purchase_sum", "product_quantity"))
    pid_col = _pick_col(purch, _ID_ALIASES, "customer id")
    purch = purch.rename(columns={pid_col: "customer_id"})
    purch["transaction_datetime"] = pd.to_datetime(purch["transaction_datetime"])

    g = purch.groupby("customer_id")
    feat = pd.DataFrame(index=pd.Index(train["customer_id"].unique(), name="customer_id"))
    ref_date = purch["transaction_datetime"].max()
    freq = g["transaction_id"].nunique() if "transaction_id" in purch.columns else g.size()
    feat["freq"] = freq.reindex(feat.index).fillna(0)
    last_dt = g["transaction_datetime"].max().reindex(feat.index)
    first_dt = g["transaction_datetime"].min().reindex(feat.index)
    feat["recency_days"] = (ref_date - last_dt).dt.days.fillna(9999)
    feat["tenure_days"] = (ref_date - first_dt).dt.days.fillna(0)
    if "purchase_sum" in purch.columns:
        feat["total_spend"] = g["purchase_sum"].sum().reindex(feat.index).fillna(0)
        feat["avg_spend"] = feat["total_spend"] / feat["freq"].clip(lower=1)

    # demographics (age/gender), if present -- one-hot gender
    demo_cols = [c for c in ("age", "gender") if c in clients.columns]
    if demo_cols:
        clients_idx = clients.set_index("customer_id")[demo_cols]
        feat = feat.join(clients_idx, how="left")
        if "gender" in feat.columns:
            feat = pd.get_dummies(feat, columns=["gender"], drop_first=True)
        if "age" in feat.columns:
            feat["age"] = feat["age"].fillna(feat["age"].median())

    feat = feat.reset_index()
    return feat.merge(train, on="customer_id", how="inner")


def main(seeds=3):
    from econml.dml import CausalForestDML
    from econml.metalearners import TLearner, XLearner
    from sklift.metrics import qini_auc_score, uplift_at_k

    panel = build_panel()
    feat_cols = [c for c in panel.columns if c not in ("customer_id", "T", "Y")]
    X = panel[feat_cols].to_numpy(float)
    T = panel["T"].to_numpy(int)
    Y = panel["Y"].to_numpy(float)
    print(f"X5 RetailHero: N={len(panel)} | treated {T.mean():.1%} | target rate {Y.mean():.1%} "
         f"| {len(feat_cols)} feats: {feat_cols}")

    rows = []
    for seed in range(seeds):
        tr, te = train_test_split(np.arange(len(X)), test_size=0.3, random_state=seed, stratify=T)
        scores = {}
        cf = CausalForestDML(model_y=_rf_reg(), model_t=_rf_clf(), discrete_treatment=True,
                             n_estimators=200, min_samples_leaf=50, random_state=seed)
        cf.fit(Y[tr], T[tr], X=X[tr]); scores["uplift_CausalForest"] = cf.effect(X[te])
        tl = TLearner(models=_rf_reg()); tl.fit(Y[tr], T[tr], X=X[tr])
        scores["uplift_Tlearner"] = tl.effect(X[te])
        xl = XLearner(models=_rf_reg(), propensity_model=_rf_clf()); xl.fit(Y[tr], T[tr], X=X[tr])
        scores["uplift_Xlearner"] = xl.effect(X[te])
        vreg = _rf_reg(); vreg.fit(X[tr], Y[tr]); scores["target_value"] = vreg.predict(X[te])
        scores["random"] = np.random.default_rng(seed).random(len(te))
        yte, tte = pd.Series(Y[te]), pd.Series(T[te])
        for name, s in scores.items():
            s = pd.Series(np.asarray(s).ravel())
            q = qini_auc_score(yte, s, tte)
            u30 = uplift_at_k(yte, s, tte, strategy="overall", k=0.3)
            rows.append(dict(method=name, qini_auc=q, uplift_at_30=u30, seed=seed))

    res = pd.DataFrame(rows)
    RES.mkdir(exist_ok=True)
    res.to_csv(RES / "gear2_x5_summary.csv", index=False)
    agg = res.groupby("method")[["qini_auc", "uplift_at_30"]].mean().sort_values(
        "qini_auc", ascending=False)
    print("\n=== X5 RetailHero targeting quality (mean over seeds; randomized => Qini valid) ===")
    print(agg.round(4).to_string())
    print("\nwrote results/gear2_x5_summary.csv")
    return res


if __name__ == "__main__":
    main()
