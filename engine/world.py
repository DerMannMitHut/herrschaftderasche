"""World representation loaded from data files."""

import json
from pathlib import Path


class World:
    def __init__(self, data: dict):
        self.rooms = data["rooms"]
        self.current = data["start"]

    @classmethod
    def from_file(cls, path: str | Path) -> "World":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(data)

    def describe_current(self) -> str:
        room = self.rooms[self.current]
        return room["description"]

    def move(self, exit_name: str) -> bool:
        room = self.rooms[self.current]
        if exit_name in room.get("exits", {}):
            self.current = room["exits"][exit_name]
            return True
        return False
