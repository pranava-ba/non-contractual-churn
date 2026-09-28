"""Crossref + OpenCitations citation-tree builder (no OpenAlex; DOI-keyed; free).

OpenAlex's keyless daily IP budget is exhausted and its DOI-lookup path is blocked,
so we build entirely on:
  * Crossref  /works/{doi}      -> metadata + reference[] (backward)  [polite pool]
  * Crossref  /works?query...   -> resolve each seed to its CORRECT DOI
  * OpenCitations COCI          -> citing DOIs (forward) of the seeds
Nodes are keyed by DOI. Emits the same tree_nodes.csv / tree_edges.csv the ingest
and history scripts consume. Forward progression WITHIN the corpus is later derived
by reversing reference edges.
"""
import urllib.request, urllib.parse, urllib.error, json, time, re, sys, csv, os, html
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

MAILTO = "santhosh.exe@gmail.com"
CR = "https://api.crossref.org/works"
COCI = "https://opencitations.net/index/coci/api/v1/citations"
OUT = os.path.dirname(os.path.abspath(__file__))

MAX_BACK_DEPTH = 2
FRONTIER_CAP   = 180
WANT_CAP       = 1600
FWD_CAP        = 25
NODE_CAP       = 3600

# (label, title, first_author_surname, doi_hint_or_None)
SEEDS = [
 ("Ehrenberg 1959 NBD","The Pattern of Consumer Purchases","Ehrenberg","10.2307/2985810"),
 ("Goodhardt Ehrenberg Chatfield 1984 Dirichlet","The Dirichlet a comprehensive model of buying behaviour","Goodhardt","10.2307/2981696"),
 ("Chatfield Ehrenberg Goodhardt 1966 NBD","Progress on a simplified model of stationary purchasing behaviour","Chatfield",None),
 ("Schmittlein Morrison Colombo 1987 Pareto/NBD","Counting your customers who are they and what will they do next","Schmittlein","10.1287/mnsc.33.1.1"),
 ("Schmittlein Peterson 1994 B2B","Customer base analysis an industrial purchase process application","Schmittlein","10.1287/mksc.13.1.41"),
 ("Morrison Schmittlein 1988 generalizing NBD","Generalizing the NBD model for customer purchases","Morrison",None),
 ("Reinartz Kumar 2000 noncontractual profitability","On the profitability of long-life customers in a noncontractual setting","Reinartz","10.1509/jmkg.64.4.17.18077"),
 ("Reinartz Kumar 2003 lifetime duration","The impact of customer relationship characteristics on profitable lifetime duration","Reinartz","10.1509/jmkg.67.1.77.18589"),
 ("Fader Hardie Lee 2005 BG/NBD","Counting your customers the easy way an alternative to the pareto nbd model","Fader","10.1287/mksc.1040.0098"),
 ("Fader Hardie Lee 2005 RFM CLV","RFM and CLV using iso value curves for customer base analysis","Fader",None),
 ("Fader Hardie 2001 CDNOW","Forecasting repeat sales at CDNOW a case study","Fader",None),
 ("Fader Hardie 2009 probability models","Probability models for customer base analysis","Fader","10.1016/j.intmar.2009.02.004"),
 ("Fader Hardie 2010 BG/BB discrete","Customer base analysis in a discrete time noncontractual setting","Fader","10.1287/mksc.1100.0580"),
 ("Abe 2009 HB Pareto/NBD","Counting your customers one by one a hierarchical bayes extension to the pareto nbd model","Abe","10.1287/mksc.1090.0502"),
 ("Platzer Reutterer 2016 Pareto/GGG","Ticking away the moments timing regularity helps to better predict customer activity","Platzer","10.1287/mksc.2015.0963"),
 ("Bemmaor Glady 2012 sudden death","Modeling purchasing behavior with sudden death a flexible customer lifetime model","Bemmaor","10.1287/mnsc.1110.1461"),
 ("Jerath Fader Hardie 2011 periodic death","New perspectives on customer death using a generalization of the pareto nbd model","Jerath","10.1287/mksc.1110.0654"),
 ("Batislam et al 2007","Empirical validation and comparison of models for customer base analysis","Batislam","10.1016/j.ijresmar.2006.12.005"),
 ("Wubben von Wangenheim 2008 heuristics","Instant customer base analysis managerial heuristics often get it right","Wubben","10.1509/jmkg.72.3.82"),
 ("Glady Baesens Croux 2009","A modified pareto nbd approach for predicting customer lifetime value","Glady",None),
 ("Gupta Lehmann Stuart 2004 valuing customers","Valuing customers","Gupta","10.1509/jmkr.41.1.7.25084"),
 ("Gupta et al 2006 Modeling CLV","Modeling customer lifetime value","Gupta","10.1177/1094670506293810"),
 ("Venkatesan Kumar 2004 CLV framework","A customer lifetime value framework for customer selection and resource allocation","Venkatesan","10.1509/jmkg.68.4.106.42728"),
 ("Rust Lemon Zeithaml 2004 customer equity","Return on marketing using customer equity to focus marketing strategy","Rust","10.1509/jmkg.68.1.109.24030"),
 ("Chamberlain et al 2017 CLV embeddings","Customer lifetime value prediction using embeddings","Chamberlain","10.1145/3097983.3098123"),
 ("Wang Liu Miao 2019 ZILN deep CLV","A deep probabilistic model for customer lifetime value prediction","Wang","10.48550/arXiv.1912.07753"),
 ("Valendin et al 2022 RNN CBA","Customer base analysis with recurrent neural networks","Valendin",None),
 ("Bauer Jannach 2021 deep CLV seq2seq","Improved customer lifetime value prediction with sequence to sequence learning and feature based models","Bauer",None),
 ("Buckinx Van den Poel 2005 partial defection","Customer base analysis partial defection of behaviourally loyal clients in a non contractual fmcg retail setting","Buckinx","10.1016/j.ejor.2004.06.036"),
 ("Migueis Van den Poel 2012 partial churn","Modeling partial customer churn on the value of first product category purchase sequences","Miguéis",None),
 ("Simon 2025 generalised comparison","A generalised comparison of pareto nbd based forecasts using mcmc","Simon","10.1007/s11573-025-01237-8"),
 ("Imani 2025 churn systematic review","Customer churn prediction a systematic literature review","Imani","10.3390/make7030105"),
 ("Manzoor et al 2024 churn ML review","Customer churn prediction a comprehensive review","Manzoor","10.1109/ACCESS.2024.3402092"),
 ("Gneiting Raftery 2007 proper scores","Strictly proper scoring rules prediction and estimation","Gneiting","10.1198/016214506000001437"),
 ("Gneiting Balabdaoui Raftery 2007 calibration","Probabilistic forecasts calibration and sharpness","Gneiting","10.1111/j.1467-9868.2007.00587.x"),
 ("Czado Gneiting Held 2009 PIT count","Predictive model assessment for count data","Czado","10.1111/j.1541-0420.2009.01191.x"),
 ("Dawid 1984 prequential","Present position and potential developments some personal views statistical theory the prequential approach","Dawid","10.2307/2981683"),
 ("Guo et al 2017 NN calibration","On calibration of modern neural networks","Guo","10.48550/arXiv.1706.04599"),
 ("Kuleshov Fenner Ermon 2018 calibrated regression","Accurate uncertainties for deep learning using calibrated regression","Kuleshov","10.48550/arXiv.1807.00263"),
]

