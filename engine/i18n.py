"""Simple translation loader."""

from pathlib import Path
from typing import Dict, List, Union

import yaml


def load_messages(language: str) -> Dict[str, str]:
    """Load translation messages for the given language code."""
    path = (
        Path(__file__).resolve().parent.parent / "data" / language / "messages.yaml"
    )
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_commands(language: str) -> Dict[str, Union[str, List[str]]]:
    """Load command translations for the given language code."""
    path = (
        Path(__file__).resolve().parent.parent / "data" / language / "commands.yaml"
    )
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_command_keys() -> List[str]:
    """Return the list of canonical command names."""
    path = Path(__file__).resolve().parent.parent / "data" / "generic" / "commands.yaml"
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
