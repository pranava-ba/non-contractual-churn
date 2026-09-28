"""Triage the raw citation-tree corpus into read-tiers (the sifting funnel).

Reads tree_nodes.csv + tree_edges.csv. Scores every paper on independent signals
(keyword relevance, seed-connectivity, in-corpus citation degree, cross-source
corroboration, global citations, recency), assigns Tier A/B/C/D, runs QC
(duplicate/preprint + orphan + year), and writes:
  * genealogy_triage.csv     every paper + all signals + tier (the audit trail)
  * CORE_READING_LIST.md     Tier-A spine, grouped by era (the actual reading list)
  * funnel printed to stdout (identified -> tiers)
Also tags tracker.db: paper_state.tags gets the tier; Tier-A papers also get a
'core_reading' category so the GUI shows them as a browsable bucket.
"""
import csv, os, collections, sqlite3, re, math, datetime, html as _html

ROOT = "C:/Users/Pranava Baascaran/Desktop/Projects/pareto-nbd-extension"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
NODES = f"{SCRATCH}/tree_nodes.csv"
EDGES = f"{SCRATCH}/tree_edges.csv"
DB = f"{ROOT}/research-paper-tracker/data/tracker.db"
OUTCSV = f"{ROOT}/research-paper-tracker/data/out/genealogy_triage.csv"
OUTMD = f"{ROOT}/deep_research/CORE_READING_LIST.md"
TODAY = datetime.date.today().isoformat()

nodes = {n["oaid"]: n for n in csv.DictReader(open(NODES, encoding="utf-8"))}
edges = list(csv.DictReader(open(EDGES, encoding="utf-8")))
seeds = {o for o,n in nodes.items() if n["seed"] == "1"}

def yr(n):
    try: return int(n["year"])
    except: return 0
def cb(n):
    try: return int(n["cited_by"])
    except: return 0

# ---- graph signals ----
deg_in = collections.Counter()      # corpus papers that cite X (forward influence)
deg_out = collections.Counter()     # corpus papers X cites
seed_conn = collections.defaultdict(set)   # distinct seeds X is edge-connected to
cites_a_seed = set()                # X -> seed  (X cites a seed)
reffed_by_seed = set()              # seed -> X  (a seed references X)
for e in edges:
    s, d, rel = e["src_oaid"], e["dst_oaid"], e["relation"]
    if s not in nodes or d not in nodes: continue
    # edge means s -> d : "s cites d" or "s references d"  => d gains forward degree
    deg_in[d] += 1; deg_out[s] += 1
    if d in seeds: seed_conn[s].add(d); cites_a_seed.add(s)
    if s in seeds: seed_conn[d].add(s); reffed_by_seed.add(d)

def tier_of(o):
    n = nodes[o]
    kw = int(n["relevance"] or 0)
    sc = len(seed_conn.get(o, ()))
    di = deg_in[o]
    c  = cb(n)
    corrob = (o in cites_a_seed) and (o in reffed_by_seed)
    is_btyd = "BTYD" in (n["tags"] or "")
    if o in seeds:
        return "A", 999, kw, sc, di, c, corrob
    # composite (interpretable): topical vocab dominates, then graph centrality, then impact
    score = 4*kw + 3*sc + 2*min(di,10) + 3*int(corrob) + 2*is_btyd + math.log10(c+1)
    if (is_btyd and (sc>=2 or di>=3)) or (kw>=4 and c>=100) or (kw>=3 and sc>=3):
        t = "A"                                   # core spine — read
    elif kw>=2 and (sc>=2 or di>=3 or c>=100 or corrob or (is_btyd and di>=1)):
        t = "B"                                   # solidly on-topic — scan
    elif kw>=2:
        t = "C"                                   # weakly-linked on-topic — reference tail
    else:
        t = "D"                                   # tools / off-topic — archive
    return t, round(score,2), kw, sc, di, c, corrob

# ---- QC: duplicate/preprint + orphan ----
by_title = collections.defaultdict(list)
def norm(s): return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
for o,n in nodes.items():
    if n["title"]: by_title[norm(n["title"])[:80]].append(o)
dups = {o for grp in by_title.values() if len(grp)>1 for o in grp}
orphans = {o for o in nodes if deg_in[o]==0 and deg_out[o]==0 and o not in seeds}

rows=[]
tally=collections.Counter()
for o,n in nodes.items():
    t,score,kw,sc,di,c,corrob = tier_of(o)
    tally[t]+=1
    rows.append(dict(tier=t,score=score,year=n["year"],authors=n["authors"],title=n["title"],
        venue=n["venue"],cited_by=c,kw=kw,seed_conn=sc,deg_in=di,corrob=int(corrob),
        tags=n["tags"],seed=n["seed"],dup=int(o in dups),orphan=int(o in orphans),
        doi=n["doi"],oaid=o))
