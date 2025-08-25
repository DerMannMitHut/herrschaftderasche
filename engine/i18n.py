"""Simple translation loader."""

from pathlib import Path
from typing import Dict

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - ignore missing library
    yaml = None  # type: ignore


def _simple_yaml_load(fh) -> Dict[str, str]:
    """Very small YAML subset loader for environments without PyYAML."""
    result: Dict[str, str] = {}
    for raw in fh:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value and value[0] in "'\"" and value[-1] == value[0]:
            value = value[1:-1]
        result[key] = value
    return result


def load_messages(language: str) -> Dict[str, str]:
    """Load translation messages for the given language code."""
    path = Path(__file__).resolve().parent.parent / "data" / language / "messages.yaml"
    with open(path, encoding="utf-8") as fh:
        if yaml is not None:
            return yaml.safe_load(fh)
        return _simple_yaml_load(fh)
