"""Configuration loading and derived lookups."""
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"


def _load(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> "Config":
    return Config(
        settings=_load("settings.yaml"),
        journals=_load("journals.yaml"),
        categories=_load("categories.yaml")["categories"],
    )


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

    def top_n(self, category: dict) -> int:
        return int(category.get("top_n", self.settings["default_top_n"]))
