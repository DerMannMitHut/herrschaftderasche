"""World representation loaded from data files."""

from pathlib import Path
from typing import Any, Dict

import yaml


class World:
    def __init__(self, data: Dict[str, Any]):
        self.rooms = data["rooms"]
        self.items = data.get("items", {})
        self.current = data["start"]
        self.inventory: list[str] = data.get("inventory", [])

    @classmethod
    def from_file(cls, path: str | Path) -> "World":
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rooms": self.rooms,
            "items": self.items,
            "start": self.current,
            "inventory": self.inventory,
        }

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_dict(), fh)

    def describe_current(self, messages: Dict[str, str] | None = None) -> str:
        room = self.rooms[self.current]
        desc = room["description"]
        room_items = room.get("items", [])
        if room_items:
            item_names = [self.items[i]["names"][0] for i in room_items]
            if messages:
                desc += " " + messages["items_here"].format(items=", ".join(item_names))
            else:  # pragma: no cover - fallback without messages
                desc += " You see here: " + ", ".join(item_names)
        return desc

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

    def take(self, item_name: str) -> bool:
        room = self.rooms[self.current]
        items = room.get("items", [])
        item_name_cf = item_name.casefold()
        for item_id in list(items):
            names = self.items.get(item_id, {}).get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                items.remove(item_id)
                self.inventory.append(item_id)
                return True
        return False

    def drop(self, item_name: str) -> bool:
        item_name_cf = item_name.casefold()
        for item_id in list(self.inventory):
            names = self.items.get(item_id, {}).get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                self.inventory.remove(item_id)
                room = self.rooms[self.current]
                room.setdefault("items", []).append(item_id)
                return True
        return False

    def describe_inventory(self, messages: Dict[str, str]) -> str:
        if not self.inventory:
            return messages["inventory_empty"]
        item_names = [self.items[i]["names"][0] for i in self.inventory]
        return messages["inventory_items"].format(items=", ".join(item_names))
