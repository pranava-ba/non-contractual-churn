"""SQLite persistence. This DB is the source of truth; CSV (and the future GUI)
are read-layers over it.

Tables:
  papers            one row per unique paper (dedup by uid = doi:.. or arxiv:..)
  paper_categories  one row per (paper, category) the paper was surfaced under.
                    A paper stays here forever, so re-runs never re-report it.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    uid              TEXT PRIMARY KEY,
    doi              TEXT,
    arxiv_id         TEXT,
    oa_url           TEXT,
    title            TEXT,
    abstract         TEXT,
    authors          TEXT,
    venue            TEXT,
    publication_date TEXT,
    source           TEXT,
    url              TEXT,
    first_seen       TEXT
);

-- Per-paper user state (read / starred / hidden / tags), keyed by uid so it
-- persists across runs.
CREATE TABLE IF NOT EXISTS paper_state (
    uid     TEXT PRIMARY KEY,
    read    INTEGER DEFAULT 0,
    starred INTEGER DEFAULT 0,
    hidden  INTEGER DEFAULT 0,
    tags    TEXT
);

CREATE TABLE IF NOT EXISTS paper_categories (
    uid           TEXT,
    category      TEXT,
    date_added    TEXT,
    run_date      TEXT,
    rank          INTEGER,
    match_score   INTEGER,
    relevance     REAL,
    matched_terms TEXT,
    PRIMARY KEY (uid, category),
    FOREIGN KEY (uid) REFERENCES papers(uid)
);

-- Every candidate that passed a category's filter, whether or not it made the
-- top-N. This is what dedup checks, so a paper is never re-surfaced and the
-- overflow beyond top-N (dropped by the cap) does not resurface next run.
CREATE TABLE IF NOT EXISTS seen (
    uid      TEXT,
    category TEXT,
    run_date TEXT,
    PRIMARY KEY (uid, category)
);

-- One row per refresh. Drives the "last refreshed / due / overdue" status.
CREATE TABLE IF NOT EXISTS runs (
    run_at      TEXT PRIMARY KEY,   -- ISO timestamp (unique per run)
    run_date    TEXT,               -- YYYY-MM-DD
    window_from TEXT,
    window_to   TEXT,
    surfaced    INTEGER,
    errors      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_pc_category ON paper_categories(category);
CREATE INDEX IF NOT EXISTS idx_pc_run      ON paper_categories(run_date);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # timeout avoids "database is locked" if the GUI reads while a refresh writes.
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # migrate older DBs that predate newer columns
    for table, col, decl in [
        ("paper_categories", "matched_terms", "TEXT"),
        ("papers", "oa_url", "TEXT"),
        ("paper_state", "hidden", "INTEGER DEFAULT 0"),
        ("paper_state", "tags", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
    return conn


def existing_uids_for_category(conn: sqlite3.Connection, category: str) -> set[str]:
    rows = conn.execute(
        "SELECT uid FROM seen WHERE category = ?", (category,)
    ).fetchall()
    return {r["uid"] for r in rows}


def mark_seen(conn: sqlite3.Connection, category: str, uids: list[str], run_date: str) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO seen (uid, category, run_date) VALUES (?, ?, ?)",
        [(u, category, run_date) for u in uids],
    )
    conn.commit()


def _upsert_paper(conn: sqlite3.Connection, p: dict, run_date: str) -> None:
    conn.execute(
        """
        INSERT INTO papers (uid, doi, arxiv_id, oa_url, title, abstract, authors, venue,
                            publication_date, source, url, first_seen)
        VALUES (:uid, :doi, :arxiv_id, :oa_url, :title, :abstract, :authors, :venue,
                :publication_date, :source, :url, :first_seen)
        ON CONFLICT(uid) DO UPDATE SET
            title=excluded.title,
            abstract=excluded.abstract,
            authors=excluded.authors,
            venue=excluded.venue,
            publication_date=excluded.publication_date,
            oa_url=excluded.oa_url,
            url=excluded.url
        """,
        {
            "uid": p["uid"],
            "doi": p.get("doi"),
            "arxiv_id": p.get("arxiv_id"),
            "oa_url": p.get("oa_url"),
            "title": p.get("title", ""),
            "abstract": p.get("abstract", ""),
            "authors": "; ".join(p.get("authors", [])),
            "venue": p.get("venue", ""),
            "publication_date": p.get("publication_date", ""),
            "source": p.get("source", ""),
            "url": p.get("url", ""),
            "first_seen": run_date,
        },
    )


def persist_selection(
    conn: sqlite3.Connection, category: str, papers: list[dict], run_date: str
) -> None:
    """Store the ranked top-N papers for a category. `rank` reflects list order."""
    for rank, p in enumerate(papers, start=1):
        _upsert_paper(conn, p, run_date)
        conn.execute(
            """
            INSERT OR IGNORE INTO paper_categories
                (uid, category, date_added, run_date, rank, match_score, relevance, matched_terms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["uid"],
                category,
                run_date,
                run_date,
                rank,
                p.get("match_score", 0),
                p.get("relevance", 0.0),
                p.get("matched_terms", ""),
            ),
        )
    conn.commit()


