"""Beatability signals extracted from a paper's title + abstract.

The whole point of the reproduce-and-improve project is picking a paper you can
(a) actually reproduce and (b) plausibly beat. So for each candidate we mine the
abstract for:

    * a headline metric  (accuracy / F1 / AUC / ... of 96.2%)  -> is there room?
    * public datasets    (MNIST, ISIC, UCI, "publicly available", ...) -> reproducible?
    * code availability   (github, "code is available")            -> reproducible?

and roll it into a coarse band the UI colours: strong / ok / weak / unknown.
These are *hints from the abstract only* — always confirm in the full paper.
"""
from __future__ import annotations

import re

# Higher-is-better % metrics — a value below ~98.5 means there's headroom to beat.
_HB = (r"accuracy|acc|f1[- ]?score|f-?measure|f1|auroc|au[- ]?roc|auc|precision|"
       r"recall|sensitivity|specificity|dice(?:[- ]score)?|iou|jaccard|"
       r"map|mean average precision|bleu|rouge|kappa|balanced accuracy")
# Lower-is-better metrics — reported for context, not used to judge "room".
_LB = r"rmse|mae|mse|error rate|eer|mape|perplexity|wer|cer|log[- ]?loss"

_NUM = r"(\d{1,3}(?:\.\d+)?)\s*%"          # require a percent sign to avoid noise
_NUM_ANY = r"(\d{1,3}(?:\.\d+)?)\s*%?"     # metric-first form may omit the %

# "... accuracy of 96.2%" / "F1 = 0.94" style (metric then number)
_RE_MB = re.compile(rf"\b({_HB}|{_LB})\b[^.\n]{{0,25}}?{_NUM_ANY}", re.I)
# "96.2% accuracy" style (number then metric)
_RE_BM = re.compile(rf"{_NUM}\s*(?:of\s+)?\b({_HB}|{_LB})\b", re.I)

_HB_RE = re.compile(rf"\b({_HB})\b", re.I)

# Well-known public benchmarks, grouped loosely by area.
_DATASETS = [
    "MNIST", "Fashion-MNIST", "CIFAR-10", "CIFAR-100", "CIFAR", "ImageNet",
    "SVHN", "STL-10", "Tiny ImageNet", "Caltech-101", "Caltech-256",
    "ISIC", "HAM10000", "ChestX-ray14", "ChestX-ray", "CheXpert", "NIH Chest",
    "BraTS", "LIDC", "DRIVE", "STARE", "Kvasir", "PH2", "MIAS", "DDSM", "CBIS-DDSM",
    "PhysioNet", "MIMIC-III", "MIMIC-IV", "MIMIC", "PTB-XL", "MIT-BIH",
    "UCI", "Kaggle", "OpenML",
    "Cleveland", "Pima", "Wisconsin", "WDBC", "Iris", "Adult", "Heart Disease",
    "NSL-KDD", "KDD Cup", "KDDCup", "CICIDS", "CIC-IDS", "UNSW-NB15", "CICIDS2017",
    "UCI HAR", "WISDM", "PAMAP2", "OPPORTUNITY", "mHealth",
    "IMDB", "SST", "SST-2", "GLUE", "SQuAD", "AG News", "20 Newsgroups",
    "Reuters", "Yelp", "Amazon Reviews", "TREC", "SNLI", "MultiNLI",
    "Indian Pines", "Pavia", "Salinas", "Houston",
    "Cora", "Citeseer", "PubMed", "Yahoo", "MovieLens",
    "DEAP", "SEED", "BCI Competition", "CHB-MIT",
]
_DATASET_RES = [(d, re.compile(r"\b" + re.escape(d) + r"\b", re.I)) for d in _DATASETS]

_PUBLIC_PHRASES = re.compile(
    r"publicly available|publicly accessible|public(?:ly)?[- ]?(?:available )?dataset|"
    r"open[- ]access dataset|benchmark dataset|open dataset|open[- ]source dataset|"
    r"uci machine learning repository|freely available", re.I)

