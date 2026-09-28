"""Semantic Scholar: not a feed (we don't page a keyword search here), just an
abstract-backfill step. Many publishers hand Crossref no abstract, and some
OpenAlex records lack an `abstract_inverted_index` (Elsevier opt-outs are the
common case) -- title-only text then silently weakens `src/match.py`'s scoring
and can drop a genuinely relevant paper. Semantic Scholar's free API (no key
needed) covers most published papers and preprints by DOI or arXiv id and often
has an abstract where the primary sources didn't.
"""
from __future__ import annotations

import time

import requests

BASE = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = "abstract"
CALLS_MADE = 0


def backfill_abstracts(papers: list[dict], cfg) -> int:
    """Fill in `abstract` (in place) for any paper missing one and carrying a
    doi or arxiv_id. Returns how many were filled. Best-effort: any failure here
    just leaves abstracts as they were: this is a precision aid, not core to a run.
    """
    global CALLS_MADE
    if not cfg.settings.get("semanticscholar_backfill", True):
        return 0
    targets = [p for p in papers if not (p.get("abstract") or "").strip()
               and (p.get("doi") or p.get("arxiv_id"))]
    if not targets:
        return 0

    def s2_id(p: dict) -> str:
        return f"arXiv:{p['arxiv_id']}" if p.get("arxiv_id") else f"DOI:{p['doi']}"

    filled = 0
    session = requests.Session()
    timeout = cfg.settings["request_timeout"]
    delay = cfg.settings.get("semanticscholar_delay", 1.0)
    batch_size = 500  # S2's documented batch endpoint limit
    for i in range(0, len(targets), batch_size):
        batch = targets[i:i + batch_size]
        ids = [s2_id(p) for p in batch]
        try:
            CALLS_MADE += 1
            r = session.post(BASE, params={"fields": FIELDS}, json={"ids": ids}, timeout=timeout)
            if r.status_code == 429:
                continue  # best-effort: skip this batch rather than block a whole refresh
            r.raise_for_status()
            results = r.json()
        except (requests.RequestException, ValueError):
            continue
        for p, rec in zip(batch, results or []):
            if rec and rec.get("abstract"):
                p["abstract"] = rec["abstract"]
                filled += 1
        if i + batch_size < len(targets):
            time.sleep(delay)
    return filled