# --- refresh tracking -------------------------------------------------------

def record_run(conn, run_at, run_date, window_from, window_to, surfaced, errors) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs (run_at, run_date, window_from, window_to, surfaced, errors)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (run_at, run_date, window_from, window_to, surfaced, errors),
    )
    conn.commit()


def last_run(conn) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs ORDER BY run_at DESC LIMIT 1").fetchone()


def last_refresh_date(conn) -> date | None:
    row = last_run(conn)
    return date.fromisoformat(row["run_date"]) if row else None


# --- read layer (used by the GUI) ------------------------------------------

def list_run_dates(conn) -> list[dict]:
    """Distinct refresh weeks, newest first, with how many papers each surfaced."""
    rows = conn.execute(
        "SELECT run_date, COUNT(*) AS n FROM paper_categories"
        " GROUP BY run_date ORDER BY run_date DESC"
    ).fetchall()
    return [{"run_date": r["run_date"], "count": r["n"]} for r in rows]


def papers_for_category(conn, category: str, run_date: str | None = None) -> list[sqlite3.Row]:
    """Surfaced papers for a category, optionally restricted to one refresh week."""
    sql = (
        "SELECT p.*, pc.run_date, pc.rank, pc.match_score, pc.relevance, pc.matched_terms,"
        " COALESCE(ps.read,0) AS read, COALESCE(ps.starred,0) AS starred,"
        " COALESCE(ps.hidden,0) AS hidden, COALESCE(ps.tags,'') AS tags"
        " FROM paper_categories pc JOIN papers p ON p.uid = pc.uid"
        " LEFT JOIN paper_state ps ON ps.uid = p.uid"
        " WHERE pc.category = ?"
    )
    args: list = [category]
    if run_date:
        sql += " AND pc.run_date = ?"
        args.append(run_date)
    sql += " ORDER BY pc.run_date DESC, pc.rank ASC"
    return conn.execute(sql, args).fetchall()


def get_paper(conn, uid: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM papers WHERE uid = ?", (uid,)).fetchone()


def set_state(conn, uid: str, field: str, value: int) -> None:
    """Set a per-paper flag ('read' / 'starred' / 'hidden')."""
    if field not in ("read", "starred", "hidden"):
        raise ValueError(field)
    conn.execute("INSERT OR IGNORE INTO paper_state (uid) VALUES (?)", (uid,))
    conn.execute(f"UPDATE paper_state SET {field} = ? WHERE uid = ?", (int(bool(value)), uid))
    conn.commit()


def set_tags(conn, uid: str, tags: str) -> None:
    conn.execute("INSERT OR IGNORE INTO paper_state (uid) VALUES (?)", (uid,))
    conn.execute("UPDATE paper_state SET tags = ? WHERE uid = ?", (tags or "", uid))
    conn.commit()
