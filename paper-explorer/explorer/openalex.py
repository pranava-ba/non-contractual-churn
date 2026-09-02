"""Standalone OpenAlex client for the explorer.

Three primitives:
    search_core()  -> journal-only (NOT conference) AI/ML candidate papers
    references()   -> works the core paper cites   (filter=cited_by:)  -> helpers
    citations()    -> works that cite the core      (filter=cites:)     -> additional

Kept dependency-free of the tracker's config so this tool can be packaged on its
own. Borrows the polite-pool + abstract-reconstruction + retry patterns.
"""
from __future__ import annotations

import time

import requests

BASE = "https://api.openalex.org/works"
MAILTO = "pranavabaascaran@gmail.com"          # OpenAlex "polite pool" -> faster, kinder
TIMEOUT = 30
MIN_YEAR = 2023                                # hard floor: never consider papers before this

# Fields we pull. Kept tight to keep responses small and fast.
SELECT = (
    "id,doi,title,publication_year,publication_date,cited_by_count,"
    "primary_location,best_oa_location,open_access,authorships,"
    "abstract_inverted_index,primary_topic,referenced_works_count"
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": f"paper-explorer (mailto:{MAILTO})"})
    return s


def _get(session: requests.Session, params: dict) -> dict:
    """GET with a few retries on transient rate limits (429/503)."""
    params = {**params, "mailto": MAILTO}
    last = None
    for attempt in range(3):
        r = session.get(BASE, params=params, timeout=TIMEOUT)
        if r.status_code in (429, 503) and attempt < 2:
            time.sleep(1.0 * (attempt + 1))
            last = r
            continue
        r.raise_for_status()
        return r.json()
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("OpenAlex request failed")


def _reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def _bare_doi(doi_url: str | None) -> str | None:
    if not doi_url:
        return None
    return (doi_url.replace("https://doi.org/", "")
                   .replace("http://doi.org/", "").lower())


def _short_id(oa_id: str | None) -> str:
    return (oa_id or "").rsplit("/", 1)[-1]


def _normalize(work: dict) -> dict | None:
    title = work.get("title")
    if not title:
        return None
    source = (work.get("primary_location") or {}).get("source") or {}
    best = work.get("best_oa_location") or {}
    oa = work.get("open_access") or {}
    topic = work.get("primary_topic") or {}

    authors = [
        a["author"]["display_name"]
        for a in (work.get("authorships") or [])
        if a.get("author", {}).get("display_name")
    ][:25]

    bare = _bare_doi(work.get("doi"))
    short = _short_id(work.get("id"))
    url = (f"https://doi.org/{bare}" if bare else work.get("id") or "")

    return {
        "id": short,
        "oa_id": work.get("id") or "",
        "doi": bare,
        "title": title.strip(),
        "year": work.get("publication_year"),
        "date": work.get("publication_date", "") or "",
        "citations": int(work.get("cited_by_count") or 0),
        "venue": source.get("display_name") or "",
        "venue_type": source.get("type") or "",
        "issn": source.get("issn_l") or "",
        "authors": authors,
        "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        "oa_url": best.get("pdf_url") or oa.get("oa_url") or None,
        "is_oa": bool(oa.get("is_oa")),
        "topic": topic.get("display_name") or "",
        "ref_count": int(work.get("referenced_works_count") or 0),
        "url": url,
    }


def _paged(session, params: dict, per_page: int, max_pages: int) -> list[dict]:
    out: list[dict] = []
    params = {**params, "per-page": per_page, "select": SELECT}
    for page in range(1, max_pages + 1):
        params["page"] = page
        data = _get(session, params)
        results = data.get("results", [])
        for w in results:
            p = _normalize(w)
            if p:
                out.append(p)
        if len(results) < per_page:
            break
        time.sleep(0.2)
    return out


def search_core(query: str, year_from: int = MIN_YEAR, min_citations: int = 20,
                limit: int = 40, journals_only: bool = True) -> list[dict]:
    """Journal-only AI/ML candidate papers, ranked by OpenAlex relevance.

    journals_only=True adds `primary_location.source.type:journal`, which
    excludes conference proceedings by construction — that's the hard
    'journal, NOT a conference' requirement. `year_from` is clamped to MIN_YEAR
    so papers before that are never considered.
    """
    session = _session()
    year_from = max(int(year_from), MIN_YEAR)
    filters = [
        "type:article",
        f"from_publication_date:{year_from}-01-01",
    ]
    if min_citations > 0:
        filters.append(f"cited_by_count:>{min_citations - 1}")
    if journals_only:
        filters.append("primary_location.source.type:journal")
    params = {
        "search": query,
        "filter": ",".join(filters),
        "sort": "relevance_score:desc",
    }
    per_page = min(limit, 50)
    max_pages = max(1, (limit + per_page - 1) // per_page)
    return _paged(session, params, per_page, max_pages)[:limit]


def references(work_id: str, limit: int = 10) -> list[dict]:
    """Works the core paper CITES (its bibliography), most-cited first.

    filter=cited_by:<id> returns the reference list with full metadata, so we
    can rank the foundational ones to the top -> your 'helper' papers.
    """
    session = _session()
    params = {
        "filter": f"cited_by:{work_id}",
        "sort": "cited_by_count:desc",
    }
    return _paged(session, params, min(limit, 50), 1)[:limit]


def citations(work_id: str, limit: int = 40, sort: str = "cited_by_count:desc") -> list[dict]:
    """Works that CITE the core (forward citations) -> your 'additional' pool.

    sort: "cited_by_count:desc" (most influential) or "publication_date:desc"
    (most recent).
    """
    session = _session()
    params = {"filter": f"cites:{work_id}", "sort": sort}
    per_page = min(limit, 50)
    max_pages = max(1, (limit + per_page - 1) // per_page)
    return _paged(session, params, per_page, max_pages)[:limit]
