"""Save game state to disk."""

from __future__ import annotations

import contextlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:  # pragma: no cover - used for type checking only
    from .world import World


@dataclass
class LogEntry:
    command: str
    output: list[str]


class SaveManager:
    """Handle persisting the game state.

    Parameters
    ----------
    data_dir:
        Directory where the ``save.yaml`` file is stored.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.save_path = self.data_dir / "save.yaml"

    def load(self) -> dict[str, Any]:
        """Return previously saved data if available."""

        if not self.save_path.exists():
            return {}
        with open(self.save_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        log_data = data.get("log", [])
        data["log"] = [LogEntry(**entry) for entry in log_data]
        return data

    def save(self, world: World, language: str, log: list[LogEntry] | None = None) -> None:
        """Persist the current world state, language and log."""

        data = world.to_state()
        data["language"] = language
        if log:
            data["log"] = [asdict(entry) for entry in log]
        with open(self.save_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh)

    def cleanup(self) -> None:
        """Remove the save file if it exists."""

        if self.save_path.exists():
            with contextlib.suppress(OSError):
                self.save_path.unlink()


__all__ = ["SaveManager", "LogEntry"]
