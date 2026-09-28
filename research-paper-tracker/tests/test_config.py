import pytest

from src.config import ConfigError, Config, _validate, load_config


def _minimal_settings():
    return {
        "contact_email": "x@example.com", "refresh_interval_days": 7, "lookback_days": 7,
        "lag_margin_days": 2, "max_lookback_days": 60, "default_top_n": 10,
        "db_path": "data/tracker.db", "output_dir": "data/out",
        "openalex_per_page": 200, "openalex_max_pages": 1, "crossref_rows": 10,
        "arxiv_page_size": 10, "arxiv_max_pages": 1, "request_timeout": 30,
        "openalex_delay": 0.1, "arxiv_delay": 0.1, "arxiv_tier": 4, "unknown_venue_tier": 9,
    }


def _minimal_category(**overrides):
    cat = {"key": "k1", "label": "K1", "feeds": [], "require_all": [], "exclude": []}
    cat.update(overrides)
    return cat


def test_load_config_on_real_files_succeeds():
    cfg = load_config()
    assert cfg.categories
    assert cfg.top_n({"key": "x"}) == cfg.settings["default_top_n"]


def test_validate_rejects_missing_setting():
    settings = _minimal_settings()
    del settings["contact_email"]
    with pytest.raises(ConfigError, match="contact_email"):
        _validate(settings, {"areas": {}}, [_minimal_category()])


def test_validate_rejects_missing_category_key():
    cat = _minimal_category()
    del cat["feeds"]
    with pytest.raises(ConfigError, match="feeds"):
        _validate(_minimal_settings(), {"areas": {}}, [cat])


def test_validate_rejects_duplicate_category_key():
    with pytest.raises(ConfigError, match="duplicate"):
        _validate(_minimal_settings(), {"areas": {}}, [_minimal_category(), _minimal_category()])


def test_validate_rejects_bad_group():
    with pytest.raises(ConfigError, match="group"):
        _validate(_minimal_settings(), {"areas": {}}, [_minimal_category(group="not_a_group")])


def test_validate_accepts_valid_group():
    _validate(_minimal_settings(), {"areas": {}}, [_minimal_category(group="nbd")])


def test_validate_rejects_feed_missing_source():
    cat = _minimal_category(feeds=[{"mode": "keyword", "query": "x"}])
    with pytest.raises(ConfigError, match="feed"):
        _validate(_minimal_settings(), {"areas": {}}, [cat])


def test_category_group_lookup():
    cfg = Config(_minimal_settings(), {"areas": {}},
                 [_minimal_category(group="causal"), _minimal_category(key="k2")])
    assert cfg.category_group("k1") == "causal"
    assert cfg.category_group("k2") is None
    assert cfg.category_group("missing") is None
