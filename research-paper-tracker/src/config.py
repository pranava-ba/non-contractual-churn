"""Configuration loading, validation, and derived lookups."""
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

REQUIRED_SETTINGS = [
    "contact_email", "refresh_interval_days", "lookback_days", "lag_margin_days",
    "max_lookback_days", "default_top_n", "db_path", "output_dir",
    "openalex_per_page", "openalex_max_pages", "crossref_rows",
    "arxiv_page_size", "arxiv_max_pages", "request_timeout",
    "openalex_delay", "arxiv_delay", "arxiv_tier", "unknown_venue_tier",
]
REQUIRED_CATEGORY_KEYS = ["key", "label", "feeds", "require_all", "exclude"]
VALID_GROUPS = {"nbd", "causal"}


class ConfigError(ValueError):
    """A malformed config file. Raised before any API call, so a typo never
    burns quota or aborts mid-run."""


def _load(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate(settings: dict, journals: dict, categories: list) -> None:
    missing = [k for k in REQUIRED_SETTINGS if k not in settings]
    if missing:
        raise ConfigError(f"settings.yaml is missing required key(s): {missing}")

    if not categories:
        raise ConfigError("categories.yaml has no categories")
    seen_keys: set[str] = set()
    for i, cat in enumerate(categories):
        missing = [k for k in REQUIRED_CATEGORY_KEYS if k not in cat]
        if missing:
            raise ConfigError(f"categories.yaml entry #{i} ({cat.get('key','?')}) "
                              f"is missing required key(s): {missing}")
        if cat["key"] in seen_keys:
            raise ConfigError(f"categories.yaml: duplicate category key '{cat['key']}'")
        seen_keys.add(cat["key"])
        group = cat.get("group")
        if group is not None and group not in VALID_GROUPS:
            raise ConfigError(f"categories.yaml: category '{cat['key']}' has "
                              f"group={group!r}, expected one of {sorted(VALID_GROUPS)}")
        for feed in cat["feeds"]:
            if "source" not in feed or "mode" not in feed:
                raise ConfigError(f"categories.yaml: category '{cat['key']}' has a feed "
                                  f"missing 'source'/'mode': {feed}")

    for area, area_journals in journals.get("areas", {}).items():
        for j in area_journals:
            if "issn" not in j or "tier" not in j or "name" not in j:
                raise ConfigError(f"journals.yaml: area '{area}' has an entry "
                                  f"missing name/issn/tier: {j}")


def load_config() -> "Config":
    settings = _load("settings.yaml")
    journals = _load("journals.yaml")
    categories = _load("categories.yaml")["categories"]
    _validate(settings, journals, categories)
    return Config(settings=settings, journals=journals, categories=categories)


class Config:
    def __init__(self, settings: dict, journals: dict, categories: list):
        self.settings = settings
        self.categories = categories
        self._areas = journals["areas"]

        # issn -> tier / name, and the set of "broad" venues that need a sieve.
        self.issn_tier: dict[str, int] = {}
        self.issn_name: dict[str, str] = {}
        self.sieve_issns: set[str] = set()
        for area_journals in self._areas.values():
            for j in area_journals:
                issn = j["issn"].strip()
                self.issn_tier[issn] = j["tier"]
                self.issn_name[issn] = j["name"]
                if j.get("sieve"):
                    self.sieve_issns.add(issn)

    def area_journals(self, area: str) -> list[dict]:
        return self._areas[area]

    def path(self, key: str) -> Path:
        """Resolve a settings path key (db_path / output_dir) against the project root."""
        return ROOT / self.settings[key]

    def bib_path(self, group: str) -> Path | None:
        """Resolve a group's manuscript .bib file (settings.yaml: bib_files), for the
        'used' (cited-in-manuscript) auto-detect. None if not configured."""
        rel = (self.settings.get("bib_files") or {}).get(group)
        return (ROOT / rel).resolve() if rel else None

    def category_group(self, category_key: str) -> str | None:
        for c in self.categories:
            if c["key"] == category_key:
                return c.get("group")
        return None

    def top_n(self, category: dict) -> int:
        return int(category.get("top_n", self.settings["default_top_n"]))
