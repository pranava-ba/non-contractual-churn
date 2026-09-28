import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingest import elog_to_features  # noqa: E402
from empirical import elog_to_summary  # noqa: E402


def _toy_elog(with_spend: bool = False) -> pd.DataFrame:
    # cust 1: acquisition + a same-day duplicate on 01-08 + a repeat on 01-22
    #   (gaps are exact multiples of 7 days so weeks are hand-checkable)
    # cust 2: a single transaction (no repeats -> x=0)
    rows = [
        (1, "2024-01-01", 10.0),
        (1, "2024-01-08", 5.0),
        (1, "2024-01-08", 5.0),   # same-day duplicate: merges into the row above
        (1, "2024-01-22", 8.0),
        (2, "2024-01-01", 3.0),
    ]
    df = pd.DataFrame(rows, columns=["cust", "date", "spend"])
    df["date"] = pd.to_datetime(df["date"])
    if not with_spend:
        df = df.drop(columns=["spend"])
    return df


def test_elog_to_features_basic_counts_and_recency():
    out = elog_to_features(_toy_elog()).set_index("cust")
    assert set(out.columns) == {"x", "t_x", "T_cal"}

    # cust 1: 3 unique dates after same-day dedup -> acquisition + 2 repeats
    assert out.loc[1, "x"] == 2
    assert out.loc[1, "t_x"] == 3.0        # (01-22 - 01-01) / 7 weeks
    assert out.loc[1, "T_cal"] == 3.0      # as_of defaults to the log's max date (01-22)

    # cust 2: single transaction -> no repeats
    assert out.loc[2, "x"] == 0
    assert out.loc[2, "t_x"] == 0.0
    assert out.loc[2, "T_cal"] == 3.0      # still measured to the log-wide max date


def test_elog_to_features_monetary_column():
    out = elog_to_features(_toy_elog(with_spend=True)).set_index("cust")
    assert "m_bar" in out.columns
    # cust 1's repeats: day 01-08 (5+5 same-day dedup summed = 10), day 01-22 (8)
    assert out.loc[1, "m_bar"] == 9.0       # mean([10, 8])
    assert out.loc[2, "m_bar"] == 0.0       # x=0 placeholder


def test_elog_to_features_explicit_as_of():
    out = elog_to_features(_toy_elog(), as_of=pd.Timestamp("2024-01-15")).set_index("cust")
    assert out.loc[1, "T_cal"] == 2.0       # (01-15 - 01-01) / 7
    assert out.loc[1, "x"] == 1             # only the 01-08 repeat is <= as_of
    assert out.loc[1, "t_x"] == 1.0         # (01-08 - 01-01) / 7


def test_elog_to_features_subday_as_of_truncates_to_day_granularity():
    # Regression test: as_of parameter must be truncated to day granularity
    # before computing T_cal, matching the elog's date truncation.
    # Real callers pass pd.Timestamp.now() (with time-of-day), so this is critical.
    midnight = pd.Timestamp("2024-01-15 00:00:00")
    evening = pd.Timestamp("2024-01-15 23:59:59")
    afternoon = pd.Timestamp("2024-01-15 18:00:00")

    out_midnight = elog_to_features(_toy_elog(), as_of=midnight).set_index("cust")
    out_evening = elog_to_features(_toy_elog(), as_of=evening).set_index("cust")
    out_afternoon = elog_to_features(_toy_elog(), as_of=afternoon).set_index("cust")

    # All should produce the same day-truncated results
    assert out_midnight.loc[1, "T_cal"] == 2.0
    assert out_evening.loc[1, "T_cal"] == 2.0
    assert out_afternoon.loc[1, "T_cal"] == 2.0

    # Verify they all match exactly
    pd.testing.assert_frame_equal(out_midnight, out_evening)
    pd.testing.assert_frame_equal(out_midnight, out_afternoon)


def test_elog_to_features_matches_elog_to_summary_calibration_side():
    # elog_to_summary's calibration-window math (x, t_x, T_cal) is already
    # validated research code; when elog_to_features's as_of is set to the
    # exact same cal_end, the two must agree on every shared customer.
    elog = _toy_elog()
    t0 = elog["date"].min()
    cal_weeks = 3
    cal_end = t0 + cal_weeks * np.timedelta64(7, "D")

    a = elog_to_features(elog, as_of=cal_end).set_index("cust")[["x", "t_x", "T_cal"]]
    b = elog_to_summary(elog, cal_weeks=cal_weeks, horizon=1).set_index("cust")[["x", "t_x", "T_cal"]]

    pd.testing.assert_frame_equal(a.sort_index(), b.sort_index())
