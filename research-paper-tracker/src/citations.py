"""Cross-reference tracked papers against a manuscript's .bib file to auto-detect
"used" (cited) status for the Coverage page.

No new dependency: a small brace-aware field extractor, not a full BibTeX grammar,
is enough for the two hand-maintained .bib files this project has (refs_phase2.bib,
refs_gear2.bib) -- they're simple `@type{key, field = {value}, ...}` entries with at
most one level of nested braces (LaTeX escapes like `{\"a}`, protected acronyms like
`{Pareto/NBD}`).

Matching, in order of confidence:
  1. DOI (normalized, case-insensitive)      -- the reliable case
  2. arXiv id (from a `note = {arXiv:...}` field, common for preprint-only entries)
  3. normalized title (fallback for entries that predate a DOI-verification pass,
     or a tracked paper whose own DOI/arXiv id didn't resolve)
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_FIELD_RE = re.compile(r"([A-Za-z][\w-]*)\s*=\s*", re.IGNORECASE)
_ENTRY_START_RE = re.compile(r"^@[A-Za-z]+\{", re.MULTILINE)
_ARXIV_RE = re.compile(r"arxiv[:\s]*([0-9]{4}\.[0-9]{4,5})", re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None


def normalize_title(title: str | None) -> str | None:
    if not title:
        return None
    t = title.lower()
    t = re.sub(r"[{}\\]", "", t)          # drop LaTeX braces/backslashes
    t = re.sub(r"``|''", '"', t)
    t = _NON_ALNUM_RE.sub(" ", t).strip()
    return t or None


def _braced_value(text: str, start: int) -> tuple[str, int]:
    """text[start] must be '{'. Returns (inner_text, index_just_after_closing_brace)."""
    depth = 0
    i = start
    out_start = start + 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[out_start:i], i + 1
    return text[out_start:], len(text)  # unbalanced; be lenient


def _parse_entry(entry_text: str) -> dict:
    """entry_text starts right after the opening '{' of '@type{key,'."""
    comma = entry_text.find(",")
    key = entry_text[:comma].strip() if comma != -1 else entry_text.strip()
    fields: dict[str, str] = {}
    for m in _FIELD_RE.finditer(entry_text):
        j = m.end()
        while j < len(entry_text) and entry_text[j].isspace():
            j += 1
        if j >= len(entry_text) or entry_text[j] != "{":
            continue  # quoted-with-"" or bare numeric fields -- not used by these files
        value, _ = _braced_value(entry_text, j)
        fields[m.group(1).lower()] = value
    return {"key": key, **fields}


def parse_bib(path: Path) -> list[dict]:
    """Every entry in a .bib file as {key, title, doi, note, author, ...}."""
    text = path.read_text(encoding="utf-8")
    starts = [m.end() for m in _ENTRY_START_RE.finditer(text)]
    entries = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(text)
        # walk back from the next '@...{' to this entry's own closing brace
        chunk = text[start:end]
        last_close = chunk.rfind("}\n")
        if last_close != -1:
            chunk = chunk[:last_close]
        entries.append(_parse_entry(chunk))
    return entries


class BibIndex:
    """DOI / arXiv-id / normalized-title lookup over one .bib file's entries."""

    def __init__(self, entries: list[dict]):
        self.by_doi: dict[str, str] = {}
        self.by_arxiv: dict[str, str] = {}
        self.by_title: dict[str, str] = {}
        for e in entries:
            key = e["key"]
            doi = normalize_doi(e.get("doi"))
            if doi:
                self.by_doi[doi] = key
            arxiv_src = " ".join(v for k, v in e.items() if k in ("note", "journal", "eprint"))
            am = _ARXIV_RE.search(arxiv_src)
            if am:
                self.by_arxiv[am.group(1)] = key
            title = normalize_title(e.get("title"))
            if title:
                self.by_title[title] = key

    def match(self, doi: str | None, arxiv_id: str | None, title: str | None) -> str | None:
        """The bib key this paper is cited under, or None."""
        d = normalize_doi(doi)
        if d and d in self.by_doi:
            return self.by_doi[d]
        if arxiv_id and arxiv_id in self.by_arxiv:
            return self.by_arxiv[arxiv_id]
        t = normalize_title(title)
        if t and t in self.by_title:
            return self.by_title[t]
        return None


@lru_cache(maxsize=8)
def _load_index(path_str: str, mtime: float) -> BibIndex:
    return BibIndex(parse_bib(Path(path_str)))


def load_index(path: Path | None) -> BibIndex | None:
    """Cached by (path, mtime) so re-parsing only happens when the .bib actually
    changes -- cheap enough to call once per GUI snapshot regardless."""
    if not path or not path.exists():
        return None
    return _load_index(str(path), path.stat().st_mtime)
