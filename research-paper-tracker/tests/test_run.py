from datetime import date

from src import run, store


SETTINGS = {"lag_margin_days": 2, "max_lookback_days": 60, "lookback_days": 7,
           "min_publication_date": ""}


def test_window_start_explicit_lookback_ignores_history(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    today = date(2026, 6, 15)
    start = run._window_start(conn, SETTINGS, today, lookback=30)
    assert start == date(2026, 5, 16)
    conn.close()


def test_window_start_first_run_with_floor_is_comprehensive(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    settings = dict(SETTINGS, min_publication_date="1959-01-01")
    today = date(2026, 6, 15)
    start = run._window_start(conn, settings, today, lookback=None)
    assert start == date(1959, 1, 1)
    conn.close()


def test_window_start_first_run_no_floor_uses_lookback_days(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    today = date(2026, 6, 15)
    start = run._window_start(conn, SETTINGS, today, lookback=None)
    assert start == date(2026, 6, 8)  # today - lookback_days(7)
    conn.close()


def test_window_start_auto_since_last_refresh_plus_lag_margin(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.record_run(conn, "2026-06-01T00:00:00", "2026-06-01", "2026-05-25", "2026-06-01", 5, 0)
    today = date(2026, 6, 10)
    start = run._window_start(conn, SETTINGS, today, lookback=None)
    assert start == date(2026, 5, 30)  # last_run - lag_margin_days(2)
    conn.close()


def test_window_start_is_capped_at_max_lookback(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.record_run(conn, "2020-01-01T00:00:00", "2020-01-01", "2019-12-01", "2020-01-01", 5, 0)
    today = date(2026, 6, 10)  # last refresh is years ago
    start = run._window_start(conn, SETTINGS, today, lookback=None)
    assert start == today - __import__("datetime").timedelta(days=SETTINGS["max_lookback_days"])
    conn.close()


def test_better_prefers_higher_match_score():
    a = {"match_score": 5, "relevance": 0.1, "tier": 3}
    b = {"match_score": 2, "relevance": 0.9, "tier": 1}
    assert run._better(a, b) is True
    assert run._better(b, a) is False


def test_merge_backfills_missing_fields_from_the_loser():
    winner = {"match_score": 5, "relevance": 0.1, "tier": 3, "abstract": "", "oa_url": None,
             "doi": "10.1/a", "arxiv_id": None, "venue": "J", "authors": []}
    loser = {"match_score": 1, "relevance": 0.1, "tier": 3, "abstract": "a real abstract",
            "oa_url": "https://oa.example/pdf", "doi": None, "arxiv_id": None,
            "venue": "", "authors": ["A. Author"]}
    merged = run._merge(winner, loser)
    assert merged["match_score"] == 5          # kept the winner's own fields
    assert merged["abstract"] == "a real abstract"  # backfilled from the loser
    assert merged["oa_url"] == "https://oa.example/pdf"
    assert merged["doi"] == "10.1/a"           # winner's own non-empty field is NOT overwritten
