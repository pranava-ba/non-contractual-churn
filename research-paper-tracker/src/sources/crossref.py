"""Crossref keyword feed. A DOI-registry search across all publishers — a second
source alongside OpenAlex (and unaffected by OpenAlex rate limits). Returns papers
in the same normalized shape as the other sources.
"""
from __future__ import annotations

import html
import re

import requests

BASE = "https://api.crossref.org/works"
SELECT = ("DOI,title,container-title,published,published-online,published-print,"
          "issued,author,score,abstract")


def _strip_jats(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)          # drop JATS/XML tags
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"^abstract[:\s]*", "", s, flags=re.I)


def _date(item: dict) -> str:
    for key in ("published", "issued", "published-online", "published-print"):
        parts = (item.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            p = parts[0]
            y = p[0]
            m = p[1] if len(p) > 1 else 1
            d = p[2] if len(p) > 2 else 1
            return f"{y:04d}-{m:02d}-{d:02d}"
    return ""


def _normalize(item: dict, cfg) -> dict | None:
    titles = item.get("title") or []
    doi = (item.get("DOI") or "").lower()
    if not titles or not doi:
        return None
    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in (item.get("author") or [])
        if a.get("family") or a.get("given")
    ][:25]
    return {
        "uid": f"doi:{doi}",
        "doi": doi,
        "arxiv_id": None,
        "oa_url": None,
        "title": titles[0].strip(),
        "abstract": _strip_jats(item.get("abstract", "")),
        "authors": authors,
        "venue": (item.get("container-title") or [""])[0],
        "publication_date": _date(item),
        "source": "crossref",
        "url": f"https://doi.org/{doi}",
        "tier": cfg.settings["unknown_venue_tier"],
        "relevance": float(item.get("score") or 0.0),
    }


def fetch_keyword(cfg, query: str, date_from: str, date_to: str) -> list[dict]:
    rows = int(cfg.settings.get("crossref_rows", 600))
    params = {
        "query": query,
        "filter": f"from-pub-date:{date_from},until-pub-date:{date_to},type:journal-article",
        "rows": rows,
        "mailto": cfg.settings["contact_email"],
        "select": SELECT,
    }
    ua = f"research-paper-tracker/1.0 (mailto:{cfg.settings['contact_email']})"
    r = requests.get(BASE, params=params, headers={"User-Agent": ua},
                     timeout=cfg.settings["request_timeout"])
    r.raise_for_status()
    items = r.json().get("message", {}).get("items", [])
    out = []
    for it in items:
        p = _normalize(it, cfg)
        if p:
            out.append(p)
    return out
