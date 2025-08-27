"""World representation loaded from data files."""

from pathlib import Path
from typing import Any, Dict, Callable

import yaml
import re


def _compile_condition(expr: str) -> Callable[["World"], bool]:
    expr_cf = expr.casefold()
    expr_cf = re.sub(r"\band\b", " and ", expr_cf)
    expr_cf = re.sub(r"\bor\b", " or ", expr_cf)
    expr_cf = re.sub(r"at ([a-z0-9_]+)", r'(self.current == "\1")', expr_cf)
    expr_cf = re.sub(r"inventory has ([a-z0-9_]+)", r'("\1" in self.inventory)', expr_cf)
    expr_cf = re.sub(
        r"inventory lacks ([a-z0-9_]+)", r'("\1" not in self.inventory)', expr_cf
    )
    expr_cf = re.sub(
        r"([a-z0-9_]+) has ([a-z0-9_]+)",
        r'("\2" in self.rooms.get("\1", {}).get("items", []))',
        expr_cf,
    )
    expr_cf = re.sub(
        r"([a-z0-9_]+) lacks ([a-z0-9_]+)",
        r'("\2" not in self.rooms.get("\1", {}).get("items", []))',
        expr_cf,
    )
    expr_cf = re.sub(
        r"([a-z0-9_]+) is ([a-z0-9_]+)",
        r'(self.item_states.get("\1") == "\2")',
        expr_cf,
    )
    code = compile(expr_cf, "<condition>", "eval")

    def func(world: "World") -> bool:
        return bool(eval(code, {}, {"self": world}))

    return func


class World:
    def __init__(self, data: Dict[str, Any]):
        self.rooms = data["rooms"]
        self.items = data.get("items", {})
        self.current = data["start"]
        self.inventory: list[str] = data.get("inventory", [])
        self.endings = data.get("endings", {})
        self.uses: list[Dict[str, Any]] = data.get("uses", [])
        for ending in self.endings.values():
            cond = ending.get("condition")
            if cond:
                ending["check"] = _compile_condition(cond)
        self.item_states: Dict[str, str] = {
            item_id: item_data.get("state")
            for item_id, item_data in self.items.items()
            if item_data.get("state") is not None
        }
        self._base_rooms: Dict[str, list[str]] = {
            room_id: list(room.get("items", [])) for room_id, room in self.rooms.items()
        }
        self._base_inventory: list[str] = list(self.inventory)
        self._base_item_states: Dict[str, str] = dict(self.item_states)

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
            item_cfg = items.setdefault(item_id, {})
            lang_states = item_data.get("states")
            if lang_states:
                base_states = item_cfg.setdefault("states", {})
                for state_id, state_cfg in lang_states.items():
                    base_states.setdefault(state_id, {}).update(state_cfg)
            for key, value in item_data.items():
                if key != "states":
                    item_cfg[key] = value
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
        endings: Dict[str, Any] = {}
        for end_id, cond in base.get("endings", {}).items():
            endings[end_id] = {"condition": cond}
        for end_id, desc in lang.get("endings", {}).items():
            endings.setdefault(end_id, {})["description"] = desc
        uses: list[Dict[str, Any]] = []
        base_uses = base.get("uses", {})
        lang_uses = lang.get("uses", {})
        for use_id, cfg_use in base_uses.items():
            use = dict(cfg_use)
            use.update(lang_uses.get(use_id, {}))
            uses.append(use)
        data = {
            "items": items,
            "rooms": rooms,
            "start": base["start"],
            "endings": endings,
            "uses": uses,
        }
        return cls(data)

    def to_state(self) -> Dict[str, Any]:
        """Return the minimal state describing differences from the base world."""
        state: Dict[str, Any] = {"current": self.current}
        if self.inventory != self._base_inventory:
            state["inventory"] = self.inventory
        rooms_diff: Dict[str, list[str]] = {}
        for room_id, room in self.rooms.items():
            items = list(room.get("items", []))
            base_items = self._base_rooms.get(room_id, [])
            if items != base_items:
                rooms_diff[room_id] = items
        if rooms_diff:
            state["rooms"] = rooms_diff
        states_diff: Dict[str, str] = {}
        for item_id, cur_state in self.item_states.items():
            if self._base_item_states.get(item_id) != cur_state:
                states_diff[item_id] = cur_state
        if states_diff:
            state["item_states"] = states_diff
        return state

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_state(), fh)

    def load_state(self, path: str | Path) -> None:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        self.current = data.get("current", self.current)
        # Only override inventory if it was stored; otherwise keep base inventory.
        self.inventory = data.get("inventory", self.inventory)
        room_items = data.get("rooms", {})
        for room_id, room in self.rooms.items():
            items = room_items.get(room_id)
            if items is None:
                continue
            if items:
                room["items"] = items
            else:
                room.pop("items", None)
        item_states = data.get("item_states", {})
        for item_id, state in item_states.items():
            if item_id in self.item_states:
                self.item_states[item_id] = state
                self.items[item_id]["state"] = state

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
        exits = room.get("exits", {})
        if exits:
            exit_names = []
            for names in exits.values():
                if isinstance(names, list):
                    exit_names.append(names[0])
                else:  # pragma: no cover - legacy single-string syntax
                    exit_names.append(names)
            if messages:
                desc += " " + messages["exits"].format(exits=", ".join(exit_names))
            else:  # pragma: no cover - fallback without messages
                desc += " Exits: " + ", ".join(exit_names)
        return desc

    def describe_item(self, item_name: str) -> str | None:
        item_name_cf = item_name.casefold()
        room = self.rooms[self.current]
        for item_id in room.get("items", []):
            item = self.items.get(item_id, {})
            names = item.get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                state = self.item_states.get(item_id)
                if state:
                    desc = item.get("states", {}).get(state, {}).get("description")
                    if desc is not None:
                        return desc
                return item.get("description")
        for item_id in self.inventory:
            item = self.items.get(item_id, {})
            names = item.get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                state = self.item_states.get(item_id)
                if state:
                    desc = item.get("states", {}).get(state, {}).get("description")
                    if desc is not None:
                        return desc
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

    def set_item_state(self, item_id: str, state: str) -> bool:
        """Set the state for an item if the state exists.

        Returns True if the state was changed, False otherwise."""
        item = self.items.get(item_id)
        if not item:
            return False
        states = item.get("states")
        if not states or state not in states:
            return False
        self.item_states[item_id] = state
        item["state"] = state
        return True

    def describe_inventory(self, messages: Dict[str, str]) -> str:
        if not self.inventory:
            return messages["inventory_empty"]
        item_names = [self.items[i]["names"][0] for i in self.inventory]
        return messages["inventory_items"].format(items=", ".join(item_names))

    def check_endings(self) -> str | None:
        for ending in self.endings.values():
            check = ending.get("check")
            if check and check(self):
                return ending.get("description")
        return None
