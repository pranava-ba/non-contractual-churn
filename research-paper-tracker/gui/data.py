"""Read-only snapshot of the tracker DB, shaped for the GUI. Pure/testable."""
from __future__ import annotations

from src.config import load_config
from src import store, status


def _paper(row) -> dict:
    return {
        "uid": row["uid"],
        "rank": row["rank"],
        "title": row["title"] or "",
        "doi": row["doi"] or "",
        "arxiv_id": row["arxiv_id"] or "",
        "oa_url": row["oa_url"] or "",
        "read": bool(row["read"]),
        "starred": bool(row["starred"]),
        "hidden": bool(row["hidden"]),
        "tags": row["tags"] or "",
        "url": row["url"] or "",
        "venue": row["venue"] or "",
        "date": row["publication_date"] or "",
        "authors": row["authors"] or "",
        "source": row["source"] or "",
        "match_score": row["match_score"],
        "relevance": round(row["relevance"] or 0.0, 2),
        "matched_terms": (row["matched_terms"] or ""),
        "run_date": row["run_date"],
        "first_seen": row["first_seen"] or "",
        "abstract": row["abstract"] or "",
    }


def snapshot(cfg=None) -> dict:
    """Everything the UI needs in one call: status, weeks, categories, papers."""
    cfg = cfg or load_config()
    conn = store.connect(cfg.path("db_path"))
    try:
        st = status.refresh_status(conn, cfg.settings)
        weeks = store.list_run_dates(conn)
        cats = [
            {"key": c["key"], "label": c["label"], "important": bool(c.get("important"))}
            for c in cfg.categories
        ]
        papers = {
            c["key"]: [_paper(r) for r in store.papers_for_category(conn, c["key"])]
            for c in cfg.categories
        }
        return {"status": st, "weeks": weeks, "categories": cats, "papers": papers}
    finally:
        conn.close()