CAL = re.compile(r"\bPIT\b|\bCRPS\b|calibrat|proper scor|reliability diagram|\bECE\b|"
                 r"probability integral|quantile loss|conformal|sharpness", re.I)
BTYD = re.compile(r"Pareto/?NBD|buy[- ]?till|\bBTYD\b|BG/?NBD|BG/?BB|Schmittlein|"
                  r"customer base analysis|counting your customers|negative binomial", re.I)
CHURN = re.compile(r"churn|defection|attrition|retention|customer base|repeat[- ]?buy|"
                   r"non[- ]?contractual|purchas", re.I)
CLV = re.compile(r"lifetime value|\bCLV\b|\bLTV\b|customer equity|customer value", re.I)

_last=[0.0]; MIN_INTERVAL=0.12
def _pace():
    dt=time.time()-_last[0]
    if dt<MIN_INTERVAL: time.sleep(MIN_INTERVAL-dt)
    _last[0]=time.time()

def _get(url, tries=5):
    for a in range(tries):
        _pace()
        try:
            req=urllib.request.Request(url, headers={"User-Agent": f"genealogy ({MAILTO})"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400,404): return None
            if e.code in (429,503):
                ra=0
                try: ra=int(e.headers.get("Retry-After",0))
                except Exception: pass
                time.sleep(min(ra or 3*(2**a),45)); continue
            if a==tries-1: return None
            time.sleep(2*(a+1))
        except Exception:
            if a==tries-1: return None
            time.sleep(2*(a+1))
    return None

def strip_tags(s):
    return re.sub(r"<[^>]+>","",html.unescape(s or "")).strip()
def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
def toks(s): return set(norm(s).split())

def cr_get(doi):
    d=_get(f"{CR}/{urllib.parse.quote(doi)}?mailto={MAILTO}")
    return d.get("message") if d else None
def cr_search(title, author):
    q=urllib.parse.urlencode({"query.bibliographic":title,"query.author":author,
                              "rows":3,"mailto":MAILTO})
    d=_get(f"{CR}?{q}")
    return (d.get("message",{}).get("items") if d else []) or []

nodes={}; edges=set()
def rec_from_msg(m, depth, is_seed=False, seed_label=""):
    doi=(m.get("DOI") or "").lower()
    if not doi: return None
    title=(m.get("title") or [""])[0]
    abt=strip_tags(m.get("abstract"))
    yr=""
    try: yr=(m.get("issued") or {}).get("date-parts",[[None]])[0][0] or ""
    except Exception: yr=""
    venue=(m.get("container-title") or [""])[0] if m.get("container-title") else ""
    auth="; ".join(f"{a.get('given','')} {a.get('family','')}".strip()
                   for a in (m.get("author") or [])[:6])
    cb=m.get("is-referenced-by-count") or 0
    refs=[(r.get("DOI") or "").lower() for r in (m.get("reference") or []) if r.get("DOI")]
    t=f"{title} {abt} {venue}"; tags=[]; s=0
    if BTYD.search(t): tags.append("BTYD"); s+=3
    if CHURN.search(t): tags.append("churn"); s+=2
    if CLV.search(t): tags.append("CLV"); s+=2
    if CAL.search(t): tags.append("calib"); s+=2
    r=nodes.get(doi)
    if r is None:
        nodes[doi]=dict(oaid=doi,doi=doi,title=title,year=yr,venue=venue,authors=auth,
            cited_by=cb,depth=depth,seed=int(is_seed),seed_label=seed_label,
            relevance=s,tags="|".join(tags),abstract=abt[:1500],refs=refs)
    else:
        r["depth"]=min(r["depth"],depth)
        if is_seed: r["seed"]=1; r["seed_label"]=seed_label or r["seed_label"]
        if refs and not r["refs"]: r["refs"]=refs
    return doi

# ---- 1. seeds — resolve to the CANONICAL version ----
# Prefer, across the hint DOI + top search hits: title overlap >=0.6, then a real
# published type (journal/proceedings/book) over preprints/reports/theses, then the
# most-cited (the canonical version), then best overlap. This corrects both wrong
# hint DOIs and search hits that land on a preprint/tech-report/thesis clone.
GOOD_TYPES={"journal-article","proceedings-article","book-chapter","book","monograph","reference-entry"}
BAD_TYPES={"posted-content","report","dissertation","other","component","dataset","grant"}
def _ov(title,m):
    return len(toks(title)&toks((m.get("title") or [""])[0]))/max(1,len(toks(title)))
def _score_msg(m,title):
    typ=m.get("type","")
    trank=2 if typ in GOOD_TYPES else (0 if typ in BAD_TYPES else 1)
    return (trank, m.get("is-referenced-by-count") or 0, _ov(title,m))
def resolve_seed(title,author,hint):
    cands=[]
    if hint:
        m=cr_get(hint)
        if m: cands.append(m)
    cands += cr_search(title,author)
    cands=[m for m in cands if _ov(title,m)>=0.6]
    return max(cands, key=lambda m:_score_msg(m,title)) if cands else None

print("Resolving seeds to canonical version...", flush=True)
seed_ids=[]
for label,title,author,hint in SEEDS:
    m=resolve_seed(title,author,hint)
    if not m:
        print(f"  MISS {label}"); continue
    i=rec_from_msg(m,0,is_seed=True,seed_label=label); seed_ids.append(i)
    print(f"  ok {label[:42]:42s} {nodes[i]['year']} cb={nodes[i]['cited_by']} refs={len(nodes[i]['refs'])} [{m.get('type','')}]  {i}")
seed_ids=list(dict.fromkeys([i for i in seed_ids if i]))
print(f"seeds: {len(seed_ids)}\n", flush=True)

# ---- 2. backward via Crossref reference DOIs ----
frontier=list(seed_ids)
for depth in range(1,MAX_BACK_DEPTH+1):
    if depth>=2:
        frontier=sorted([i for i in frontier if nodes[i]["relevance"]>=2],
                        key=lambda i:(nodes[i]["relevance"],nodes[i]["cited_by"]),reverse=True)[:FRONTIER_CAP]
    want=[]; seen=set()
    for i in frontier:
        for r in nodes[i]["refs"]:
            if r and r not in nodes and r not in seen:
                seen.add(r); want.append(r)
    want=want[:WANT_CAP]
    print(f"[back d{depth}] frontier={len(frontier)} fetch {len(want)} (corpus={len(nodes)})",flush=True)
    if not want or len(nodes)>=NODE_CAP: break
    newf=[]
    for n,r in enumerate(want):
        m=cr_get(r)
        if m:
            nid=rec_from_msg(m,depth)          # canonical DOI may differ from r
            if nid: newf.append(nid)
        if n and n%150==0: print(f"    .. {n}/{len(want)} corpus={len(nodes)}",flush=True)
    frontier=list(dict.fromkeys(newf))

# ---- 3. forward via OpenCitations (seeds) ----
print(f"\n[fwd] OpenCitations citers of seeds (cap {FWD_CAP}/seed)",flush=True)
for sid in list(seed_ids):
    if len(nodes)>=NODE_CAP: break
    d=_get(f"{COCI}/{sid}")
    if not d: continue
    citers=[c.get("citing") for c in d if c.get("citing")][:FWD_CAP]
    for cdoi in citers:
        cdoi=(cdoi or "").strip().lower()
        if not cdoi: continue
        if cdoi in nodes:
            edges.add((cdoi,sid,"cites")); continue
        m=cr_get(cdoi)
        if m:
            cid=rec_from_msg(m,1)
            if cid: edges.add((cid,sid,"cites"))
    print(f"  {nodes[sid]['seed_label'][:36]:36s} corpus={len(nodes)}",flush=True)

# ---- 4. reference edges within corpus ----
idset=set(nodes)
for i,rec in nodes.items():
    for r in rec["refs"]:
        if r in idset: edges.add((i,r,"references"))

# ---- 5. write ----
with open(os.path.join(OUT,"tree_nodes.csv"),"w",newline="",encoding="utf-8") as f:
    wr=csv.writer(f); wr.writerow(["oaid","doi","title","year","venue","authors","cited_by","depth","seed","seed_label","relevance","tags","abstract"])
    for r in sorted(nodes.values(), key=lambda r:(int(r["year"]) if str(r["year"]).isdigit() else 0)):
        wr.writerow([r["oaid"],r["doi"],r["title"],r["year"],r["venue"],r["authors"],r["cited_by"],r["depth"],r["seed"],r["seed_label"],r["relevance"],r["tags"],r["abstract"]])
with open(os.path.join(OUT,"tree_edges.csv"),"w",newline="",encoding="utf-8") as f:
    wr=csv.writer(f); wr.writerow(["src_oaid","dst_oaid","relation"])
    for e in sorted(edges): wr.writerow(e)
print(f"\nDONE {len(nodes)} nodes, {len(edges)} edges")
print(f"relevance>=2: {sum(1 for r in nodes.values() if r['relevance']>=2)}  BTYD: {sum('BTYD' in r['tags'] for r in nodes.values())}")
