"""Fetch a paper's full-text PDF.

Order of preference (legal sources first):
  1. arXiv  — open access, direct.
  2. OpenAlex open-access / Unpaywall PDF link, when the paper has one.
  3. Sci-Hub, by DOI, via the `scidownl` engine (auto-discovers current mirrors).
     A last-resort fallback for paywalled papers; access may be legally restricted
     where you live, and many ISPs block Sci-Hub outright — set a `proxy` in
     settings.yaml (VPN / SOCKS / HTTP proxy) to route around such blocks.
"""
from __future__ import annotations

import re
from pathlib import Path

import requests

_UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}


def _safe_name(s: str, maxlen: int = 120) -> str:
    s = re.sub(r"[^\w\- ]+", "", s or "").strip().replace(" ", "_")
    return s[:maxlen] or "paper"


def proxies_from(proxy: str | None) -> dict | None:
    return {"http": proxy, "https": proxy} if proxy else None


def arxiv_pdf_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}"


def _is_pdf(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5).startswith(b"%PDF")
    except OSError:
        return False


def _download(url: str, dest: Path, session: requests.Session, timeout: int = 60) -> Path:
    r = session.get(url, headers=_UA, timeout=timeout, stream=True)
    r.raise_for_status()
    ct = r.headers.get("Content-Type", "").lower()
    it = r.iter_content(8192)
    first = next(it, b"")
    # Reject HTML landing/error pages so the caller can fall through to the next source.
    if b"%PDF" not in first[:1024] and "pdf" not in ct:
        raise RuntimeError(f"not a PDF (content-type: {ct or 'unknown'})")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(first)
        for chunk in it:
            if chunk:
                f.write(chunk)
    if dest.stat().st_size < 1024:
        dest.unlink(missing_ok=True)
        raise RuntimeError("downloaded file was empty")
    return dest


def _scihub(doi: str, dest: Path, proxies: dict | None) -> Path:
    try:
        from scidownl import scihub_download
    except ImportError:
        raise RuntimeError("Sci-Hub support needs the 'scidownl' package (pip install scidownl).")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    import logging
    prev = logging.root.manager.disable
    logging.disable(logging.CRITICAL)  # silence scidownl's very chatty logging
    try:
        # scihub_url=None lets scidownl auto-discover a currently-working mirror.
        scihub_download(doi, paper_type="doi", out=str(dest), proxies=proxies or {})
    except (Exception, SystemExit):  # scidownl raises SystemExit on total failure
        pass
    finally:
        logging.disable(prev)
    if dest.exists() and dest.stat().st_size > 1024 and _is_pdf(dest):
        return dest
    raise RuntimeError(
        "Sci-Hub unreachable or the paper isn't on Sci-Hub. Many ISPs (e.g. in India) block "
        "Sci-Hub - set a proxy in settings.yaml (a VPN or SOCKS/HTTP proxy) to route around it."
    )


def download_paper(paper: dict, out_dir, mirrors: list[str] | None = None,
                   proxy: str | None = None) -> tuple[Path, str]:
    """paper: dict with arxiv_id / doi / oa_url / title. Returns (path, source_label)."""
    proxies = proxies_from(proxy)
    session = requests.Session()
    if proxies:
        session.proxies.update(proxies)
    out_dir = Path(out_dir)
    dest = out_dir / f"{_safe_name(paper.get('title') or paper.get('doi') or paper.get('arxiv_id'))}.pdf"

    if paper.get("arxiv_id"):
        return _download(arxiv_pdf_url(paper["arxiv_id"]), dest, session), "arXiv"

    if paper.get("oa_url"):
        try:
            return _download(paper["oa_url"], dest, session), "open access"
        except (requests.RequestException, RuntimeError):
            pass

    if paper.get("doi") and mirrors:  # non-empty scihub_mirrors = Sci-Hub enabled
        return _scihub(paper["doi"], dest, proxies), "Sci-Hub"

    raise RuntimeError("No PDF found (no arXiv id, open-access link, or Sci-Hub result).")
