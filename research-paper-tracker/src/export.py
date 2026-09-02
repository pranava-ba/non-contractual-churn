"""Append surfaced papers to a master CSV per category."""
from __future__ import annotations

import csv
from pathlib import Path

from .status import fmt_date

FIELDS = [
    "date_added", "rank", "title", "doi", "arxiv_id", "authors",
    "venue", "publication_date", "source", "matched_terms", "match_score", "relevance", "url",
]


def export_category(output_dir: Path, category_key: str, papers: list[dict], run_date: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{category_key}.csv"
    new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for rank, p in enumerate(papers, start=1):
            writer.writerow({
                "date_added": fmt_date(run_date),
                "rank": rank,
                "title": p.get("title", ""),
                "doi": p.get("doi") or "",
                "arxiv_id": p.get("arxiv_id") or "",
                "authors": "; ".join(p.get("authors", [])),
                "venue": p.get("venue", ""),
                "publication_date": fmt_date(p.get("publication_date", "")),
                "source": p.get("source", ""),
                "matched_terms": p.get("matched_terms", ""),
                "match_score": p.get("match_score", 0),
                "relevance": round(p.get("relevance", 0.0), 2),
                "url": p.get("url", ""),
            })
    return path
