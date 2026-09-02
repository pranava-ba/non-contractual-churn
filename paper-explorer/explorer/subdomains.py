"""AI/ML sub-domain presets -> OpenAlex search queries.

Each preset is just a good default search string. The user can always edit the
query box, but these seed reproducible sub-fields that tend to have public
datasets and beatable journal baselines.
"""
from __future__ import annotations

PRESETS = [
    {"key": "medimg",  "label": "Medical imaging / diagnosis",
     "query": "deep learning medical image classification diagnosis"},
    {"key": "tabular", "label": "Tabular / classical ML classification",
     "query": "machine learning classification tabular clinical data"},
    {"key": "nlp",     "label": "NLP text classification / sentiment",
     "query": "deep learning text classification sentiment analysis"},
    {"key": "ts",      "label": "Time-series forecasting",
     "query": "deep learning time series forecasting prediction"},
    {"key": "ids",     "label": "Intrusion detection / network security",
     "query": "machine learning intrusion detection network security"},
    {"key": "har",     "label": "Human activity recognition (sensors)",
     "query": "deep learning human activity recognition wearable sensors"},
    {"key": "hsi",     "label": "Remote sensing / hyperspectral",
     "query": "deep learning hyperspectral image classification remote sensing"},
    {"key": "eeg",     "label": "EEG / biosignal classification",
     "query": "deep learning EEG signal classification"},
    {"key": "fraud",   "label": "Fraud / credit-risk detection",
     "query": "machine learning credit card fraud detection imbalanced"},
    {"key": "speech",  "label": "Speech / audio classification",
     "query": "deep learning speech emotion audio classification"},
]


def as_json() -> list[dict]:
    return PRESETS