rows.sort(key=lambda r:("ABCD".index(r["tier"]), -r["score"], -r["cited_by"]))

with open(OUTCSV,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["tier","score","year","authors","title","venue","cited_by",
        "kw","seed_conn","deg_in","corrob","tags","seed","dup","orphan","doi","oaid"])
    w.writeheader(); w.writerows(rows)

# ---- Tier-A reading list (by era) ----
def era(y):
    if y<=1986: return "0. Pre-history — repeat-buying (≤1986)"
    if y<=1999: return "1. Founding & consolidation (1987–1999)"
    if y<=2009: return "2. CLV + BTYD boom (2000–2009)"
    if y<=2016: return "3. Variants & validation (2010–2016)"
    if y<=2022: return "4. The ML turn (2017–2022)"
    return "5. Live frontier (2023–2026)"
A=[r for r in rows if r["tier"]=="A"]
buckets=collections.defaultdict(list)
for r in A: buckets[era(int(r["year"]) if str(r["year"]).isdigit() else 0)].append(r)

L=["---",'title: "Core reading list — non-contractual churn genealogy"',"type: reference",
   f"updated: {TODAY}","role: Tier-A spine sifted from the full citation tree. The literature",
   "      review to actually read; B/C/D live in genealogy_triage.csv.","---","",
   "# Core reading list (Tier A)","",
   f"> Sifted from **{len(nodes)} papers** in the citation tree by the triage funnel "
   f"(deep_research — see the method in the session notes). "
   f"**Tier A = {tally['A']}** (read), B = {tally['B']} (scan), C = {tally['C']} (reference), "
   f"D = {tally['D']} (tools/off-topic). Full signals + tiers: "
   f"`research-paper-tracker/data/out/genealogy_triage.csv`.","",
   "**Why a paper is here:** ★ = foundational seed · high keyword relevance · linked to "
   "multiple seeds · high in-corpus citation degree · or high field-wide citations. "
   "Columns: *cb* = global citations, *sd* = distinct seeds linked, *in* = in-corpus citations.",""]
for e in sorted(buckets):
    L.append(f"## {e}\n")
    L.append("| Year | Authors | Title | Venue | cb | sd | in | tags |")
    L.append("|---|---|---|---|---:|---:|---:|---|")
    for r in sorted(buckets[e], key=lambda r:(-r["score"],-r["cited_by"])):
        au=(r["authors"].split(";")[0].split()[-1] if r["authors"] else "—")
        n_au=r["authors"].count(";")+1 if r["authors"] else 0
        au+=" et al." if n_au>=3 else ""
        star=" ★" if r["seed"]=="1" else ""
        au=_html.unescape(au)
        ti=" ".join(_html.unescape(r["title"] or "").split()[:11])
        ve=" ".join(_html.unescape(r["venue"] or "").split()[:4])
        L.append(f"| {r['year'] or '—'} | {au}{star} | {ti} | {ve or '—'} | {r['cited_by']} | "
                 f"{r['seed_conn']} | {r['deg_in']} | {r['tags'] or '—'} |")
    L.append("")
open(OUTMD,"w",encoding="utf-8").write("\n".join(L))

# ---- write tiers back to DB ----
def uid_of(n):
    return f"doi:{n['doi'].lower()}" if n["doi"] else f"s2:{n['oaid']}"
conn=sqlite3.connect(DB); c=conn.cursor()
tagged=0; corecat=0
for o,n in nodes.items():
    t=tier_of(o)[0]
    uid=uid_of(n)
    # append tier tag to paper_state.tags (keep existing)
    row=c.execute("SELECT tags FROM paper_state WHERE uid=?",(uid,)).fetchone()
    base=(row[0] if row and row[0] else "")
    parts=[p for p in base.split(";") if p and not p.startswith("tier:")]
    parts.append(f"tier:{t}")
    c.execute("INSERT INTO paper_state(uid,read,starred,hidden,tags) VALUES(?,0,0,0,?) "
              "ON CONFLICT(uid) DO UPDATE SET tags=excluded.tags",(uid,";".join(parts)))
    tagged+=1
    if t=="A":
        c.execute("""INSERT OR IGNORE INTO paper_categories
            (uid,category,date_added,run_date,rank,match_score,relevance,matched_terms)
            VALUES(?,?,?,?,?,?,?,?)""",(uid,"core_reading",TODAY,TODAY,0,
            int(n["relevance"] or 0),float(n["relevance"] or 0),n["tags"])); corecat+=c.rowcount
conn.commit(); conn.close()

print(f"corpus={len(nodes)}  tiers: A={tally['A']} B={tally['B']} C={tally['C']} D={tally['D']}")
print(f"QC: duplicate/version rows={len(dups)}  orphans={len(orphans)}")
print(f"wrote {OUTCSV}\nwrote {OUTMD}\nDB: tagged {tagged} states, +{corecat} core_reading rows")
