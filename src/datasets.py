"""
Phase 2, Step 3: ingestion loaders for the additional public benchmarks.

Each loader converts a raw Kaggle download into a clean transaction event log with two
columns -- ``cust`` and ``date`` -- which the existing ``empirical.elog_to_summary`` turns
into the per-customer BTYD summary ``(x, t_x, T_cal, x_star_{h})``. Same pipeline as CDNow
and Grocery, so every downstream fit/score works unchanged.

Datasets (all real, non-contractual transaction logs; see docs/datasets.md for why age is
irrelevant to a calibration study and why we avoid synthetic sets):
  - Online Retail II  (UK gift retailer, 2009-2011)         data/online_retail_II.csv
  - Olist             (Brazilian marketplace, 2016-2018)    data/olist/*.csv
  - Dunnhumby         (US grocery, ~2 yrs, + demographics)  data/dunnhumby/transaction_data.csv
  - Ta-Feng           (Taiwan grocery, Nov 2000-Feb 2001)   data/tafeng/ta_feng_all_months_merged.csv

Run  `python src/datasets.py`  to print a summary cohort for each.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import elog_to_summary  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


# ------------------------------- loaders --------------------------------------- #
def load_online_retail_ii() -> pd.DataFrame:
    """UK online gift retailer, Dec 2009-Dec 2011. Drops missing customers and
    cancellations (Invoice starting 'C'); keeps positive-quantity purchase events."""
    df = pd.read_csv(DATA / "online_retail_II.csv", encoding="ISO-8859-1",
                     usecols=["Invoice", "InvoiceDate", "Customer ID", "Quantity"])
    df = df.dropna(subset=["Customer ID"])
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    df = df[df["Quantity"] > 0]
    df["date"] = pd.to_datetime(df["InvoiceDate"])
    df["cust"] = df["Customer ID"].astype(int)
    return df[["cust", "date"]]


def load_olist() -> pd.DataFrame:
    """Brazilian marketplace, 2016-2018. Repeat buyers are identified by
    customer_unique_id (customer_id is per-order). Cancelled/unavailable orders dropped."""
    orders = pd.read_csv(DATA / "olist" / "olist_orders_dataset.csv",
                         usecols=["customer_id", "order_purchase_timestamp", "order_status"])
    custs = pd.read_csv(DATA / "olist" / "olist_customers_dataset.csv",
                        usecols=["customer_id", "customer_unique_id"])
    orders = orders[~orders["order_status"].isin(["canceled", "unavailable"])]
    m = orders.merge(custs, on="customer_id", how="left")
    m["date"] = pd.to_datetime(m["order_purchase_timestamp"])
    m["cust"] = m["customer_unique_id"]
    return m[["cust", "date"]].dropna()


def load_dunnhumby() -> pd.DataFrame:
    """US grocery, ~2 years. DAY is an integer day index (1..711); map it to a real
    timeline so week arithmetic in elog_to_summary is correct. cust = household_key."""
    df = pd.read_csv(DATA / "dunnhumby" / "transaction_data.csv",
                     usecols=["household_key", "DAY"])
    df["date"] = pd.Timestamp("2000-01-01") + pd.to_timedelta(df["DAY"] - 1, unit="D")
    df["cust"] = df["household_key"]
    return df[["cust", "date"]]


def load_tafeng() -> pd.DataFrame:
    """Taiwan grocery, Nov 2000-Feb 2001 (~4 months). Short span -> short windows."""
    df = pd.read_csv(DATA / "tafeng" / "ta_feng_all_months_merged.csv",
                     usecols=["TRANSACTION_DT", "CUSTOMER_ID"])
    df["date"] = pd.to_datetime(df["TRANSACTION_DT"], format="%m/%d/%Y")
    df["cust"] = df["CUSTOMER_ID"]
    return df[["cust", "date"]]


# name -> (loader, calibration weeks, forecast horizon weeks). Windows chosen to fit each
# dataset's span (Ta-Feng is only ~17 weeks, so it needs short windows).
REGISTRY = {
    "OnlineRetailII": (load_online_retail_ii, 52, 26),
    "Olist": (load_olist, 52, 26),
    "Dunnhumby": (load_dunnhumby, 52, 26),
    "Ta-Feng": (load_tafeng, 8, 8),
}


def load_summary(name: str):
    """Load a dataset and return its per-customer BTYD cohort summary + (cal_weeks, horizon)."""
    loader, cal, h = REGISTRY[name]
    elog = loader()
    return elog_to_summary(elog, cal_weeks=cal, horizon=h), h


if __name__ == "__main__":
    for name in REGISTRY:
        loader, cal, h = REGISTRY[name]
        elog = loader()
        span_wk = (elog["date"].max() - elog["date"].min()).days / 7.0
        df, h = load_summary(name)
        y = df[f"x_star_{h}"].to_numpy()
        print(f"{name:15s} events={len(elog):>8,d}  span={span_wk:5.0f}wk  "
              f"cohort N={len(df):>6,d}  mean x(cal)={df.x.mean():4.2f}  "
              f"zero-repeat={100*(df.x==0).mean():4.1f}%  active(T*={h})={100*(y>0).mean():4.1f}%")
