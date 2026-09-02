"""Category filtering (include/exclude terms), a universal match score, and
ranking with a top-N cap."""
from __future__ import annotations

import re


GROUP_CAP = 5  # cap a single group's contribution so term-density can't dominate ranking


def _compile_term(term: str) -> re.Pattern:
    """Word-boundary, case-insensitive matcher. Trailing '*' means prefix match.
    Internal spaces/hyphens are interchangeable, so "gold standard" also matches
    "gold-standard" and "information-theoretic" matches "information theoretic"."""
    term = term.strip().lower()
    prefix = term.endswith("*")
    if prefix:
        term = term[:-1]
    # space / hyphen / slash are interchangeable, so "Pareto/NBD" also matches
    # "Pareto NBD" and "Pareto-NBD", and "gold standard" matches "gold-standard".
    tokens = [re.escape(t) for t in re.split(r"[\s\-/]+", term) if t]
    body = r"[\s\-/]+".join(tokens)
    pattern = r"\b" + body + (r"\w*" if prefix else r"\b")
    return re.compile(pattern, re.IGNORECASE)


def compile_category(category: dict) -> tuple[list[list[re.Pattern]], list[re.Pattern]]:
    groups = [
        [_compile_term(t) for t in group]
        for group in category.get("require_all", [])
    ]
    excludes = [_compile_term(t) for t in category.get("exclude", [])]
    return groups, excludes


def evaluate(paper, groups, excludes, min_hits=None):
    """Return an int match_score if the paper qualifies, else None.

    - Any exclude term present  -> reject.
    - Each require_all group must reach its threshold (default 1). A term hit
      counts once, or twice if it appears in the title, so `min_hits=[2, 2]`
      is met by either 2 distinct terms or 1 term in the title.
    - Score sums the (capped) per-group strengths.
    """
    title = (paper.get("title") or "").lower()
    text = title + " \n " + (paper.get("abstract") or "").lower()

    for ex in excludes:
        if ex.search(text):
            return None

    if not groups:
        return 0  # topic buckets: journal/category membership is the filter

    total = 0
    for gi, group in enumerate(groups):
        strength = 0
        for term in group:
            if term.search(text):
                strength += 1
                if term.search(title):
                    strength += 1  # a hit in the title is a stronger signal
        need = min_hits[gi] if (min_hits and gi < len(min_hits)) else 1
        if strength < need:
            return None
        total += min(strength, GROUP_CAP)
    return total


def any_match(paper: dict, compiled: list[re.Pattern]) -> bool:
    """True if any compiled term appears in the paper's title or abstract."""
    text = (paper.get("title") or "").lower() + " \n " + (paper.get("abstract") or "").lower()
    return any(rx.search(text) for rx in compiled)


def matched_terms(paper: dict, category: dict) -> list[str]:
    """The category search terms this paper actually matched — the human-readable
    'why it surfaced'. Empty for topic buckets (they match by journal, not terms).
    Only called on the surfaced top-N, so recompiling here is cheap."""
    groups = category.get("require_all", [])
    if not groups:
        return []
    title = (paper.get("title") or "").lower()
    text = title + " \n " + (paper.get("abstract") or "").lower()
    out: list[str] = []
    for group in groups:
        for term in group:
            if _compile_term(term).search(text):
                clean = term.rstrip("*")
                if clean not in out:
                    out.append(clean)
    return out


def _date_ord(paper: dict) -> int:
    d = (paper.get("publication_date") or "").replace("-", "")
    return int(d) if len(d) == 8 and d.isdigit() else 0


def _venue_key(paper: dict) -> str:
    if paper.get("source") == "arxiv":
        return "arxiv"
    return (paper.get("venue") or "").strip().lower()


def rank(papers: list[dict], rank_by: str, top_n: int, max_per_venue: int | None = None) -> list[dict]:
    if rank_by == "tier":
        # journal prestige first, then newest, then match strength
        papers.sort(key=lambda p: (p["tier"], -_date_ord(p), -p.get("match_score", 0)))
    else:  # "relevance": match strength, then API relevance, tier, recency
        papers.sort(
            key=lambda p: (
                -p.get("match_score", 0),
                -p.get("relevance", 0.0),
                p["tier"],
                -_date_ord(p),
            )
        )

    if not max_per_venue or len(papers) <= top_n:
        return papers[:top_n]

    # Greedily take the best while capping each venue; keep a queue of the
    # capped-out ones to backfill if diversity can't fill top_n.
    selected: list[dict] = []
    overflow: list[dict] = []
    counts: dict[str, int] = {}
    for p in papers:
        v = _venue_key(p)
        if counts.get(v, 0) < max_per_venue:
            selected.append(p)
            counts[v] = counts.get(v, 0) + 1
            if len(selected) >= top_n:
                return selected
        else:
            overflow.append(p)
    for p in overflow:  # relax the cap only to reach top_n
        if len(selected) >= top_n:
            break
        selected.append(p)
    return selected[:top_n]