_CODE_RE = re.compile(
    r"github\.com|gitlab\.com|\bgithub\b|code is (?:publicly )?available|"
    r"source code (?:is )?(?:available|released)|our (?:code|implementation) "
    r"(?:is )?available|reproduc\w+ package|available at http", re.I)


def _to_pct(value_str: str) -> float:
    v = float(value_str)
    if v <= 1.0:            # 0.962 -> 96.2 (fractions reported without a %)
        v *= 100.0
    return round(v, 2)


def extract_metrics(text: str) -> list[dict]:
    """Every metric mention we can find, de-duplicated, best value per metric."""
    found: dict[str, float] = {}
    for m in _RE_BM.finditer(text):                    # number-then-metric
        name, val = m.group(2).lower(), _to_pct(m.group(1))
        found[name] = max(found.get(name, 0.0), val)
    for m in _RE_MB.finditer(text):                    # metric-then-number
        name, val = m.group(1).lower(), _to_pct(m.group(2))
        found[name] = max(found.get(name, 0.0), val)
    return [{"name": k, "value": v} for k, v in found.items()]


def _headline(metrics: list[dict]) -> dict | None:
    """The metric we judge 'room' on: prefer accuracy > F1 > AUC > the rest, and
    only higher-is-better metrics count."""
    order = ["accuracy", "acc", "balanced accuracy", "f1", "f1-score", "f1 score",
             "f-measure", "auc", "auroc", "au-roc", "dice", "dice score", "iou",
             "jaccard", "precision", "recall", "sensitivity", "specificity",
             "kappa", "map", "mean average precision", "bleu", "rouge"]
    hb = [m for m in metrics if _HB_RE.fullmatch(m["name"]) or _HB_RE.match(m["name"])]
    if not hb:
        return None
    def rank(m):
        n = m["name"]
        return order.index(n) if n in order else len(order)
    hb.sort(key=lambda m: (rank(m), -m["value"]))
    return hb[0]


def detect_datasets(text: str) -> tuple[list[str], bool]:
    hits: list[str] = []
    for name, rex in _DATASET_RES:
        if rex.search(text) and name not in hits:
            hits.append(name)
    public = bool(hits) or bool(_PUBLIC_PHRASES.search(text))
    return hits[:6], public


def detect_code(text: str, oa_url: str | None = None) -> bool:
    if oa_url and ("github" in oa_url.lower() or "gitlab" in oa_url.lower()):
        return True
    return bool(_CODE_RE.search(text))


def score(paper: dict) -> dict:
    """Mutate `paper` in place with beatability fields, and return it."""
    text = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
    metrics = extract_metrics(text)
    headline = _headline(metrics)
    datasets, public = detect_datasets(text)
    code = detect_code(text, paper.get("oa_url"))

    reasons: list[str] = []
    room = "unknown"
    if headline:
        v = headline["value"]
        if v > 99.5:
            room = "saturated"
            reasons.append(f"{headline['name']} {v}% - near-ceiling, hard to beat")
        elif v > 98.5:
            room = "tight"
            reasons.append(f"{headline['name']} {v}% - little headroom")
        else:
            room = "open"
            reasons.append(f"{headline['name']} {v}% - clear room to improve")
    else:
        reasons.append("no headline % metric found in abstract")

    if datasets:
        reasons.append("public data: " + ", ".join(datasets))
    elif public:
        reasons.append("mentions a publicly available dataset")
    else:
        reasons.append("no public dataset named in abstract")
    if code:
        reasons.append("code appears to be available")

    repro = bool(datasets or public)
    if room == "open" and repro:
        band = "strong"
    elif room == "saturated":
        band = "weak"
    elif room in ("open", "tight") or repro:
        band = "ok"
    else:
        band = "unknown"

    paper.update(
        metrics=metrics,
        headline=headline,
        datasets=datasets,
        public_hint=public,
        code=code,
        room=room,
        band=band,
        reasons=reasons,
    )
    return paper
