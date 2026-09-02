"""Curate the tracked corpus for the non-contractual-BTYD paper.

Three jobs, all driven off the SQLite DB (the source of truth):

  1. snapshot  -> data/out/all_papers.csv     a regenerable dump of every paper +
                                              its categories + read/star/hidden state.
  2. classify  -> data/out/curation_review.csv  a transparent keep/remove decision
                                              (with reason) for every paper.
  3. funnel    -> data/out/funnel_counts.csv   PRISMA-style counts per category and
                                              overall (identified -> excluded -> kept),
                                              the numbers for the paper's figure.

By default it is a DRY RUN: it writes the review + snapshot + funnel and changes
nothing. Pass --apply to actually set paper_state.hidden=1 for the removals (after a
timestamped DB backup) and rebuild data/out/removed_papers.csv.

    python tools/curate.py            # review only (safe)
    python tools/curate.py --apply    # apply removals (reversible: hidden flag + backup)

Removal reasons (paper-level, evaluated on title+abstract+venue):
  non_english        title reads as Indonesian / Turkish / Portuguese / other non-EN
  offtopic           keyword false positive (remote sensing, quantum, credit scoring, ...)
  contractual_churn  telecom / subscription / OTT / SaaS churn with no non-contractual signal
  rfm_segmentation   an RFM + clustering *segmentation* exercise, not a BTYD/ML forecasting model

Everything else is kept. The rules are deliberately conservative: any paper carrying a
BTYD model name or a real ML-forecasting signal is kept even if it also mentions
clustering, so genuinely relevant work is never dropped by an incidental word.

Manual review is authoritative: a paper you have STARRED in the GUI is treated as a
persistent "keep" and is never auto-hidden, so re-running --apply can never undo a
manual check.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "tracker.db"
OUT = ROOT / "data" / "out"

# --- term sets --------------------------------------------------------------
BTYD = ["btyd", "buy till you die", "buy-till-you-die", "pareto/nbd", "pareto nbd",
        "bg/nbd", "mbg/nbd", "bg/bb", "latent attrition", "gamma-gamma",
        "conditional expected transaction", "cnbd"]
ML_SIGNAL = ["gradient boosting", "xgboost", "lightgbm", "hurdle", "zero-inflated",
             "zero inflated", "deep learning", "neural network", "survival",
             "hazard", "random forest", "quantile", "conformal", "lstm", "gru",
             "transformer", "gradient-boosting", "markov", "bayesian", "ensemble",
             "stacking", "stacked", "probabilistic", "meta-learning", "meta learning",
             "embedding", "variational", "reinforcement"]
NONCONTRACTUAL = ["non-contractual", "noncontractual", "non contractual",
                  "non-subscription"] + BTYD
CLUSTERING = ["k-means", "kmeans", "k means", "dbscan", "fuzzy c-means", "c-means",
              "clustering", "agglomerative", "hierarchical cluster"]
# An RFM/segmentation *exercise* (as opposed to a forecasting model). Combined with
# the CLUSTERING terms, this catches the dominant noise class. Papers carrying a BTYD
# name or a real ML-forecasting method (ML_SIGNAL above) are protected and kept.
SEGMENTATION = ["segmentation", "segmentasi", "customer segment", "segment customers",
                "segmenting", "customer profiling", "customer profile", "rfm score",
                "rfm analysis", "rfm model", "rfm method"]
OFFTOPIC = ["remote sensing", "road extraction", "u-net", "unet", "mamba",
            "quantum", "self-orthogonal", "lcd code", "quantum code",
            "credit scoring", "credit score", "electricity customer demand",
            "image segmentation", "convolutional neural network for customer segment"]
CONTRACTUAL = ["telecom", "telecommunication", "subscription-based", "subscription based",
               "ott platform", "over-the-top", "saas", "internet service provider",
               "mobile telecommunication"]
# Indonesian / Malay / Turkish / Portuguese function words -> non-English title.
NON_EN = ["analisis", "segmentasi", "pelanggan", "menggunakan", "berdasarkan",
          "dengan", " dan ", "penerapan", "metode", "loyalitas", "kepuasan",
          "perusahaan", "müşteri", "için", "analizi", "clientes", "modelos",
          "não", "fidelização", "retenção", "segmentación", "método"]


def _has(text: str, terms) -> bool:
    return any(t in text for t in terms)


def classify(title: str, abstract: str, venue: str) -> tuple[str, str]:
    """Return (decision, reason). decision in {'keep','remove'}."""
    t = " " + (title or "").lower() + " "
    full = t + " " + (abstract or "").lower() + " " + (venue or "").lower()

    # 1. non-English (title is the reliable signal)
    if _has(t, NON_EN):
        return "remove", "non_english"
    # 2. hard off-topic keyword false positives
    if _has(full, OFFTOPIC):
        return "remove", "offtopic"
    # BTYD / real ML-forecasting papers are always kept from here on.
    protected = _has(full, BTYD) or _has(full, ML_SIGNAL)
    # 3. contractual-setting churn: the paper is *about* telecom/subscription/OTT/SaaS
    #    (term in the TITLE), not merely benchmarking on such data. Title-only keeps
    #    general methodology papers that happen to test on a telecom dataset.
    if _has(t, CONTRACTUAL) and not _has(full, NONCONTRACTUAL):
        return "remove", "contractual_churn"
    # 4. RFM / clustering segmentation exercise (the dominant noise), unless it
    #    carries a BTYD name or a real ML-forecasting method. Trigger on a clustering
    #    algorithm anywhere, or a segmentation cue in the title.
    if not protected and (_has(full, CLUSTERING) or _has(t, SEGMENTATION)):
        return "remove", "rfm_segmentation"
    return "keep", ""


def rows(conn):
    q = """SELECT p.uid, p.title, p.abstract, p.authors, p.venue, p.publication_date,
                  p.source, p.doi, p.arxiv_id, p.url, p.first_seen,
                  COALESCE(ps.hidden,0) hidden, COALESCE(ps.read,0) read,
                  COALESCE(ps.starred,0) starred,
                  (SELECT GROUP_CONCAT(pc.category, '|') FROM paper_categories pc
                    WHERE pc.uid = p.uid) cats
           FROM papers p LEFT JOIN paper_state ps ON ps.uid = p.uid"""
    return conn.execute(q).fetchall()


def snapshot(rs):
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["uid", "cats", "title", "authors", "venue", "publication_date", "source",
            "doi", "arxiv_id", "url", "first_seen", "hidden", "read", "starred"]
    with open(OUT / "all_papers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rs:
            w.writerow([r[c] for c in cols])
    print(f"snapshot -> {OUT/'all_papers.csv'}  ({len(rs)} papers)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="apply removals (default: dry run)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    rs = rows(conn)
    snapshot(rs)

    # classify. Precedence: a prior removal stays removed; a manual keep (the user
    # starred it) is authoritative and is NEVER auto-hidden; otherwise auto-classify.
    review = []
    for r in rs:
        if r["hidden"]:
            decision, reason = "remove", "already_hidden"
        elif r["starred"]:
            decision, reason = "keep", "user_kept"     # persistent manual check — protect it
        else:
            decision, reason = classify(r["title"], r["abstract"], r["venue"])
        review.append((r["uid"], r["cats"] or "", decision, reason,
                       r["venue"] or "", r["publication_date"] or "", r["title"] or "",
                       r["doi"] or "", r["url"] or ""))

    with open(OUT / "curation_review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uid", "categories", "decision", "reason", "venue",
                    "publication_date", "title", "doi", "url"])
        w.writerows(review)
    print(f"review   -> {OUT/'curation_review.csv'}")

    # --- funnel (per category + overall) ---
    reasons = ["non_english", "offtopic", "contractual_churn", "rfm_segmentation"]
    cats = ["non_contractual_churn", "btyd_models", "clv_rfm", "ml_noncontractual_churn"]
    def in_cat(row, cat): return cat in (row[1].split("|") if row[1] else [])
    funnel = []
    header = ["category", "identified", "already_hidden"] + reasons + ["kept"]
    for cat in cats + ["__ALL_unique__"]:
        sel = review if cat == "__ALL_unique__" else [r for r in review if in_cat(r, cat)]
        ident = len(sel)
        prev = sum(1 for r in sel if r[3] == "already_hidden")
        byr = {rn: sum(1 for r in sel if r[3] == rn) for rn in reasons}
        kept = sum(1 for r in sel if r[2] == "keep")
        funnel.append([cat, ident, prev] + [byr[rn] for rn in reasons] + [kept])
    with open(OUT / "funnel_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(funnel)

    print("\n=== FUNNEL (for the paper's figure) ===")
    print(f"{'category':26s} {'ident':>5} {'prevHid':>7} " +
          " ".join(f"{r[:9]:>9}" for r in reasons) + f" {'KEPT':>5}")
    for row in funnel:
        print(f"{row[0]:26s} {row[1]:5d} {row[2]:7d} " +
              " ".join(f"{v:9d}" for v in row[3:3+len(reasons)]) + f" {row[-1]:5d}")

    newly = [r for r in review if r[2] == "remove" and r[3] != "already_hidden"]
    print(f"\nnewly-removable: {len(newly)}   (already hidden: "
          f"{sum(1 for r in review if r[3]=='already_hidden')})")

    if not args.apply:
        print("\nDRY RUN — nothing changed. Re-run with --apply to hide the removals.")
        conn.close(); return

    # --- APPLY ---
    bak = DB.with_name(f"tracker.db.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(DB, bak); print(f"\nDB backed up -> {bak.name}")
    for r in newly:
        conn.execute("INSERT OR IGNORE INTO paper_state (uid) VALUES (?)", (r[0],))
        conn.execute("UPDATE paper_state SET hidden=1 WHERE uid=?", (r[0],))
    conn.commit()

    # rebuild removed_papers.csv from all hidden papers
    hidden_rows = [r for r in review if r[2] == "remove"]
    with open(OUT / "removed_papers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["reason", "venue", "title", "doi", "url"])
        for r in hidden_rows:
            w.writerow([r[3], r[4], r[6], r[7], r[8]])
    print(f"applied: hid {len(newly)} papers; removed_papers.csv now lists "
          f"{len(hidden_rows)} total.")
    conn.close()


if __name__ == "__main__":
    main()
