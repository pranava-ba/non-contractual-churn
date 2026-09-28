"""Build HISTORICAL_PROGRESSION.md from the citation tree.

Shows how each paper progresses FORWARD: for the field's spine (seeds + the
highest-signal descendants) it lists year, venue, global citations, and — the
forward-progression column — how many *in-corpus* papers cite it and the notable
later works that do. Emits a large chronological markdown table + era rollup.
"""
import csv, os, collections, datetime, html as _html

ROOT = "C:/Users/Pranava Baascaran/Desktop/Projects/pareto-nbd-extension"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
NODES = f"{SCRATCH}/tree_nodes.csv"
EDGES = f"{SCRATCH}/tree_edges.csv"
OUTMD = f"{ROOT}/deep_research/HISTORICAL_PROGRESSION.md"

nodes = {n["oaid"]: n for n in csv.DictReader(open(NODES, encoding="utf-8"))}
edges = list(csv.DictReader(open(EDGES, encoding="utf-8")))

# in-corpus forward citations: who cites X  (edge cites: src cites dst -> dst gets forward)
fwd = collections.defaultdict(list)   # dst -> [src...]
back = collections.defaultdict(list)  # src -> [dst...] (references)
for e in edges:
    s, d, rel = e["src_oaid"], e["dst_oaid"], e["relation"]
    if s not in nodes or d not in nodes:
        continue
    if rel == "cites":          # s cites d  => d is cited by s
        fwd[d].append(s)
    elif rel == "references":   # s references d => d is cited by s
        fwd[d].append(s)
        back[s].append(d)

def yr(n):
    try: return int(n["year"])
    except: return 0
def short_auth(a):
    a=_html.unescape(a or "")
    if not a: return "—"
    first = a.split(";")[0].strip()
    last = first.split()[-1] if first else "—"
    n = a.count(";") + 1
    return last + (" et al." if n >= 3 else (f" & {a.split(';')[1].strip().split()[-1]}" if n==2 else ""))
def short_title(t, k=8):
    t=_html.unescape(t or "")
    return " ".join(t.split()[:k]) + ("…" if len(t.split())>k else "")

# spine = all seeds + top descendants by (relevance, cited_by)
seeds = [n for n in nodes.values() if n["seed"]=="1"]
desc = [n for n in nodes.values() if n["seed"]!="1"]
def score(n):
    try: cb=int(n["cited_by"])
    except: cb=0
    return (int(n["relevance"] or 0), len(fwd[n["oaid"]]), cb)
desc_top = sorted(desc, key=score, reverse=True)[:70]
spine = {n["oaid"] for n in seeds} | {n["oaid"] for n in desc_top}
rows = sorted((nodes[o] for o in spine), key=lambda n:(yr(n), -int(n["cited_by"] or 0)))

def notable_forward(oaid, k=3):
    cs = sorted(fwd[oaid], key=lambda s:(int(nodes[s]["relevance"] or 0), int(nodes[s]["cited_by"] or 0)), reverse=True)
    out=[]
    for s in cs:
        if nodes[s]["oaid"]==oaid: continue
        out.append(f"{short_auth(nodes[s]['authors'])} {nodes[s]['year']}")
        if len(out)>=k: break
    return "; ".join(out) or "—"

# ---- write ----
total = len(nodes)
rel2 = sum(1 for n in nodes.values() if int(n["relevance"] or 0)>=2)
btyd = sum(1 for n in nodes.values() if "BTYD" in (n["tags"] or ""))
minyr = min((yr(n) for n in nodes.values() if yr(n)>0), default=0)
maxyr = max((yr(n) for n in nodes.values() if yr(n)>0), default=0)

L=[]
L.append("---")
L.append('title: "Historical progression — non-contractual churn / BTYD"')
L.append("type: reference")
L.append(f"updated: {datetime.date.today().isoformat()}")
L.append("role: The year-by-year spine of the field, generated from the citation tree.")
L.append("      Each row shows a paper and how it progresses FORWARD (in-corpus works that cite it).")
L.append("---\n")
L.append("# Historical progression of non-contractual churn modelling\n")
L.append(f"> Generated from the citation-tree repository (`research-paper-tracker/data/tracker.db`, "
         f"`source='genealogy'`; raw CSV `data/out/genealogy_tree.csv`). "
         f"**{total} papers** span **{minyr}–{maxyr}**; {rel2} are on-topic (relevance≥2), "
         f"{btyd} explicitly BTYD/customer-base. This file shows the **spine** "
         f"({len(rows)} pivotal works); the full corpus is in the DB/CSV.\n")
L.append("**Columns.** *Cites* = global OpenAlex citations. *→ In-corpus* = how many papers "
         "in this repository cite it (its measured forward influence *within the field*). "
         "*Notable descendants* = the highest-signal later works that cite it — literally "
         "how the idea progresses forward. *Tags*: BTYD / churn / CLV / calib.\n")
L.append("| Year | Authors | Title | Venue | Cites | → In-corpus | Notable descendants | Tags |")
L.append("|---|---|---|---|---:|---:|---|---|")
for n in rows:
    mark = " **★**" if n["seed"]=="1" else ""
    L.append(f"| {n['year'] or '—'} | {short_auth(n['authors'])}{mark} | {short_title(n['title'])} | "
             f"{short_title(n['venue'],5) or '—'} | {n['cited_by'] or 0} | {len(fwd[n['oaid']])} | "
             f"{notable_forward(n['oaid'])} | {n['tags'] or '—'} |")
L.append("\n★ = seed (foundational / currently-cited).\n")

# era rollup
L.append("## Era rollup — papers per period (whole corpus)\n")
buckets = collections.Counter()
labels = [("≤1986","pre-history"),("1987-1999","founding+consolidation"),
          ("2000-2009","CLV + BTYD boom"),("2010-2016","variants + validation"),
          ("2017-2022","ML turn"),("2023-2026","live frontier")]
def bucket(y):
    if y<=1986: return "≤1986"
    if y<=1999: return "1987-1999"
    if y<=2009: return "2000-2009"
    if y<=2016: return "2010-2016"
    if y<=2022: return "2017-2022"
    return "2023-2026"
for n in nodes.values():
    if yr(n)>0: buckets[bucket(yr(n))]+=1
L.append("| Period | Theme | Papers in corpus |")
L.append("|---|---|---:|")
for key,theme in labels:
    L.append(f"| {key} | {theme} | {buckets.get(key,0)} |")
L.append("")

open(OUTMD,"w",encoding="utf-8").write("\n".join(L))
print(f"wrote {OUTMD}  ({len(rows)} spine rows, {total} corpus)")
