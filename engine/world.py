"""World representation loaded from data files."""

from pathlib import Path
from typing import Any, Dict
import sys

import yaml


class World:
    def __init__(self, data: Dict[str, Any], debug: bool = False):
        self._debug_enabled = debug
        self.rooms = data["rooms"]
        self.items = data.get("items", {})
        self.npcs = data.get("npcs", {})
        self.current = data["start"]
        self.inventory: list[str] = data.get("inventory", [])
        self.endings = data.get("endings", {})
        actions = data.get("actions", [])
        if isinstance(actions, dict):
            actions = list(actions.values())
        self.actions: list[Dict[str, Any]] = list(actions)
        self.item_states: Dict[str, str] = {
            item_id: item_data.get("state")
            for item_id, item_data in self.items.items()
            if item_data.get("state") is not None
        }
        self.npc_states: Dict[str, str] = {
            npc_id: npc_data.get("state")
            for npc_id, npc_data in self.npcs.items()
            if npc_data.get("state") is not None
        }
        self._base_rooms: Dict[str, list[str]] = {
            room_id: list(room.get("items", [])) for room_id, room in self.rooms.items()
        }
        self._base_inventory: list[str] = list(self.inventory)
        self._base_item_states: Dict[str, str] = dict(self.item_states)
        self._base_npc_states: Dict[str, str] = dict(self.npc_states)

        for room in self.rooms.values():
            exits = room.get("exits")
            if not exits:
                continue
            if isinstance(exits, list):
                room["exits"] = {e: {"names": [e]} for e in exits}
                continue
            new_exits: Dict[str, Dict[str, Any]] = {}
            for target, cfg in exits.items():
                if isinstance(cfg, list):
                    new_exits[target] = {"names": list(cfg)}
                elif isinstance(cfg, dict):
                    names = cfg.get("names", [])
                    pre = cfg.get("preconditions")
                    new_exits[target] = {"names": list(names)}
                    if pre:
                        new_exits[target]["preconditions"] = pre
                else:  # pragma: no cover - legacy single-string syntax
                    new_exits[target] = {"names": [cfg]}
            room["exits"] = new_exits

    def debug(self, message: str) -> None:
        if self._debug_enabled:
            print(f"-- {message}", file=sys.stderr)

    @classmethod
    def from_file(cls, path: str | Path, debug: bool = False) -> "World":
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        actions = data.get("actions", {})
        if isinstance(actions, dict):
            data["actions"] = list(actions.values())
        return cls(data, debug=debug)

    @classmethod
    def from_files(
        cls, config_path: str | Path, language_path: str | Path, debug: bool = False
    ) -> "World":
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
            cfg_exits = cfg_room.get("exits", {})
            if isinstance(cfg_exits, list):
                cfg_exits = {target: {} for target in cfg_exits}
            for target, exit_cfg in cfg_exits.items():
                names = lang_rooms.get(target, {}).get("names", [target])
                exit_entry: Dict[str, Any] = {"names": names}
                pre = exit_cfg.get("preconditions") if isinstance(exit_cfg, dict) else None
                if pre:
                    exit_entry["preconditions"] = pre
                exits[target] = exit_entry
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
        # Ensure items and rooms have at least default translations
        for item_id, item_cfg in items.items():
            item_cfg.setdefault("names", [item_id])
            if "description" not in item_cfg:
                item_cfg["description"] = item_id
            states = item_cfg.get("states", {})
            for state_id, state_cfg in states.items():
                state_cfg.setdefault("description", state_id)
        for room_id, room in rooms.items():
            room.setdefault("names", [room_id])
            room.setdefault("description", room_id)
        endings: Dict[str, Any] = {}
        base_endings = base.get("endings", {})
        lang_endings = lang.get("endings", {})
        for end_id, cfg_end in base_endings.items():
            ending = dict(cfg_end)
            lang_cfg = lang_endings.get(end_id)
            if isinstance(lang_cfg, dict):
                ending.update(lang_cfg)
            elif lang_cfg is not None:
                ending["description"] = lang_cfg
            endings[end_id] = ending
        actions: list[Dict[str, Any]] = []
        base_actions = base.get("actions", {})
        lang_actions = lang.get("actions", {})
        for action_id, cfg_action in base_actions.items():
            action = dict(cfg_action)
            action.update(lang_actions.get(action_id, {}))
            actions.append(action)
        npcs: Dict[str, Any] = base.get("npcs", {})
        lang_npcs = lang.get("npcs", {})
        for npc_id, npc_data in lang_npcs.items():
            npc_cfg = npcs.setdefault(npc_id, {})
            lang_states = npc_data.get("states")
            if lang_states:
                base_states = npc_cfg.setdefault("states", {})
                for state_id, state_cfg in lang_states.items():
                    base_states.setdefault(state_id, {}).update(state_cfg)
            for key, value in npc_data.items():
                if key == "states":
                    continue
                if isinstance(value, dict):
                    npc_cfg.setdefault(key, {}).update(value)
                else:
                    npc_cfg[key] = value
        data = {
            "items": items,
            "rooms": rooms,
            "start": base["start"],
            "endings": endings,
            "actions": actions,
            "npcs": npcs,
        }
        return cls(data, debug=debug)

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
        npc_states_diff: Dict[str, str] = {}
        for npc_id, cur_state in self.npc_states.items():
            if self._base_npc_states.get(npc_id) != cur_state:
                npc_states_diff[npc_id] = cur_state
        if npc_states_diff:
            state["npc_states"] = npc_states_diff
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
        npc_states = data.get("npc_states", {})
        for npc_id, state in npc_states.items():
            if npc_id in self.npc_states:
                self.npc_states[npc_id] = state
                self.npcs[npc_id]["state"] = state

    # Condition / effect handling -------------------------------------------------

    def _check_item_condition(self, cond: Dict[str, Any]) -> bool:
        item_id = cond.get("item")
        if not item_id:
            return False
        state = cond.get("state")
        if state and self.item_states.get(item_id) != state:
            return False
        location = cond.get("location")
        if location:
            if location == "INVENTORY":
                if item_id not in self.inventory:
                    return False
            else:
                if item_id not in self.rooms.get(location, {}).get("items", []):
                    return False
        return True

    def _check_npc_condition(self, cond: Dict[str, Any]) -> bool:
        npc_id = cond.get("npc")
        state = cond.get("state")
        if not npc_id or not state:
            return False
        return self.npc_state(npc_id) == state

    def check_preconditions(self, pre: Dict[str, Any] | None) -> bool:
        if not pre:
            return True
        loc = pre.get("is_location")
        if loc and self.current != loc:
            return False
        item_cond = pre.get("item_condition")
        if item_cond and not self._check_item_condition(item_cond):
            return False
        npc_met = pre.get("npc_met")
        if npc_met and not self._check_npc_condition({"npc": npc_met, "state": "met"}):
            return False
        npc_help = pre.get("npc_help")
        if npc_help and not self._check_npc_condition({"npc": npc_help, "state": "helped"}):
            return False
        npc_cond = pre.get("npc_state")
        if npc_cond and not self._check_npc_condition(npc_cond):
            return False
        npc_conditions = pre.get("npc_condition")
        if npc_conditions:
            if isinstance(npc_conditions, dict):
                npc_conditions = [npc_conditions]
            for cond in npc_conditions:
                if not self._check_npc_condition(cond):
                    return False
        return True

    def apply_item_condition(self, cond: Dict[str, Any]) -> None:
        item_id = cond.get("item")
        if not item_id:
            return
        state = cond.get("state")
        if state:
            self.set_item_state(item_id, state)
        location = cond.get("location")
        if location:
            if location == "CURRENT_ROOM":
                location = self.current
            if item_id in self.inventory:
                self.inventory.remove(item_id)
                self.debug(f"inventory {self.inventory}")
            for room_id, room in self.rooms.items():
                items = room.get("items", [])
                if item_id in items:
                    items.remove(item_id)
                    self.debug(f"room {room_id} items {items}")
            if location == "INVENTORY":
                self.inventory.append(item_id)
                self.debug(f"inventory {self.inventory}")
            else:
                self.rooms.setdefault(location, {}).setdefault("items", []).append(item_id)
                items = self.rooms[location].get("items", [])
                self.debug(f"room {location} items {items}")

    def apply_effect(self, effect: Dict[str, Any]) -> None:
        item_cond = effect.get("item_condition") or effect.get("item_conditions")
        if item_cond:
            if isinstance(item_cond, dict):
                item_cond = [item_cond]
            for cond in item_cond:
                self.apply_item_condition(cond)
        add_exit = effect.get("add_exit")
        if add_exit:
            if isinstance(add_exit, dict):
                add_exit = [add_exit]
            for cfg in add_exit:
                room = cfg.get("room")
                target = cfg.get("target")
                pre = cfg.get("preconditions")
                if room and target:
                    self.add_exit(room, target, pre)

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
        room_npcs = [
            npc.get("names", [npc_id])[0]
            for npc_id, npc in self.npcs.items()
            if npc.get("meet", {}).get("location") == self.current
        ]
        if room_npcs:
            if messages:
                desc += " " + messages["npcs_here"].format(npcs=", ".join(room_npcs))
            else:  # pragma: no cover - fallback without messages
                desc += " You see here: " + ", ".join(room_npcs)
        exits = room.get("exits", {})
        if exits:
            exit_names = []
            for cfg in exits.values():
                names = cfg.get("names", [])
                if names:
                    exit_names.append(names[0])
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
        for target, cfg in exits.items():
            names = cfg.get("names", [])
            if any(name.casefold() == exit_name_cf for name in names):
                self.current = target
                self.debug(f"location {self.current}")
                return True
        return False

    def can_move(self, exit_name: str) -> bool:
        room = self.rooms[self.current]
        exits = room.get("exits", {})
        exit_name_cf = exit_name.casefold()
        for cfg in exits.values():
            names = cfg.get("names", [])
            if any(name.casefold() == exit_name_cf for name in names):
                pre = cfg.get("preconditions")
                return self.check_preconditions(pre)
        return False

    def add_exit(
        self, room_id: str, target: str, pre: Dict[str, Any] | None = None
    ) -> None:
        room = self.rooms.setdefault(room_id, {})
        exits = room.setdefault("exits", {})
        names = self.rooms.get(target, {}).get("names", [target])
        exits[target] = {"names": names}
        if pre:
            exits[target]["preconditions"] = pre

    def take(self, item_name: str) -> str | None:
        """Move an item from the current room into the inventory.

        Returns the canonical item name if the item was taken, otherwise ``None``.
        """
        room = self.rooms[self.current]
        items = room.get("items", [])
        item_name_cf = item_name.casefold()
        for item_id in list(items):
            names = self.items.get(item_id, {}).get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                items.remove(item_id)
                self.inventory.append(item_id)
                self.debug(f"room {self.current} items {items}")
                self.debug(f"inventory {self.inventory}")
                if names:
                    return names[0]
                return item_name
        return None

    def drop(self, item_name: str) -> bool:
        item_name_cf = item_name.casefold()
        for item_id in list(self.inventory):
            names = self.items.get(item_id, {}).get("names", [])
            if any(name.casefold() == item_name_cf for name in names):
                self.inventory.remove(item_id)
                room = self.rooms[self.current]
                room.setdefault("items", []).append(item_id)
                self.debug(f"inventory {self.inventory}")
                self.debug(f"room {self.current} items {room['items']}")
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
        self.debug(f"item {item_id} state {state}")
        return True

    def set_npc_state(self, npc_id: str, state: str) -> bool:
        """Set the state for an NPC if the state exists.

        Returns True if the state was changed, False otherwise."""
        npc = self.npcs.get(npc_id)
        if not npc:
            return False
        states = npc.get("states")
        if not states or state not in states:
            return False
        self.npc_states[npc_id] = state
        npc["state"] = state
        self.debug(f"npc {npc_id} state {state}")
        return True

    def meet_npc(self, npc_id: str) -> bool:
        """Mark an NPC as met if a corresponding state exists."""
        npc = self.npcs.get(npc_id)
        if not npc:
            return False
        states = npc.get("states", {})
        if "met" not in states:
            return False
        self.npc_states[npc_id] = "met"
        npc["state"] = "met"
        self.debug(f"npc {npc_id} state met")
        return True

    def npc_state(self, npc_id: str) -> str | None:
        """Return the current state of an NPC."""
        return self.npc_states.get(npc_id)

    def describe_inventory(self, messages: Dict[str, str]) -> str:
        if not self.inventory:
            return messages["inventory_empty"]
        item_names = [self.items[i]["names"][0] for i in self.inventory]
        return messages["inventory_items"].format(items=", ".join(item_names))

    def check_endings(self) -> str | None:
        for ending in self.endings.values():
            pre = ending.get("preconditions")
            if self.check_preconditions(pre):
                return ending.get("description")
        return None
