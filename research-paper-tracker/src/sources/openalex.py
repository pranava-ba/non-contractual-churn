"""OpenAlex feeds: journal-scoped (by ISSN) and open keyword search."""
from __future__ import annotations

import random
import re
import time

import requests

BASE = "https://api.openalex.org/works"
SELECT = ("id,doi,title,publication_date,relevance_score,primary_location,authorships,"
          "abstract_inverted_index,open_access,best_oa_location,concepts")

# Bumped when a request is actually sent, so run.py can report how many hit the API
# this run (feeds into the daily-budget check in store.api_calls / config settings).
CALLS_MADE = 0


def _get(session, params, cfg):
    """GET with a SHORT, jittered backoff on transient rate limits, but fail fast on
    a hard block (server sends a big Retry-After) so a refresh never hangs for
    minutes. Jitter avoids every retry landing on the same wall-clock second as
    other callers sharing this IP's rate-limit bucket."""
    global CALLS_MADE
    timeout = cfg.settings["request_timeout"]
    for attempt in range(3):
        CALLS_MADE += 1
        r = session.get(BASE, params=params, timeout=timeout)
        if r.status_code in (429, 503):
            retry_after = 0
            try:
                retry_after = int(r.headers.get("Retry-After", 0))
            except ValueError:
                pass
            if retry_after > 60:            # hard block (minutes/hours) — don't wait
                r.raise_for_status()
            if attempt < 2:
                base_wait = retry_after or (attempt + 1) * 2
                time.sleep(min(base_wait + random.uniform(0, 1.5), 6))
                continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


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
    return doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "").lower()


def _source_issns(source: dict) -> list[str]:
    issns: list[str] = []
    if source.get("issn_l"):
        issns.append(source["issn_l"])
    for i in source.get("issn") or []:
        if i not in issns:
            issns.append(i)
    return issns


def _normalize(work: dict, cfg) -> dict | None:
    title = work.get("title")
    if not title:
        return None
    source = (work.get("primary_location") or {}).get("source") or {}
    issns = _source_issns(source)
    tier = cfg.settings["unknown_venue_tier"]
    is_sieve = False
    for issn in issns:
        if issn in cfg.issn_tier:
            tier = cfg.issn_tier[issn]
            is_sieve = issn in cfg.sieve_issns
            break

    bare = _bare_doi(work.get("doi"))
    arxiv_id = None
    if bare and bare.startswith("10.48550/arxiv."):
        # OpenAlex indexes arXiv preprints under a 10.48550/arXiv.* DOI.
        # Canonicalize to the arXiv id so these dedupe against the arXiv feed.
        arxiv_id = re.sub(r"v\d+$", "", bare[len("10.48550/arxiv."):])
        uid = f"arxiv:{arxiv_id}"
        url = f"https://arxiv.org/abs/{arxiv_id}"
    elif bare:
        uid = f"doi:{bare}"
        url = f"https://doi.org/{bare}"
    else:
        oa_id = (work.get("id") or "").rsplit("/", 1)[-1]
        uid = f"openalex:{oa_id}"
        url = work.get("id") or ""

    authors = [
        a["author"]["display_name"]
        for a in (work.get("authorships") or [])
        if a.get("author", {}).get("display_name")
    ][:25]

    best = work.get("best_oa_location") or {}
    oa_url = (best.get("pdf_url") or (work.get("open_access") or {}).get("oa_url")
              or (work.get("primary_location") or {}).get("pdf_url"))

    # Topic concepts (OpenAlex's own classifier) as a secondary relevance signal,
    # alongside the keyword regex match in src/match.py -- catches papers whose
    # abstract is generic but whose classified topic is squarely on point, and can
    # down-weight a keyword false positive whose top concepts are unrelated.
    concepts = sorted(
        ((c.get("display_name", ""), float(c.get("score", 0.0)))
         for c in (work.get("concepts") or []) if c.get("score", 0) >= 0.3),
        key=lambda c: -c[1],
    )[:6]

    return {
        "uid": uid,
        "doi": bare,
        "arxiv_id": arxiv_id,
        "oa_url": oa_url,
        "_src_type": source.get("type"),
        "_sieve": is_sieve,
        "title": title.strip(),
        "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        "authors": authors,
        "venue": source.get("display_name", "") or "",
        "publication_date": work.get("publication_date", "") or "",
        "source": "openalex",
        "url": url,
        "tier": tier,
        "relevance": float(work.get("relevance_score") or 0.0),
        "concepts": concepts,
    }


def _paged(params: dict, cfg, max_pages: int) -> list[dict]:
    session = requests.Session()
    per_page = cfg.settings["openalex_per_page"]
    params = dict(params)
    params.update(
        {
            "per-page": per_page,
            "select": SELECT,
            "mailto": cfg.settings["contact_email"],
        }
    )
    out: list[dict] = []
    try:
        for page in range(1, max_pages + 1):
            params["page"] = page
            r = _get(session, params, cfg)
            results = r.json().get("results", [])
            for w in results:
                p = _normalize(w, cfg)
                if p:
                    out.append(p)
            if len(results) < per_page:
                break
            time.sleep(cfg.settings["openalex_delay"])
    except requests.RequestException:
        # A hard failure mid-paging (e.g. a rate-limit block on page 2 of 3) used
        # to discard every page already fetched this call. Keep what we have —
        # partial coverage beats silently losing already-fetched candidates.
        if not out:
            raise
    return out


def fetch_journals(cfg, areas: list[str], date_from: str, date_to: str) -> list[dict]:
    issns = []
    for area in areas:
        for j in cfg.area_journals(area):
            issns.append(j["issn"])
    issn_filter = "|".join(issns)
    params = {
        "filter": (
            f"primary_location.source.issn:{issn_filter},"
            f"from_publication_date:{date_from},to_publication_date:{date_to}"
        ),
        "sort": "publication_date:desc",
    }
    # Journal weekly volume is small; a couple of pages is plenty.
    return _paged(params, cfg, cfg.settings["openalex_max_pages"])


def fetch_keyword(cfg, query: str, date_from: str, date_to: str) -> list[dict]:
    params = {
        "search": query,
        "filter": f"from_publication_date:{date_from},to_publication_date:{date_to}",
    }
    # Default sort with `search` is relevance:desc — top pages are the most relevant.
    papers = _paged(params, cfg, cfg.settings["openalex_max_pages"])
    if cfg.settings.get("keyword_exclude_repositories", True):
        # Drop Zenodo / Research Square / SSRN-style preprint mills. Genuine
        # preprints still arrive via the arXiv feed.
        papers = [p for p in papers if p.get("_src_type") != "repository"]
    return papers
