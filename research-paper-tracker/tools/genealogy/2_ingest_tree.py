"""Ingest the citation-tree genealogy into the tracker DB (one unified corpus).

- Backs up tracker.db first.
- Adds a `citation_edges` table (the tree structure).
- Inserts every tree node into `papers` (source='genealogy'), WITHOUT touching
  papers already present (dedup by uid = doi:.. | openalex:..).
- Adds a `paper_categories` row (category='genealogy', seeds also 'foundations')
  so the corpus surfaces as buckets in the GUI, carrying relevance + tags.
- Exports research-paper-tracker/data/out/genealogy_tree.csv.
"""
import sqlite3, csv, os, shutil
from datetime import date, datetime

ROOT = "C:/Users/Pranava Baascaran/Desktop/Projects/pareto-nbd-extension"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
DB = f"{ROOT}/research-paper-tracker/data/tracker.db"
OUT = f"{ROOT}/research-paper-tracker/data/out"
NODES = f"{SCRATCH}/tree_nodes.csv"
EDGES = f"{SCRATCH}/tree_edges.csv"
TODAY = date.today().isoformat()

def uid_of(doi, oaid):
    return f"doi:{doi.lower()}" if doi else f"openalex:{oaid}"

# ---- load tree ----
nodes = list(csv.DictReader(open(NODES, encoding="utf-8")))
edges = list(csv.DictReader(open(EDGES, encoding="utf-8")))
oaid2uid = {n["oaid"]: uid_of(n["doi"], n["oaid"]) for n in nodes}
print(f"tree: {len(nodes)} nodes, {len(edges)} edges")

# ---- backup ----
bak = f"{DB}.bak-{datetime.now():%Y%m%d-%H%M%S}"
shutil.copy2(DB, bak)
print(f"backup -> {os.path.basename(bak)}")

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS citation_edges (
    src_uid  TEXT, dst_uid TEXT, relation TEXT,
    PRIMARY KEY (src_uid, dst_uid, relation))""")
c.execute("CREATE INDEX IF NOT EXISTS idx_ce_src ON citation_edges(src_uid)")
c.execute("CREATE INDEX IF NOT EXISTS idx_ce_dst ON citation_edges(dst_uid)")

existing = {r[0] for r in c.execute("SELECT uid FROM papers")}
print(f"existing papers in DB: {len(existing)}")

ins_p = ins_c = skip = 0
for n in nodes:
    oaid, doi = n["oaid"], n["doi"]
    uid = oaid2uid[oaid]
    year = n["year"] or ""
    pubdate = f"{year}-01-01" if year else ""
    url = f"https://doi.org/{doi}" if doi else f"https://openalex.org/{oaid}"
    oa_url = f"https://openalex.org/{oaid}" if oaid.startswith("W") else ""
    if uid not in existing:
        c.execute("""INSERT OR IGNORE INTO papers
            (uid,doi,arxiv_id,oa_url,title,abstract,authors,venue,publication_date,source,url,first_seen)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, doi or None, None, oa_url,
             n["title"], n["abstract"], n["authors"], n["venue"], pubdate,
             "genealogy", url, TODAY))
        existing.add(uid); ins_p += 1
    # category rows (idempotent)
    rel = float(n["relevance"] or 0)
    c.execute("""INSERT OR IGNORE INTO paper_categories
        (uid,category,date_added,run_date,rank,match_score,relevance,matched_terms)
        VALUES (?,?,?,?,?,?,?,?)""",
        (uid, "genealogy", TODAY, TODAY, 0, int(rel), rel, n["tags"]))
    if c.rowcount: ins_c += 1
    if n["seed"] == "1":
        c.execute("""INSERT OR IGNORE INTO paper_categories
            (uid,category,date_added,run_date,rank,match_score,relevance,matched_terms)
            VALUES (?,?,?,?,?,?,?,?)""",
            (uid, "foundations", TODAY, TODAY, 0, int(rel), rel, n["seed_label"]))
    # keep genealogy rows unread + not-starred, but don't clobber existing state
    c.execute("INSERT OR IGNORE INTO paper_state (uid,read,starred,hidden,tags) VALUES (?,0,0,0,?)",
              (uid, n["tags"]))

ins_e = 0
for e in edges:
    su, du = oaid2uid.get(e["src_oaid"]), oaid2uid.get(e["dst_oaid"])
    if su and du:
        c.execute("INSERT OR IGNORE INTO citation_edges (src_uid,dst_uid,relation) VALUES (?,?,?)",
                  (su, du, e["relation"]))
        if c.rowcount: ins_e += 1

conn.commit()
print(f"inserted: papers +{ins_p}, category-rows +{ins_c}, edges +{ins_e}")

# ---- export genealogy CSV ----
os.makedirs(OUT, exist_ok=True)
q = """SELECT p.publication_date, p.title, p.authors, p.venue, p.doi,
       pc.relevance, pc.matched_terms, p.oa_url, p.source
       FROM papers p JOIN paper_categories pc ON pc.uid=p.uid
       WHERE pc.category='genealogy' ORDER BY p.publication_date"""
with open(f"{OUT}/genealogy_tree.csv","w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["publication_date","title","authors","venue","doi","relevance","tags","oa_url","source"])
    for row in c.execute(q): w.writerow(row)
print(f"exported {OUT}/genealogy_tree.csv")

# ---- summary ----
tot = c.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
gen = c.execute("SELECT COUNT(*) FROM papers WHERE source='genealogy'").fetchone()[0]
yr = c.execute("SELECT MIN(publication_date),MAX(publication_date) FROM papers WHERE publication_date!=''").fetchone()
print(f"\nDB now: {tot} papers total ({gen} genealogy). span {yr[0]} .. {yr[1]}")
conn.close()
