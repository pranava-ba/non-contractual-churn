"""Weekly entry point.

Usage:
    python -m src.run                 # rolling last `lookback_days`
    python -m src.run --lookback 30   # override the window (days)
    python -m src.run --dry-run       # fetch + rank, but don't write DB/CSV
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta

from .config import load_config
from . import store, match, export, status
from .sources import openalex, arxiv, crossref, semanticscholar

# module -> its request-count counter, for the end-of-run budget report.
_SOURCE_MODULES = {"openalex": openalex, "arxiv": arxiv, "crossref": crossref}


def _feed_cache_key(feed: dict, date_from: str, date_to: str) -> str:
    """Two categories often search near-identical term space (e.g. every
    non-contractual-churn category touches churn/CLV/BTYD vocabulary); when their
    `feeds` entries resolve to the literal same request, fetch it once per run and
    reuse it rather than re-paging the same API call under each category."""
    return json.dumps([feed, date_from, date_to], sort_keys=True)


def gather_feed(cfg, feed: dict, date_from: str, date_to: str) -> list[dict]:
    src, mode = feed["source"], feed["mode"]
    if src == "openalex":
        if mode == "journals":
            return openalex.fetch_journals(cfg, feed["areas"], date_from, date_to)
        if mode == "keyword":
            return openalex.fetch_keyword(cfg, feed["query"], date_from, date_to)
    if src == "arxiv":
        if mode == "categories":
            return arxiv.fetch_categories(cfg, feed["cats"], date_from, date_to)
        if mode == "cross":
            return arxiv.fetch_cross(cfg, feed["all_of"], date_from, date_to)
        if mode == "keyword":
            return arxiv.fetch_keyword(cfg, feed["query"], date_from, date_to)
    if src == "crossref":
        if mode == "keyword":
            return crossref.fetch_keyword(cfg, feed["query"], date_from, date_to)
    raise ValueError(f"unknown feed: {feed}")


def _better(a: dict, b: dict) -> bool:
    """Which representation to use as the base when the same paper arrives via two
    feeds within one category."""
    ka = (a.get("match_score", 0), a.get("relevance", 0.0), -a.get("tier", 9))
    kb = (b.get("match_score", 0), b.get("relevance", 0.0), -b.get("tier", 9))
    return ka > kb


_MERGEABLE_FIELDS = ("abstract", "oa_url", "doi", "arxiv_id", "venue", "authors")


def _merge(a: dict, b: dict) -> dict:
    """Combine two feeds' records of the same paper: start from the richer one
    (by _better), but backfill any field it's missing from the other, instead of
    discarding the loser's data outright (e.g. an abstract Crossref had and
    OpenAlex didn't)."""
    winner, loser = (a, b) if _better(a, b) else (b, a)
    merged = dict(winner)
    for field in _MERGEABLE_FIELDS:
        if not (merged.get(field) or None):
            if loser.get(field):
                merged[field] = loser[field]
    return merged


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

    # Reset per-run API call counters (module-level, so a long-lived GUI process
    # doesn't accumulate across refreshes).
    for mod in _SOURCE_MODULES.values():
        mod.CALLS_MADE = 0
    feed_cache: dict[str, list[dict]] = {}

    per_category: list[dict] = []
    errors = 0
    total_cats = len(cfg.categories)
    for idx, category in enumerate(cfg.categories):
        key, label = category["key"], category["label"]
        star = " *" if category.get("important") else ""
        if on_progress:
            on_progress(idx, total_cats, f"Fetching {label}…")
        try:
            groups, excludes = match.compile_category(category)
            sieve_terms = [match._compile_term(t) for t in category.get("sieve_terms", [])]

            raw: list[dict] = []
            for feed in category["feeds"]:
                if source and source != "all" and feed.get("source") != source:
                    continue
                cache_key = _feed_cache_key(feed, date_from, date_to)
                if cache_key in feed_cache:
                    raw.extend(feed_cache[cache_key])
                    continue
                try:
                    papers = gather_feed(cfg, feed, date_from, date_to)
                except Exception as e:  # keep going if one feed hiccups
                    errors += 1
                    print(f"  ! {label}: feed {feed.get('source')}/{feed.get('mode')} failed: {e}")
                    papers = []
                feed_cache[cache_key] = papers
                raw.extend(papers)

            # Backfill missing abstracts BEFORE matching -- a title-only record
            # weakens match.evaluate's scoring (and can silently drop a relevant
            # paper) purely because a publisher didn't hand Crossref an abstract.
            semanticscholar.backfill_abstracts(raw, cfg)

            # Hard floor: previously only shaped the FIRST run's window (see
            # _window_start) -- a later run had nothing stopping a paper with a
            # stale/corrected publication_date from slipping in. Enforce it on
            # every run, not just the first.
            floor = cfg.settings.get("min_publication_date")
            if floor:
                raw = [p for p in raw if not p.get("publication_date")
                       or p["publication_date"] >= floor]

            candidates: dict[str, dict] = {}
            for p in raw:
                score = match.evaluate(p, groups, excludes, category.get("min_hits"))
                if score is None:
                    continue
                # Broad-venue papers must clear the IT vocabulary sieve.
                if sieve_terms and p.get("_sieve") and not match.any_match(p, sieve_terms):
                    continue
                p["match_score"] = score
                cur = candidates.get(p["uid"])
                candidates[p["uid"]] = _merge(p, cur) if cur is not None else p

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
        except Exception as e:
            # A config/logic error in ONE category (bad regex, missing key, ...)
            # used to abort the whole run, including record_run() at the end --
            # every earlier category's writes stayed committed, but the run would
            # never register as "done", so the next refresh's window calculation
            # silently re-fetched the same range. Isolate it like a feed error.
            errors += 1
            print(f"  ! {label}: category failed: {e}")
            per_category.append({
                "key": key, "label": label, "important": bool(category.get("important")),
                "candidates": 0, "new": 0, "surfaced": 0, "error": str(e),
            })

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

    call_counts = {name: mod.CALLS_MADE for name, mod in _SOURCE_MODULES.items() if mod.CALLS_MADE}
    budget = int(cfg.settings.get("openalex_daily_budget", 0) or 0)
    warn_frac = float(cfg.settings.get("openalex_budget_warn_frac", 0.5) or 0.5)
    if not dry_run:
        for src_name, n in call_counts.items():
            store.record_api_calls(conn, run_date, src_name, n)
    if budget and call_counts.get("openalex"):
        used_today = store.api_calls_today(conn, run_date, "openalex")
        if used_today >= budget * warn_frac:
            print(f"  ! OpenAlex: {used_today}/{budget} of today's estimated shared "
                  f"daily budget used — consider spacing refreshes out if 429s appear.")

    print(f"\nDone. {total_new} papers surfaced across {len(per_category)} categories"
          f"{f', {errors} feed error(s)' if errors else ''}.")
    if call_counts:
        print("  API calls this run: " + ", ".join(f"{k}={v}" for k, v in call_counts.items()))
    st = status.refresh_status(conn, cfg.settings)
    print(st["message"])
    if not dry_run:
        print(f"CSVs: {output_dir}")
    conn.close()

    return {
        "run_date": run_date, "window_from": date_from, "window_to": date_to,
        "surfaced": total_new, "errors": errors, "dry_run": dry_run,
        "categories": per_category, "status": st, "api_calls": call_counts,
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
