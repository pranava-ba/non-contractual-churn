"""Generate golden-file CSV + JSON fixtures for cross-checking a C++ Arrow
ingestion port (cpp/src/ingest.cpp) against the real Python elog_to_features."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import elog_to_features  # noqa: E402

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# Deliberately small and hand-checkable: gaps are exact multiples of 7 days.
# cust A: acquisition + a same-day duplicate + two more repeats.
# cust B: a single transaction (x=0, exercises the no-repeat path).
# cust C: acquired partway through, two repeats, tests a second active customer.
_ROWS = [
    ("A", "2024-01-01", 10.0),
    ("A", "2024-01-08", 5.0),
    ("A", "2024-01-08", 5.0),   # same-day duplicate of the row above
    ("A", "2024-01-22", 8.0),
    ("A", "2024-02-05", 12.0),
    ("B", "2024-01-01", 3.0),
    ("C", "2024-01-15", 20.0),
    ("C", "2024-01-29", 6.0),
    ("C", "2024-02-12", 6.0),
]


def _elog(with_spend: bool) -> pd.DataFrame:
    df = pd.DataFrame(_ROWS, columns=["cust", "date", "spend"])
    df["date"] = pd.to_datetime(df["date"])
    if not with_spend:
        df = df.drop(columns=["spend"])
    return df


def _to_json(features: pd.DataFrame, as_of: str | None, has_money: bool) -> dict:
    customers = []
    for row in features.to_dict("records"):
        c = {"cust": str(row["cust"]), "x": row["x"], "t_x": row["t_x"], "T_cal": row["T_cal"]}
        c["m_bar"] = row["m_bar"] if has_money else None
        customers.append(c)
    return {"as_of": as_of, "customers": customers}


if __name__ == "__main__":
    MODELS_DIR.mkdir(exist_ok=True)

    money_elog = _elog(with_spend=True)
    money_elog.assign(
        customer_id=money_elog["cust"], transaction_date=money_elog["date"].dt.strftime("%Y-%m-%d"),
        amount=money_elog["spend"],
    )[["customer_id", "transaction_date", "amount"]].to_csv(
        MODELS_DIR / "ingest_sample.csv", index=False)

    no_money_elog = _elog(with_spend=False)
    no_money_elog.assign(
        customer_id=no_money_elog["cust"], transaction_date=no_money_elog["date"].dt.strftime("%Y-%m-%d"),
    )[["customer_id", "transaction_date"]].to_csv(
        MODELS_DIR / "ingest_sample_no_money.csv", index=False)

    default_features = elog_to_features(money_elog)
    (MODELS_DIR / "ingest_golden.json").write_text(
        json.dumps(_to_json(default_features, as_of=None, has_money=True), indent=2))

    as_of = pd.Timestamp("2024-01-29")
    as_of_features = elog_to_features(money_elog, as_of=as_of)
    (MODELS_DIR / "ingest_golden_as_of.json").write_text(
        json.dumps(_to_json(as_of_features, as_of=as_of.strftime("%Y-%m-%d"), has_money=True), indent=2))

    no_money_features = elog_to_features(no_money_elog)
    (MODELS_DIR / "ingest_golden_no_money.json").write_text(
        json.dumps(_to_json(no_money_features, as_of=None, has_money=False), indent=2))

    print("Wrote ingest_sample.csv, ingest_sample_no_money.csv, and 3 golden JSON files")
