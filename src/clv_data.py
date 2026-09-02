"""
Phase 2, Step 7: monetary / CLV data layer.

Builds a per-customer summary carrying spend, so we can forecast future customer value (money),
not just purchase counts. From a transaction log with spend we compute, per customer:
  x, t_x, T_cal   -- the usual BTYD calibration summary (repeat-purchase counts/recency/window)
  m_bar           -- average spend per calibration transaction (the Gamma-Gamma input)
  future_clv      -- total spend in the forecast window (T_cal, T_cal+T*]  (the target)

Monetary loaders return a (cust, date, spend) transaction log (one row per customer-day, spend
summed within the day). Datasets with spend: Online Retail II, Ta-Feng, Dunnhumby.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import WEEK  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


# ------------------------- monetary transaction loaders ------------------------ #
def _to_txn(df, cust, date, spend):
    """Collapse to one transaction per customer-day, spend summed."""
    out = df[[cust, date, spend]].copy()
    out.columns = ["cust", "date", "spend"]
    out["date"] = pd.to_datetime(out["date"]).values.astype("datetime64[D]")
    out = out[out["spend"] > 0]
    return out.groupby(["cust", "date"], as_index=False)["spend"].sum()


def load_online_retail_ii_money():
    df = pd.read_csv(DATA / "online_retail_II.csv", encoding="ISO-8859-1",
                     usecols=["Invoice", "InvoiceDate", "Customer ID", "Quantity", "Price"])
    df = df.dropna(subset=["Customer ID"])
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    df["spend"] = df["Quantity"] * df["Price"]
    df["Customer ID"] = df["Customer ID"].astype(int)
    return _to_txn(df, "Customer ID", "InvoiceDate", "spend")


def load_tafeng_money():
    df = pd.read_csv(DATA / "tafeng" / "ta_feng_all_months_merged.csv",
                     usecols=["TRANSACTION_DT", "CUSTOMER_ID", "AMOUNT", "SALES_PRICE"])
    df["date"] = pd.to_datetime(df["TRANSACTION_DT"], format="%m/%d/%Y")
    df["spend"] = df["AMOUNT"] * df["SALES_PRICE"]
    return _to_txn(df, "CUSTOMER_ID", "date", "spend")


def load_dunnhumby_money():
    df = pd.read_csv(DATA / "dunnhumby" / "transaction_data.csv",
                     usecols=["household_key", "DAY", "SALES_VALUE"])
    df["date"] = pd.Timestamp("2000-01-01") + pd.to_timedelta(df["DAY"] - 1, unit="D")
    return _to_txn(df, "household_key", "date", "SALES_VALUE")


# ----------------------------- CLV summary builder ----------------------------- #
def clv_summary(txn: pd.DataFrame, cal_weeks: int, horizon: int) -> pd.DataFrame:
    """Per-customer BTYD summary + average calibration spend + future-window CLV target."""
    t0 = txn["date"].min()
    cal_end = t0 + cal_weeks * WEEK
    fc_end = cal_end + horizon * WEEK
    rows = []
    for cust, g in txn.groupby("cust"):
        g = g.sort_values("date")
        dates = g["date"].values
        spend = g["spend"].values
        acq = dates[0]
        if acq > cal_end:
            continue
        rep = dates[1:]
        rep_spend = spend[1:]
        cal_m = rep <= cal_end
        fut_m = (rep > cal_end) & (rep <= fc_end)
        x = int(cal_m.sum())
        t_x = (rep[cal_m][-1] - acq) / WEEK if x > 0 else 0.0
        rows.append({
            "cust": cust, "x": x, "t_x": float(t_x),
            "T_cal": float((cal_end - acq) / WEEK),
            "m_bar": float(rep_spend[cal_m].mean()) if x > 0 else 0.0,
            f"clv_{horizon}": float(rep_spend[fut_m].sum()),
        })
    return pd.DataFrame(rows)


MONEY_REGISTRY = {
    "OnlineRetailII": (load_online_retail_ii_money, 52, 26),
    "Ta-Feng": (load_tafeng_money, 8, 8),
    "Dunnhumby": (load_dunnhumby_money, 52, 26),
}


def load_clv_summary(name: str):
    loader, cal, h = MONEY_REGISTRY[name]
    return clv_summary(loader(), cal, h), h


if __name__ == "__main__":
    for name in MONEY_REGISTRY:
        df, h = load_clv_summary(name)
        clv = df[f"clv_{h}"].to_numpy()
        print(f"{name:15s} N={len(df):>6,d}  mean x={df.x.mean():5.2f}  "
              f"mean m_bar=${df[df.x>0].m_bar.mean():7.2f}  "
              f"mean future CLV=${clv.mean():8.2f}  zero-CLV={100*(clv==0).mean():4.1f}%")
