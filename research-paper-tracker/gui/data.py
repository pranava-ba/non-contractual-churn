"""Read-only snapshot of the tracker DB, shaped for the GUI. Pure/testable."""
from __future__ import annotations

from src.config import load_config
from src import citations, store, status


def _paper(row, used_by_group: dict[str, "citations.BibIndex | None"] | None = None,
          group: str | None = None) -> dict:
    override_raw = row["used_override"] if "used_override" in row.keys() else None
    override = None if override_raw is None else bool(override_raw)
    auto = None
    if used_by_group and group:
        idx = used_by_group.get(group)
        if idx is not None:
            auto = idx.match(row["doi"], row["arxiv_id"], row["title"]) is not None
    used = override if override is not None else auto
    return {
        "uid": row["uid"],
        "rank": row["rank"] if "rank" in row.keys() else None,
        "title": row["title"] or "",
        "doi": row["doi"] or "",
        "arxiv_id": row["arxiv_id"] or "",
        "oa_url": row["oa_url"] or "",
        "read": bool(row["read"]),
        "starred": bool(row["starred"]),
        "hidden": bool(row["hidden"]),
        "analyzed": bool(row["analyzed"]) if "analyzed" in row.keys() else False,
        "used": used,           # display value: override if set, else auto-detect
        "used_auto": auto,      # the bib cross-reference's own verdict (bool or None)
        "used_override": override,  # manual override (bool), or None = "trust auto"
        "tags": row["tags"] or "",
        "url": row["url"] or "",
        "venue": row["venue"] or "",
        "date": row["publication_date"] or "",
        "authors": row["authors"] or "",
        "source": row["source"] or "",
        "match_score": row["match_score"] if "match_score" in row.keys() else None,
        "relevance": round(row["relevance"] or 0.0, 2) if "relevance" in row.keys() else 0.0,
        "matched_terms": (row["matched_terms"] or "") if "matched_terms" in row.keys() else "",
        "run_date": row["run_date"] if "run_date" in row.keys() else None,
        "first_seen": row["first_seen"] or "",
        "abstract": row["abstract"] or "",
    }


def snapshot(cfg=None) -> dict:
    """Everything the UI needs in one call: status, weeks, categories, papers,
    and the NBD/causal Coverage grouping (each tracked paper once, tagged with
    read/analyzed/used)."""
    cfg = cfg or load_config()
    conn = store.connect(cfg.path("db_path"))
    try:
        st = status.refresh_status(conn, cfg.settings)
        weeks = store.list_run_dates(conn)
        cats = [
            {"key": c["key"], "label": c["label"], "important": bool(c.get("important")),
             "group": c.get("group")}
            for c in cfg.categories
        ]
        papers = {
            c["key"]: [_paper(r) for r in store.papers_for_category(conn, c["key"])]
            for c in cfg.categories
        }
        used_by_group = {
            group: citations.load_index(cfg.bib_path(group)) for group in ("nbd", "causal")
        }
        coverage = _coverage(conn, cfg, used_by_group)
        return {"status": st, "weeks": weeks, "categories": cats, "papers": papers,
                "coverage": coverage}
    finally:
        conn.close()


def _coverage(conn, cfg, used_by_group: dict) -> dict:
    """One row per tracked (non-hidden) paper, grouped by its category's `group:`
    (nbd / causal) for the Coverage page. A paper in categories spanning both
    groups (shouldn't happen given the current config, but not assumed) is listed
    under each group it belongs to."""
    group_of = {c["key"]: c.get("group") for c in cfg.categories}
    out: dict[str, list[dict]] = {"nbd": [], "causal": []}
    for row in store.all_papers(conn):
        if row["hidden"]:
            continue
        cats_here = (row["categories"] or "").split("|") if row["categories"] else []
        groups_here = {group_of.get(c) for c in cats_here if group_of.get(c)}
        for group in groups_here:
            out.setdefault(group, []).append(_paper(row, used_by_group, group))
    return out
