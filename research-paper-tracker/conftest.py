"""Ensures `import src...` / `import gui...` work under pytest regardless of how
it's invoked (`pytest`, `python -m pytest`, from this dir or elsewhere)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
