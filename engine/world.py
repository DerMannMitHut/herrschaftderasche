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

    @classmethod
    def from_files(cls, config_path: str | Path, language_path: str | Path) -> "World":
        with open(config_path, encoding="utf-8") as fh:
            base = yaml.safe_load(fh)
        with open(language_path, encoding="utf-8") as fh:
            lang = yaml.safe_load(fh)
        items: Dict[str, Any] = base.get("items", {})
        for item_id, item_data in lang.get("items", {}).items():
            items.setdefault(item_id, {}).update(item_data)
        rooms: Dict[str, Any] = {}
        lang_rooms = lang.get("rooms", {})
        for room_id, cfg_room in base.get("rooms", {}).items():
            room: Dict[str, Any] = {}
            if cfg_room.get("items"):
                room["items"] = list(cfg_room["items"])
            exits: Dict[str, Any] = {}
            for target in cfg_room.get("exits", []):
                names = lang_rooms.get(target, {}).get("names", [target])
                exits[target] = names
            if exits:
                room["exits"] = exits
            lang_room = lang_rooms.get(room_id, {})
            names = lang_room.get("names")
            if names:
                room["names"] = names
            desc = lang_room.get("description")
            if desc is not None:
                room["description"] = desc
            rooms[room_id] = room
        data = {"items": items, "rooms": rooms, "start": base["start"]}
        return cls(data)

    def to_state(self) -> Dict[str, Any]:
        return {
            "current": self.current,
            "inventory": self.inventory,
            "rooms": {room_id: room.get("items", []) for room_id, room in self.rooms.items()},
        }

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_state(), fh)

    def load_state(self, path: str | Path) -> None:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        self.current = data.get("current", self.current)
        self.inventory = data.get("inventory", [])
        room_items = data.get("rooms", {})
        for room_id, room in self.rooms.items():
            items = room_items.get(room_id)
            if items is None:
                continue
            if items:
                room["items"] = items
            else:
                room.pop("items", None)

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

    def describe_item(self, item_name: str) -> str | None:
        item_name_cf = item_name.casefold()
        room = self.rooms[self.current]
        for item_id in room.get("items", []):
            item = self.items.get(item_id, {})
            names = item.get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                return item.get("description")
        for item_id in self.inventory:
            item = self.items.get(item_id, {})
            names = item.get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                return item.get("description")
        return None

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
