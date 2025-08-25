"""World representation loaded from data files."""

from pathlib import Path
from typing import Any, Dict

import yaml


class World:
    def __init__(self, data: Dict[str, Any]):
        self.rooms = data["rooms"]
        self.current = data["start"]

    @classmethod
    def from_file(cls, path: str | Path) -> "World":
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls(data)

    def describe_current(self) -> str:
        room = self.rooms[self.current]
        return room["description"]

    def move(self, exit_name: str) -> bool:
        room = self.rooms[self.current]
        exits = room.get("exits", {})
        exit_name_cf = exit_name.casefold()
        for target, names in exits.items():
            if isinstance(names, list):
                name_list = names
            else:  # pragma: no cover - legacy single-string syntax
                name_list = [names]
            if any(name.casefold() == exit_name_cf for name in name_list):
                self.current = target
                return True
        return False
