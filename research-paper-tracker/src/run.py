"""Weekly entry point.

Usage:
    python -m src.run                 # rolling last `lookback_days`
    python -m src.run --lookback 30   # override the window (days)
    python -m src.run --dry-run       # fetch + rank, but don't write DB/CSV
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from .config import load_config
from . import store, match, export, status
from .sources import openalex, arxiv, crossref


def gather_feed(cfg, feed: dict, date_from: str, date_to: str) -> list[dict]:
    src, mode = feed["source"], feed["mode"]
    if src == "openalex":
        if mode == "journals":
            return openalex.fetch_journals(cfg, feed["areas"], date_from, date_to)
        if mode == "keyword":
            return openalex.fetch_keyword(cfg, feed["query"], date_from, date_to)
    if src == "arxiv":
        if mode == "categories":
            return arxiv.fetch_categories(cfg, feed["cats"], date_from)
        if mode == "cross":
            return arxiv.fetch_cross(cfg, feed["all_of"], date_from)
        if mode == "keyword":
            return arxiv.fetch_keyword(cfg, feed["query"], date_from)
    if src == "crossref":
        if mode == "keyword":
            return crossref.fetch_keyword(cfg, feed["query"], date_from, date_to)
    raise ValueError(f"unknown feed: {feed}")


def _better(a: dict, b: dict) -> bool:
    """Prefer the richer representation when the same paper arrives via two feeds."""
    ka = (a.get("match_score", 0), a.get("relevance", 0.0), -a.get("tier", 9))
    kb = (b.get("match_score", 0), b.get("relevance", 0.0), -b.get("tier", 9))
    return ka > kb


def _window_start(conn, settings: dict, today: date, lookback: int | None) -> date:
    """Where the lookback window begins.

    - explicit --lookback: exactly that many days.
    - otherwise auto: from the last refresh minus a lag margin (so a late refresh
      never misses papers), or `lookback_days` on the first ever run. Capped at
      `max_lookback_days` so it can never balloon.
    """
    if lookback is not None:
        return today - timedelta(days=lookback)
    last = store.last_refresh_date(conn)
    if last is not None:
        start = last - timedelta(days=int(settings.get("lag_margin_days", 2)))
    else:
        # First ever refresh: if a publication floor is set, do a comprehensive
        # pull from it (uncapped) rather than the short rolling window.
        floor_date = settings.get("min_publication_date")
        if floor_date:
            return date.fromisoformat(str(floor_date))
        start = today - timedelta(days=int(settings["lookback_days"]))
    cap = today - timedelta(days=int(settings.get("max_lookback_days", 60)))
    return max(start, cap)


def run(lookback: int | None = None, dry_run: bool = False, on_progress=None,
        source: str | None = None) -> dict:
    """Perform a refresh. Returns a structured summary (also used by the GUI).

    on_progress(done, total, label) is called before each category so the GUI can
    drive a determinate progress bar. `source` ("openalex"/"crossref"/None|"all")
    restricts which feeds run.
    """
    cfg = load_config()
    conn = store.connect(cfg.path("db_path"))
    output_dir = cfg.path("output_dir")

    today = date.today()
    date_to = today.isoformat()
    date_from = _window_start(conn, cfg.settings, today, lookback).isoformat()
    run_date = today.isoformat()
    mode = "manual window" if lookback is not None else "auto (since last refresh)"

    print(f"\nResearch paper tracker  |  window {date_from} -> {date_to}  [{mode}]"
          f"{'  (dry run)' if dry_run else ''}\n")

    per_category: list[dict] = []
    errors = 0
    total_cats = len(cfg.categories)
    for idx, category in enumerate(cfg.categories):
        key, label = category["key"], category["label"]
        star = " *" if category.get("important") else ""
        if on_progress:
            on_progress(idx, total_cats, f"Fetching {label}…")
        groups, excludes = match.compile_category(category)
        sieve_terms = [match._compile_term(t) for t in category.get("sieve_terms", [])]

        candidates: dict[str, dict] = {}
        for feed in category["feeds"]:
            if source and source != "all" and feed.get("source") != source:
                continue
            try:
                papers = gather_feed(cfg, feed, date_from, date_to)
            except Exception as e:  # keep going if one feed hiccups
                errors += 1
                print(f"  ! {label}: feed {feed.get('source')}/{feed.get('mode')} failed: {e}")
                papers = []
            for p in papers:
                score = match.evaluate(p, groups, excludes, category.get("min_hits"))
                if score is None:
                    continue
                # Broad-venue papers must clear the IT vocabulary sieve.
                if sieve_terms and p.get("_sieve") and not match.any_match(p, sieve_terms):
                    continue
                p["match_score"] = score
                cur = candidates.get(p["uid"])
                if cur is None or _better(p, cur):
                    candidates[p["uid"]] = p

        seen = store.existing_uids_for_category(conn, key)
        fresh = [p for p in candidates.values() if p["uid"] not in seen]
        max_per_venue = category.get("max_per_venue", cfg.settings.get("max_per_venue"))
        selected = match.rank(
            fresh, category.get("rank_by", "relevance"), cfg.top_n(category), max_per_venue
        )
        for p in selected:
            p["matched_terms"] = "; ".join(match.matched_terms(p, category))

        if not dry_run:
            # Mark every fresh candidate seen (incl. overflow beyond top-N) so
            # nothing re-surfaces on a later run.
            store.mark_seen(conn, key, [p["uid"] for p in fresh], run_date)
            store.persist_selection(conn, key, selected, run_date)
            export.export_category(output_dir, key, selected, run_date)

        per_category.append({
            "key": key, "label": label, "important": bool(category.get("important")),
            "candidates": len(candidates), "new": len(fresh), "surfaced": len(selected),
        })
        print(f"  {label + star:<32} candidates={len(candidates):>4}  "
              f"new={len(fresh):>4}  surfaced={len(selected):>3}")

    if on_progress:
        on_progress(total_cats, total_cats, "Finalizing…")

    total_new = sum(c["surfaced"] for c in per_category)
    # Record the run unless it was a total wipeout (no papers AND errors) — that
    # way a Crossref-only success still counts even while OpenAlex is rate-limited,
    # but a fully-failed rate-limited run doesn't fake "up to date".
    total_failure = errors > 0 and total_new == 0
    if not dry_run and not total_failure:
        store.record_run(conn, datetime.now().isoformat(timespec="seconds"),
                         run_date, date_from, date_to, total_new, errors)

    print(f"\nDone. {total_new} papers surfaced across {len(per_category)} categories"
          f"{f', {errors} feed error(s)' if errors else ''}.")
    st = status.refresh_status(conn, cfg.settings)
    print(st["message"])
    if not dry_run:
        print(f"CSVs: {output_dir}")
    conn.close()

    return {
        "run_date": run_date, "window_from": date_from, "window_to": date_to,
        "surfaced": total_new, "errors": errors, "dry_run": dry_run,
        "categories": per_category, "status": st,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Weekly research paper tracker")
    ap.add_argument("--lookback", type=int, default=None, help="window size in days")
    ap.add_argument("--dry-run", action="store_true", help="don't write DB/CSV")
    ap.add_argument("--source", default=None, help="openalex | crossref (default: all)")
    ap.add_argument("--status", action="store_true", help="show refresh status and exit")
    args = ap.parse_args()
    if args.status:
        status.main()
        return
    run(lookback=args.lookback, dry_run=args.dry_run, source=args.source)


if __name__ == "__main__":
    main()
