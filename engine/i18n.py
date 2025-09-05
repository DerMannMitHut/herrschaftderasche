"""Simple translation loader."""

from pathlib import Path

import yaml

from .interfaces import IOBackend


def _load_yaml(path: Path, io: IOBackend) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError as exc:
        io.output(f"ERROR: Missing file '{path.name}'")
        raise SystemExit from exc
    except yaml.YAMLError as exc:
        io.output(f"ERROR: Invalid YAML in '{path.name}': {exc}")
        raise SystemExit from exc


def load_messages(language: str, io: IOBackend) -> dict[str, str]:
    """Load translation messages for the given language code."""
    path = Path(__file__).resolve().parent.parent / "data" / language / f"messages.{language}.yaml"
    return _load_yaml(path, io)


def load_commands(language: str, io: IOBackend) -> dict[str, str | list[str]]:
    """Load command translations for the given language code."""
    path = Path(__file__).resolve().parent.parent / "data" / language / f"commands.{language}.yaml"
    return _load_yaml(path, io)


def load_llm_config(language: str, io: IOBackend) -> dict:
    """Load LLM configuration for the given language code."""
    path = Path(__file__).resolve().parent.parent / "data" / language / f"llm.{language}.yaml"
    return _load_yaml(path, io) or {}


def load_command_info(io: IOBackend) -> dict[str, dict[str, int]]:
    """Return metadata about the available commands."""
    path = Path(__file__).resolve().parent.parent / "data" / "generic" / "commands.yaml"
    return _load_yaml(path, io)
