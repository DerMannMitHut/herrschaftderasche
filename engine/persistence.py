"""Save game state to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING

import yaml

if TYPE_CHECKING:  # pragma: no cover - used for type checking only
    from .world import World


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

    def load(self) -> Dict[str, Any]:
        """Return previously saved data if available."""

        if not self.save_path.exists():
            return {}
        with open(self.save_path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def save(self, world: "World", language: str) -> None:
        """Persist the current world state and language."""

        data = world.to_state()
        data["language"] = language
        with open(self.save_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh)

    def cleanup(self) -> None:
        """Remove the save file if it exists."""

        if self.save_path.exists():
            self.save_path.unlink()


__all__ = ["SaveManager"]

