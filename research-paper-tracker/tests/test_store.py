from src import store


def _paper(uid, **overrides):
    p = {
        "uid": uid, "doi": None, "arxiv_id": None, "oa_url": None,
        "title": f"Title {uid}", "abstract": "abs", "authors": ["A. Author"],
        "venue": "Some Journal", "publication_date": "2024-01-01", "source": "openalex",
        "url": "https://example.com", "match_score": 3, "relevance": 0.5, "matched_terms": "churn",
    }
    p.update(overrides)
    return p


def test_connect_creates_schema_and_is_idempotent(tmp_path):
    db = tmp_path / "t.db"
    conn1 = store.connect(db)
    conn1.close()
    conn2 = store.connect(db)  # re-running migrations against an existing DB must not raise
    conn2.close()


def test_persist_and_seen_roundtrip(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    papers = [_paper("doi:10.1/a"), _paper("doi:10.1/b")]
    store.persist_selection(conn, "cat1", papers, "2026-01-01")
    store.mark_seen(conn, "cat1", [p["uid"] for p in papers], "2026-01-01")

    seen = store.existing_uids_for_category(conn, "cat1")
    assert seen == {"doi:10.1/a", "doi:10.1/b"}

    rows = store.papers_for_category(conn, "cat1")
    assert {r["uid"] for r in rows} == {"doi:10.1/a", "doi:10.1/b"}
    assert rows[0]["read"] == 0 and rows[0]["hidden"] == 0
    conn.close()


def test_set_state_and_get_paper(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.persist_selection(conn, "cat1", [_paper("doi:10.1/a")], "2026-01-01")
    store.set_state(conn, "doi:10.1/a", "read", True)
    store.set_state(conn, "doi:10.1/a", "analyzed", True)
    row = store.papers_for_category(conn, "cat1")[0]
    assert row["read"] == 1 and row["analyzed"] == 1
    conn.close()


def test_set_used_override_roundtrip(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.persist_selection(conn, "cat1", [_paper("doi:10.1/a")], "2026-01-01")
    row = store.papers_for_category(conn, "cat1")[0]
    assert row["used_override"] is None  # default: trust auto-detect
    store.set_used_override(conn, "doi:10.1/a", True)
    row = store.papers_for_category(conn, "cat1")[0]
    assert row["used_override"] == 1
    store.set_used_override(conn, "doi:10.1/a", None)  # revert to auto
    row = store.papers_for_category(conn, "cat1")[0]
    assert row["used_override"] is None
    conn.close()


def test_alias_map(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.add_alias(conn, "arxiv:1234.5678", "doi:10.1/a", "same title", "2026-01-01")
    assert store.alias_map(conn) == {"arxiv:1234.5678": "doi:10.1/a"}
    conn.close()


def test_api_call_budget_accumulates_per_day(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.record_api_calls(conn, "2026-01-01", "openalex", 3)
    store.record_api_calls(conn, "2026-01-01", "openalex", 2)
    store.record_api_calls(conn, "2026-01-01", "crossref", 1)
    assert store.api_calls_today(conn, "2026-01-01", "openalex") == 5
    assert store.api_calls_today(conn, "2026-01-01", "crossref") == 1
    assert store.api_calls_today(conn, "2026-01-02", "openalex") == 0
    conn.close()


def test_seen_prevents_resurfacing_across_runs(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    store.mark_seen(conn, "cat1", ["doi:10.1/a"], "2026-01-01")
    seen = store.existing_uids_for_category(conn, "cat1")
    assert "doi:10.1/a" in seen
    # a different category's `seen` set is independent
    assert store.existing_uids_for_category(conn, "cat2") == set()
    conn.close()
