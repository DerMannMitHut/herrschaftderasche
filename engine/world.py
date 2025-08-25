"""World representation loaded from data files."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - ignore missing library
    yaml = None  # type: ignore


def _simple_yaml_load(fh) -> Dict[str, Any]:
    """Very small YAML subset loader for environments without PyYAML."""
    lines = [line.rstrip("\n") for line in fh
             if line.strip() and not line.lstrip().startswith("#")]

    def parse(index: int, indent: int) -> Tuple[int, Any]:
        mapping: Dict[str, Any] = {}
        while index < len(lines):
            line = lines[index]
            current_indent = len(line) - len(line.lstrip(" "))
            if current_indent < indent:
                break
            stripped = line[current_indent:]
            if stripped.startswith("- "):
                raise ValueError("unexpected list item")
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            index += 1
            if value:
                if value[0] in "'\"" and value[-1] == value[0]:
                    value = value[1:-1]
                mapping[key] = value
            else:
                if index < len(lines):
                    next_line = lines[index]
                    next_indent = len(next_line) - len(next_line.lstrip(" "))
                    next_stripped = next_line[next_indent:]
                    if next_indent > current_indent and next_stripped.startswith("- "):
                        lst: List[str] = []
                        while index < len(lines):
                            item_line = lines[index]
                            item_indent = len(item_line) - len(item_line.lstrip(" "))
                            if item_indent < next_indent:
                                break
                            item_stripped = item_line[next_indent:]
                            if not item_stripped.startswith("- "):
                                break
                            item = item_stripped[2:].strip()
                            if item and item[0] in "'\"" and item[-1] == item[0]:
                                item = item[1:-1]
                            lst.append(item)
                            index += 1
                        mapping[key] = lst
                        continue
                index, value_dict = parse(index, current_indent + 2)
                mapping[key] = value_dict
        return index, mapping

    _, data = parse(0, 0)
    return data


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
