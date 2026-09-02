"""Export selected papers as BibTeX or CSV for the report's reference section."""
from __future__ import annotations

import csv
import io
import re


def _cite_key(paper: dict) -> str:
    first = (paper.get("authors") or ["anon"])[0].split()[-1]
    first = re.sub(r"[^A-Za-z]", "", first) or "anon"
    year = str(paper.get("year") or "n.d.")
    word = ""
    for w in re.findall(r"[A-Za-z]+", paper.get("title", "")):
        if len(w) > 3:
            word = w.lower()
            break
    return f"{first.lower()}{year}{word}"


def _bibtex_one(paper: dict, key: str) -> str:
    authors = " and ".join(paper.get("authors") or [])
    fields = {
        "title": paper.get("title", ""),
        "author": authors,
        "journal": paper.get("venue", ""),
        "year": paper.get("year", ""),
        "doi": paper.get("doi", "") or "",
        "url": paper.get("url", "") or "",
    }
    lines = [f"@article{{{key},"]
    for k, v in fields.items():
        if v:
            lines.append(f"  {k} = {{{v}}},")
    lines.append("}")
    return "\n".join(lines)


def to_bibtex(papers: list[dict]) -> str:
    seen: dict[str, int] = {}
    out = []
    for p in papers:
        key = _cite_key(p)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = f"{key}{chr(ord('a') + seen[key] - 1)}"
        out.append(_bibtex_one(p, key))
    return "\n\n".join(out) + "\n"


def to_csv(papers: list[dict]) -> str:
    buf = io.StringIO()
    cols = ["role", "title", "authors", "venue", "venue_type", "year", "citations",
            "headline_metric", "datasets", "code_available", "doi", "url"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for p in papers:
        hl = p.get("headline") or {}
        w.writerow({
            "role": p.get("role", ""),
            "title": p.get("title", ""),
            "authors": "; ".join(p.get("authors") or []),
            "venue": p.get("venue", ""),
            "venue_type": p.get("venue_type", ""),
            "year": p.get("year", ""),
            "citations": p.get("citations", ""),
            "headline_metric": (f"{hl.get('name')} {hl.get('value')}%" if hl else ""),
            "datasets": "; ".join(p.get("datasets") or []),
            "code_available": "yes" if p.get("code") else "",
            "doi": p.get("doi", "") or "",
            "url": p.get("url", "") or "",
        })
    return buf.getvalue()
