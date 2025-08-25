"""Simple translation loader."""

from pathlib import Path
from typing import Dict

import yaml


def load_messages(language: str) -> Dict[str, str]:
    """Load translation messages for the given language code."""
    path = (
        Path(__file__).resolve().parent.parent / "data" / language / "messages.yaml"
    )
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
