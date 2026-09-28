from src import citations

SAMPLE_BIB = r"""
@article{bachmann2021,
  title   = {The Role of Time-Varying Contextual Factors in Latent
             Attrition Models},
  author  = {Bachmann, Patrick and Meierer, Markus and N{\"a}f, Jeffrey},
  journal = {Marketing Science},
  year    = {2021},
  doi     = {10.1287/mksc.2020.1254}
}

@article{kubota2026,
  author  = {Kubota, Kohsuke and Takahashi, Mitsuhiro and Saito, Yuta},
  title   = {Off-Policy Evaluation and Learning for Survival Outcomes under Censoring},
  journal = {arXiv preprint}, note = {arXiv:2603.22900}, year = {2026}
}

@article{noidnote,
  title  = {A Paper With No Doi Or Arxiv Id},
  author = {Someone, S.},
  year   = {2020}
}
"""


def test_parse_bib_extracts_key_and_fields(tmp_path):
    p = tmp_path / "refs.bib"
    p.write_text(SAMPLE_BIB, encoding="utf-8")
    entries = {e["key"]: e for e in citations.parse_bib(p)}
    assert set(entries) == {"bachmann2021", "kubota2026", "noidnote"}
    assert entries["bachmann2021"]["doi"] == "10.1287/mksc.2020.1254"
    assert "Latent" in entries["bachmann2021"]["title"]
    assert "arXiv:2603.22900" in entries["kubota2026"]["note"]


def test_bibindex_matches_by_doi(tmp_path):
    p = tmp_path / "refs.bib"
    p.write_text(SAMPLE_BIB, encoding="utf-8")
    idx = citations.BibIndex(citations.parse_bib(p))
    assert idx.match("10.1287/mksc.2020.1254", None, None) == "bachmann2021"
    assert idx.match("https://doi.org/10.1287/mksc.2020.1254", None, None) == "bachmann2021"
    assert idx.match("10.9999/not-in-bib", None, None) is None


def test_bibindex_matches_by_arxiv_id(tmp_path):
    p = tmp_path / "refs.bib"
    p.write_text(SAMPLE_BIB, encoding="utf-8")
    idx = citations.BibIndex(citations.parse_bib(p))
    assert idx.match(None, "2603.22900", None) == "kubota2026"
    assert idx.match(None, "1234.56789", None) is None


def test_bibindex_falls_back_to_normalized_title(tmp_path):
    p = tmp_path / "refs.bib"
    p.write_text(SAMPLE_BIB, encoding="utf-8")
    idx = citations.BibIndex(citations.parse_bib(p))
    # No doi/arxiv on this tracked record, but the title matches (modulo case/punct).
    assert idx.match(None, None, "A Paper With No Doi Or Arxiv Id") == "noidnote"


def test_load_index_missing_path_returns_none():
    assert citations.load_index(None) is None


def test_normalize_title_strips_latex_noise():
    assert citations.normalize_title("The {Achilles} Heel of {\\it Predictive} Analytics") == \
        "the achilles heel of it predictive analytics"
