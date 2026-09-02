"""OpenAlex forward-citation + topical monitor for the Phase 2 paper (deep_dive.md §4/§9).

For each seed core paper it pulls 2023+ works that CITE it (most-cited + most-recent), plus a set
of topical searches, reconstructs abstracts, and flags:
  [CALIB] the work evaluates by calibration (PIT/CRPS/coverage/ECE/proper scoring) -> novelty check
  [BTYD]  mentions Pareto/NBD / buy-till-you-die
  [INDIA] India / Indian (the open F8 dataset gap)
Run:  python deep_research/openalex_monitor.py
"""
import urllib.request, urllib.parse, json, time, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAILTO = "santhosh.exe@gmail.com"
API = "https://api.openalex.org/works"

SEEDS = {
    "Schmittlein 1987 Pareto/NBD": "10.1287/mnsc.33.1.1",
    "Fader 2005 BG/NBD":           "10.1287/mksc.1040.0098",
    "Platzer 2016 Pareto/GGG":     "10.1287/mksc.2015.0963",
    "Abe 2009 HB Pareto/NBD":      "10.1287/mksc.1090.0502",
    "Valendin 2022 RNN CBA":       "10.1016/j.ijresmar.2022.02.001",
    "Simon 2025 (source)":         "10.1007/s11573-025-01237-8",
}
TOPICAL = [
    "Pareto/NBD customer base analysis forecast calibration",
    "buy till you die probabilistic customer lifetime value",
    "non-contractual customer churn calibration proper scoring",
    "customer lifetime value deep learning probabilistic",
    "non-contractual customer churn India retail transactions",
]
CAL = re.compile(r"\bPIT\b|\bCRPS\b|calibrat|proper scor|reliability diagram|\bECE\b|coverage|"
                 r"probability integral|quantile loss|conformal", re.I)
BTYD = re.compile(r"Pareto/?NBD|buy[- ]?till|\bBTYD\b|BG/?NBD|Schmittlein", re.I)
INDIA = re.compile(r"\bIndia\b|\bIndian\b", re.I)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"phase2-monitor ({MAILTO})"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _abstract(w):
    inv = w.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def resolve(doi):
    return _get(f"{API}/doi:{doi}?mailto={MAILTO}")["id"].rsplit("/", 1)[-1]


def works(filt, sort, n=8):
    q = urllib.parse.urlencode({"filter": filt, "sort": sort, "per-page": n, "mailto": MAILTO})
    try:
        return _get(f"{API}?{q}").get("results", [])
    except Exception as e:
        print("   query error:", e); return []


def flags(w):
    text = (w.get("title") or "") + " " + _abstract(w)
    f = []
    if CAL.search(text): f.append("CALIB")
    if BTYD.search(text): f.append("BTYD")
    if INDIA.search(text): f.append("INDIA")
    return f


def show(w, seen):
    wid = w.get("id", "").rsplit("/", 1)[-1]
    if wid in seen:
        return
    seen.add(wid)
    src = (w.get("primary_location") or {}).get("source") or {}
    venue = src.get("display_name") or "?"
    fl = flags(w)
    tag = ("  <<< " + " ".join(fl)) if fl else ""
    print(f"   [{w.get('publication_year')}] cb={w.get('cited_by_count'):>4}  "
          f"{(w.get('title') or '')[:88]}  ({venue[:32]}){tag}")


def main():
    seen = set()
    hot = []  # calibration-flagged, for the summary
    for name, doi in SEEDS.items():
        try:
            wid = resolve(doi)
        except Exception as e:
            print(f"\n### {name}: resolve failed ({e})"); continue
        print(f"\n### CITES {name}  ({wid}) — 2023+")
        for sort in ("cited_by_count:desc", "publication_date:desc"):
            for w in works(f"cites:{wid},from_publication_date:2023-01-01,type:article", sort, 6):
                show(w, seen)
                if "CALIB" in flags(w):
                    hot.append(w)
            time.sleep(0.3)
    for q in TOPICAL:
        print(f"\n### SEARCH  '{q}' — 2023+")
        qq = urllib.parse.urlencode({"search": q, "filter": "from_publication_date:2023-01-01,type:article",
                                     "sort": "relevance_score:desc", "per-page": 8, "mailto": MAILTO})
        try:
            res = _get(f"{API}?{qq}").get("results", [])
        except Exception as e:
            print("   search error:", e); res = []
        for w in res:
            show(w, seen)
            if "CALIB" in flags(w):
                hot.append(w)
        time.sleep(0.3)
    print(f"\n{'='*70}\nCALIBRATION-FLAGGED works (novelty check): {len(hot)}")
    for w in hot:
        print(f"   [{w.get('publication_year')}] {(w.get('title') or '')[:96]}")


if __name__ == "__main__":
    main()
