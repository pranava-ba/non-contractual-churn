from src import match


def test_term_compile_space_hyphen_slash_interchangeable():
    rx = match._compile_term("Pareto/NBD")
    assert rx.search("a Pareto NBD model")
    assert rx.search("a Pareto-NBD model")
    assert rx.search("a Pareto/NBD model")
    assert not rx.search("paretonbd")  # not word-boundary-joined without a separator


def test_term_compile_prefix_star():
    rx = match._compile_term("predict*")
    assert rx.search("a predictive model")
    assert rx.search("we predict churn")
    assert not rx.search("unpredictable")  # \b before "predict" fails mid-word


def test_evaluate_exclude_rejects_outright():
    groups = [[match._compile_term("churn")]]
    excludes = [match._compile_term("quantum")]
    paper = {"title": "Quantum churn model", "abstract": ""}
    assert match.evaluate(paper, groups, excludes) is None


def test_evaluate_requires_every_group():
    groups = [
        [match._compile_term("pareto/nbd")],
        [match._compile_term("churn"), match._compile_term("retention")],
    ]
    ok = {"title": "A Pareto/NBD model of churn", "abstract": ""}
    missing_second_group = {"title": "A Pareto/NBD model", "abstract": "customer purchases"}
    assert match.evaluate(ok, groups, []) is not None
    assert match.evaluate(missing_second_group, groups, []) is None


def test_evaluate_min_hits_title_counts_double():
    groups = [[match._compile_term("churn"), match._compile_term("retention")]]
    # A single term in the TITLE counts twice (title + abstract hit both score),
    # so min_hits=[2] is satisfiable by one strong title term alone.
    title_hit = {"title": "Predicting churn in retail", "abstract": "no other terms here"}
    abstract_only_one_term = {"title": "A model", "abstract": "we study churn"}
    assert match.evaluate(title_hit, groups, [], min_hits=[2]) is not None
    assert match.evaluate(abstract_only_one_term, groups, [], min_hits=[2]) is None


def test_rank_max_per_venue_backfills_to_top_n():
    papers = [
        {"tier": 1, "match_score": 5, "relevance": 0.0, "venue": "Journal A",
         "publication_date": "2024-01-01"},
        {"tier": 1, "match_score": 4, "relevance": 0.0, "venue": "Journal A",
         "publication_date": "2024-01-01"},
        {"tier": 1, "match_score": 3, "relevance": 0.0, "venue": "Journal A",
         "publication_date": "2024-01-01"},
        {"tier": 2, "match_score": 2, "relevance": 0.0, "venue": "Journal B",
         "publication_date": "2024-01-01"},
    ]
    # cap=1 per venue, top_n=3: Journal A can only contribute 1 in the first pass,
    # Journal B contributes 1, and the cap must relax to reach top_n=3.
    selected = match.rank(papers, "relevance", top_n=3, max_per_venue=1)
    assert len(selected) == 3
    venues = [p["venue"] for p in selected]
    assert venues.count("Journal A") >= 1 and venues.count("Journal B") >= 1


def test_rank_without_venue_cap_is_plain_sort():
    papers = [
        {"tier": 2, "match_score": 1, "relevance": 0.0, "venue": "X", "publication_date": ""},
        {"tier": 1, "match_score": 3, "relevance": 0.0, "venue": "X", "publication_date": ""},
    ]
    selected = match.rank(papers, "tier", top_n=2, max_per_venue=None)
    assert selected[0]["tier"] == 1
