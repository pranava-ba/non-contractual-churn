"""Regression guard against silent term-matching drift in config/categories.yaml.

This is NOT a test of real paper text (no bibliographic content is reproduced here) --
it's a set of representative title/abstract fixtures, one per live category, built
from the terminology that category's own `require_all` groups are supposed to catch
(the "should match" case) plus one adjacent near-miss each (the "should NOT match"
case: generic RFM+clustering segmentation, and contractual/telecom churn -- the exact
two noise classes that caused the real `[[paper-tracker]]` RFM scope-leak incident).

If a future categories.yaml edit accidentally narrows a term group (or a bare term
like "rfm" ends up shared across groups again), one of these should fail before it
costs another multi-day manual curation cycle to notice.
"""
from src import match
from src.config import load_config

CFG = load_config()
_CATS = {c["key"]: c for c in CFG.categories}


def _score(category_key: str, title: str, abstract: str = "") -> int | None:
    cat = _CATS[category_key]
    groups, excludes = match.compile_category(cat)
    paper = {"title": title, "abstract": abstract}
    return match.evaluate(paper, groups, excludes, cat.get("min_hits"))


def test_non_contractual_churn_catches_its_core_case():
    assert _score(
        "non_contractual_churn",
        "Predicting customer churn and retention in a non-contractual customer-base",
        "We model repeat purchase behavior and customer lifetime value.",
    ) is not None


def test_non_contractual_churn_rejects_pure_contractual_signal_alone():
    # No non-contractual/BTYD signal at all -> the first require_all group can't fire.
    assert _score(
        "non_contractual_churn",
        "A neural network for telecom subscription churn",
        "We predict subscriber churn using deep learning.",
    ) is None


def test_btyd_models_catches_model_names_only():
    assert _score(
        "btyd_models", "A new Pareto/NBD and BG/NBD latent attrition model", ""
    ) is not None


def test_clv_rfm_requires_nonco_signal_not_just_bare_rfm():
    # This IS the regression case: bare "RFM" alone must NOT be enough for clv_rfm
    # once it also carries a generic clustering/segmentation framing with no real
    # non-contractual/BTYD/transactional signal.
    assert _score(
        "clv_rfm",
        "RFM analysis for customer segmentation using k-means clustering",
        "We segment customers by recency, frequency, and monetary value.",
    ) is None


def test_clv_rfm_catches_genuine_nonco_clv_case():
    assert _score(
        "clv_rfm",
        "Customer lifetime value and RFM in a non-contractual purchase-frequency setting",
        "We use customer-base analysis to estimate lifetime value.",
    ) is not None


def test_ml_noncontractual_churn_catches_its_core_case():
    assert _score(
        "ml_noncontractual_churn",
        "Gradient boosting for non-contractual customer churn and lifetime value prediction",
        "",
    ) is not None


def test_causal_ml_uplift_catches_the_ascarza_devriendt_framing():
    # Representative of the "target on lift, not risk" framing (Ascarza 2018) and
    # the "stop predicting churn, start using uplift" pivot (Devriendt 2021) --
    # both already relied on in deep_research/CAUSAL_ML_LITERATURE.md.
    assert _score(
        "causal_ml_uplift",
        "Uplift modeling and heterogeneous treatment effects for customer retention targeting",
        "We estimate CATE using a causal forest to target marketing campaigns.",
    ) is not None


def test_causal_ml_churn_catches_prescriptive_churn_framing():
    assert _score(
        "causal_ml_churn",
        "A prescriptive analytics approach: who to target for churn retention",
        "We estimate treatment effects to identify persuadable customers via a targeting policy.",
    ) is not None


def test_offtopic_exclude_still_rejects_known_false_positive_classes():
    assert _score(
        "non_contractual_churn",
        "Remote sensing road extraction with U-Net for electricity customer demand",
        "credit scoring via quantum code",
    ) is None
