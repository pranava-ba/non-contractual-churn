"""arXiv feeds: by category, cross-listed (papers tagged in ALL given groups),
and raw keyword search. Date filtering is done client-side by sorting newest
first and stopping once we pass the lookback window (more reliable than arXiv's
submittedDate range syntax)."""
from __future__ import annotations

import random
import re
import time

import feedparser
import requests

BASE = "http://export.arxiv.org/api/query"

_last_request = 0.0  # monotonic time of the last arXiv hit (module-wide throttle)
CALLS_MADE = 0        # bumped per request sent; read by run.py for the budget report


def _get(session, params, cfg):
    """Politely-spaced GET with jittered retries on transient rate limits (429/503)."""
    global _last_request, CALLS_MADE
    delay = cfg.settings["arxiv_delay"]
    timeout = cfg.settings["request_timeout"]
    headers = {"User-Agent": f"paper-tracker ({cfg.settings['contact_email']})"}
    for attempt in range(3):
        wait = delay - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        CALLS_MADE += 1
        r = session.get(BASE, params=params, headers=headers, timeout=timeout)
        _last_request = time.monotonic()
        if r.status_code in (429, 503) and attempt < 2:
            time.sleep(delay * (attempt + 2) + random.uniform(0, 1.0))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


# "q-fin" is a group, not a real category; expand to its sub-categories.
QFIN_SUBCATS = [
    "q-fin.CP", "q-fin.EC", "q-fin.GN", "q-fin.MF",
    "q-fin.PM", "q-fin.PR", "q-fin.RM", "q-fin.ST", "q-fin.TR",
]


def _expand(token: str) -> list[str]:
    return QFIN_SUBCATS if token == "q-fin" else [token]


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _base_id(entry_id: str) -> str:
    # http://arxiv.org/abs/2507.12345v2  ->  2507.12345
    frag = entry_id.rsplit("/abs/", 1)[-1]
    return re.sub(r"v\d+$", "", frag)


def _normalize(entry, cfg) -> dict | None:
    title = _ws(entry.get("title"))
    if not title:
        return None
    arxiv_id = _base_id(entry.get("id", ""))
    doi = (entry.get("arxiv_doi") or "").strip().lower() or None
    if doi and doi.startswith("10.48550/arxiv."):
        doi = None  # that's just the arXiv id again; dedupe on arxiv:<id>
    uid = f"doi:{doi}" if doi else f"arxiv:{arxiv_id}"
    authors = [a.get("name") for a in entry.get("authors", []) if a.get("name")][:25]
    cats = [t.get("term") for t in entry.get("tags", []) if t.get("term")]
    return {
        "uid": uid,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "oa_url": None,
        "title": title,
        "abstract": _ws(entry.get("summary")),
        "authors": authors,
        "venue": "arXiv (" + ", ".join(cats[:3]) + ")" if cats else "arXiv",
        "publication_date": (entry.get("published", "") or "")[:10],
        "source": "arxiv",
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "tier": cfg.settings["arxiv_tier"],
        "relevance": 0.0,
    }


def _search(query: str, cfg, date_from: str, date_to: str | None = None) -> list[dict]:
    session = requests.Session()
    page = cfg.settings["arxiv_page_size"]
    out: list[dict] = []
    seen: set[str] = set()
    try:
        for pg in range(cfg.settings["arxiv_max_pages"]):
            params = {
                "search_query": query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": pg * page,
                "max_results": page,
            }
            r = _get(session, params, cfg)
            feed = feedparser.parse(r.content)
            if not feed.entries:
                break
            found_older = False
            for entry in feed.entries:
                pub = (entry.get("published", "") or "")[:10]
                if pub and pub < date_from:
                    found_older = True
                    continue
                if date_to and pub and pub > date_to:
                    # Only matters for a bounded historical/reproducibility window
                    # (arXiv is sorted newest-first, so these are skipped, not
                    # stopped-at -- a later page can still contain in-window hits).
                    continue
                p = _normalize(entry, cfg)
                if p and p["uid"] not in seen:
                    seen.add(p["uid"])
                    out.append(p)
            # Sorted newest-first: once a page contains anything older than the
            # window, everything after is older too.
            if found_older or len(feed.entries) < page:
                break
    except requests.RequestException:
        # Keep whatever pages already succeeded rather than discarding them —
        # see the matching comment in sources/openalex.py's _paged.
        if not out:
            raise
    return out


def fetch_categories(cfg, cats: list[str], date_from: str, date_to: str | None = None) -> list[dict]:
    terms = []
    for c in cats:
        terms.extend(f"cat:{x}" for x in _expand(c))
    query = " OR ".join(terms)
    return _search(query, cfg, date_from, date_to)


def fetch_cross(cfg, all_of: list[str], date_from: str, date_to: str | None = None) -> list[dict]:
    """Papers cross-listed in EVERY group of `all_of` (each group may expand)."""
    groups = []
    for token in all_of:
        expanded = _expand(token)
        groups.append("(" + " OR ".join(f"cat:{x}" for x in expanded) + ")")
    query = " AND ".join(groups)
    return _search(query, cfg, date_from, date_to)


def fetch_keyword(cfg, query: str, date_from: str, date_to: str | None = None) -> list[dict]:
    return _search(query, cfg, date_from, date_to)
