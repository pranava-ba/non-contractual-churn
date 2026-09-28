"""Production analog of empirical.elog_to_summary / clv_data.clv_summary for
the live app: given a raw transaction log, compute per-customer BTYD +
monetary features as of "now" (or an explicit as_of date), with no
forecast-horizon holdout split -- production has no known future to hold
out. This is the Python oracle that src/export_ingest_golden.py snapshots
and cpp/src/ingest.cpp is cross-checked against."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empirical import WEEK  # noqa: E402


def elog_to_features(elog: pd.DataFrame, as_of: "pd.Timestamp | None" = None) -> pd.DataFrame:
    """elog has columns cust, date[, spend]. Same-day purchases per customer
    are merged (date-only dedup; spend summed if present -- matches
    empirical.elog_to_summary / clv_data._to_txn's same-day-merge
    convention). as_of defaults to the log's own max date ("now" = the
    last-seen transaction); only transactions with date <= as_of count as
    observed history, so a caller can also use this to reconstruct what the
    features would have looked like at an earlier point in time."""
    elog = elog.copy()
    elog["date"] = elog["date"].values.astype("datetime64[D]")
    has_spend = "spend" in elog.columns
    if has_spend:
        elog = elog.groupby(["cust", "date"], as_index=False)["spend"].sum()
    else:
        elog = elog.drop_duplicates(["cust", "date"])

    cal_end = np.datetime64(as_of).astype("datetime64[D]") if as_of is not None else elog["date"].max()
    elog = elog[elog["date"] <= cal_end]

    rows = []
    for cust, g in elog.groupby("cust"):
        g = g.sort_values("date")
        dates = g["date"].values
        acq = dates[0]
        rep = dates[1:]
        x = len(rep)
        t_x = float((rep[-1] - acq) / WEEK) if x > 0 else 0.0
        T_cal = float((cal_end - acq) / WEEK)
        row = {"cust": cust, "x": x, "t_x": t_x, "T_cal": T_cal}
        if has_spend:
            rep_spend = g["spend"].values[1:]
            row["m_bar"] = float(rep_spend.mean()) if x > 0 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)
