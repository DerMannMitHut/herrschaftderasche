"""World representation loaded from data files."""

from pathlib import Path
from typing import Any, Dict

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - ignore missing library
    yaml = None  # type: ignore


def _simple_yaml_load(fh) -> Dict[str, Any]:
    """Very small YAML subset loader for environments without PyYAML."""
    result: Dict[str, Any] = {}
    stack: list[tuple[Dict[str, Any], int]] = [(result, -1)]
    for raw in fh:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.lstrip().partition(":")
        key = key.strip()
        value = value.strip()
        while indent <= stack[-1][1]:
            stack.pop()
        current, _ = stack[-1]
        if not value:
            new_dict: Dict[str, Any] = {}
            current[key] = new_dict
            stack.append((new_dict, indent))
        else:
            if value and value[0] in "'\"" and value[-1] == value[0]:
                value = value[1:-1]
            current[key] = value
    return result


class World:
    def __init__(self, data: Dict[str, Any]):
        self.rooms = data["rooms"]
        self.current = data["start"]

    @classmethod
    def from_file(cls, path: str | Path) -> "World":
        with open(path, encoding="utf-8") as fh:
            if yaml is not None:
                data = yaml.safe_load(fh)
            else:
                data = _simple_yaml_load(fh)
        return cls(data)

    def describe_current(self) -> str:
        room = self.rooms[self.current]
        return room["description"]

    def move(self, exit_name: str) -> bool:
        room = self.rooms[self.current]
        exits = room.get("exits", {})
        target = None
        exit_name_cf = exit_name.casefold()
        for name, dest in exits.items():
            if name.casefold() == exit_name_cf:
                target = dest
                break
        if target is not None:
            self.current = target
            return True
        return False
