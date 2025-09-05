"""World representation loaded from data files."""

import inspect
import os
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

import yaml

from .world_model import Action, Item, LocationTag, Npc, Room, StateTag


def _convert_tags(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _convert_tags(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_tags(v) for v in obj]
    if isinstance(obj, str):
        if obj in LocationTag._value2member_map_:
            return LocationTag(obj)
        if obj in StateTag._value2member_map_:
            return StateTag(obj)
    return obj


def _normalize_room_config(room: dict[str, Any]) -> dict[str, Any]:
    """Normalize room configuration for pydantic validation."""
    exits = room.get("exits")
    if not exits:
        return room
    if isinstance(exits, list):
        room["exits"] = {e: {"names": [e]} for e in exits}
        return room
    new_exits: dict[str, dict[str, Any]] = {}
    for target, cfg in exits.items():
        if isinstance(cfg, list):
            new_exits[target] = {"names": list(cfg)}
        elif isinstance(cfg, dict):
            names = cfg.get("names", [])
            pre = cfg.get("preconditions")
            entry = {"names": list(names)}
            if pre:
                entry["preconditions"] = pre
            raw_dur = cfg.get("duration")
            if raw_dur is not None:
                with suppress(Exception):  # pragma: no cover - non-int durations ignored
                    entry["duration"] = int(raw_dur)  # type: ignore[arg-type]
            new_exits[target] = entry
        else:  # pragma: no cover - legacy single-string syntax
            new_exits[target] = {"names": [cfg]}
    room["exits"] = new_exits
    return room


class World:
    def __init__(self, data: dict[str, Any], debug: bool = False):
        data = _convert_tags(data)
        self._debug_enabled = debug
        raw_rooms = data.get("rooms", {})
        raw_items = data.get("items", {})
        raw_npcs = data.get("npcs", {})
        processed_rooms: dict[str, Room] = {}
        for room_id, room in raw_rooms.items():
            if isinstance(room, Room):
                processed_rooms[room_id] = room
            else:
                cfg = _normalize_room_config(dict(room))
                processed_rooms[room_id] = Room(**cfg)
        self.rooms = processed_rooms
        self.items = {item_id: item if isinstance(item, Item) else Item(**item) for item_id, item in raw_items.items()}
        self.npcs = {npc_id: npc if isinstance(npc, Npc) else Npc(**npc) for npc_id, npc in raw_npcs.items()}
        self.current = data["start"]
        self.inventory: list[str] = data.get("inventory", [])
        self.endings = data.get("endings", {})
        self.intro = data.get("intro", "")
        actions = data.get("actions", [])
        if isinstance(actions, dict):
            actions = list(actions.values())
        normalized: list[Any] = []
        for action in actions:
            if isinstance(action, dict):
                action = dict(action)
                if "precondition" in action and "preconditions" not in action:
                    action["preconditions"] = action.pop("precondition")
            normalized.append(action)
        self.actions = [act if isinstance(act, Action) else Action(**act) for act in normalized]
        # Time management: TU (time units); default start at 0
        self.time: int = int(data.get("time", 0) or 0)
        self.item_states: dict[str, str | StateTag] = {
            item_id: item_data.state for item_id, item_data in self.items.items() if item_data.state is not None
        }
        self.npc_states: dict[str, str | StateTag] = {
            npc_id: npc_data.state for npc_id, npc_data in self.npcs.items() if npc_data.state is not None
        }
        self._base_rooms: dict[str, list[str]] = {room_id: list(room.items) for room_id, room in self.rooms.items()}
        self._base_exits: dict[str, set[str]] = {room_id: set(room.exits.keys()) for room_id, room in self.rooms.items()}
        self._base_inventory: list[str] = list(self.inventory)
        self._base_item_states: dict[str, str | StateTag] = dict(self.item_states)
        self._base_npc_states: dict[str, str | StateTag] = dict(self.npc_states)
        for npc_id, npc in self.npcs.items():
            loc = npc.meet.get("location")
            if loc and loc in self.rooms:
                room = self.rooms[loc]
                room.occupants.append(npc_id)

    # --- item naming helpers (state-aware) ---
    def item_names(self, item_id: str) -> list[str]:
        item = self.items.get(item_id)
        if not item:
            return []
        base = list(item.names or [])
        st = item.state
        if isinstance(st, StateTag):
            st = st.value
        if st:
            st_cfg = (item.states or {}).get(st, {})
            st_names = st_cfg.get("names") if isinstance(st_cfg, dict) else None
            if st_names:
                try:
                    return list(st_names)
                except Exception:
                    return base
        return base

    def debug(self, message: str) -> None:
        if self._debug_enabled:
            frame = inspect.stack()[1]
            filename = os.path.basename(frame.filename)
            lineno = frame.lineno
            print(f"{filename}:{lineno} -- {message}", file=sys.stderr)

    @classmethod
    def from_files(cls, config_path: str | Path, language_path: str | Path, debug: bool = False) -> "World":
        with open(config_path, encoding="utf-8") as fh:
            base = yaml.safe_load(fh)
        with open(language_path, encoding="utf-8") as fh:
            lang = yaml.safe_load(fh)
        items: dict[str, Any] = base.get("items", {})
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
        rooms: dict[str, Any] = {}
        lang_rooms = lang.get("rooms", {})
        for room_id, cfg_room in base.get("rooms", {}).items():
            room: dict[str, Any] = {}
            if cfg_room.get("items"):
                room["items"] = list(cfg_room["items"])
            exits: dict[str, Any] = {}
            cfg_exits = cfg_room.get("exits", {})
            if isinstance(cfg_exits, list):
                cfg_exits = {target: {} for target in cfg_exits}
            for target, exit_cfg in cfg_exits.items():
                names = lang_rooms.get(target, {}).get("names", [target])
                exit_entry: dict[str, Any] = {"names": names}
                pre = exit_cfg.get("preconditions") if isinstance(exit_cfg, dict) else None
                if pre:
                    exit_entry["preconditions"] = pre
                if isinstance(exit_cfg, dict):
                    raw_dur2 = exit_cfg.get("duration")
                    if raw_dur2 is not None:
                        with suppress(Exception):  # pragma: no cover - non-int durations ignored
                            exit_entry["duration"] = int(raw_dur2)  # type: ignore[arg-type]
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
            # Optional language-specific article for movement phrases
            to_article = lang_room.get("to_article")
            if to_article is not None:
                room["to_article"] = to_article
            rooms[room_id] = room
        for item_id, item_cfg in items.items():
            item_cfg.setdefault("names", [item_id])
            if "description" not in item_cfg:
                item_cfg["description"] = item_id
            # Optional language-specific forms and articles for items
            lang_item = lang.get("items", {}).get(item_id, {})
            forms = lang_item.get("forms")
            if isinstance(forms, dict):
                item_cfg["forms"] = dict(forms)
            articles = lang_item.get("articles")
            if isinstance(articles, dict):
                item_cfg["articles"] = dict(articles)
            states = item_cfg.get("states", {})
            for state_id, state_cfg in states.items():
                state_cfg.setdefault("description", state_id)
        for room_id, room in rooms.items():
            room.setdefault("names", [room_id])
            room.setdefault("description", room_id)
            # Optional forms and move marker for rooms
            lang_room = lang_rooms.get(room_id, {})
            forms = lang_room.get("forms")
            if isinstance(forms, dict):
                room["forms"] = dict(forms)
            move_marker = lang_room.get("move_marker")
            if isinstance(move_marker, dict):
                room["move_marker"] = dict(move_marker)
        endings: dict[str, Any] = {}
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
        actions: list[dict[str, Any]] = []
        base_actions = base.get("actions", {})
        lang_actions = lang.get("actions", {})
        for action_id, cfg_action in base_actions.items():
            action = dict(cfg_action)
            action.update(lang_actions.get(action_id, {}))
            precond = action.pop("precondition", None)
            if precond is not None and "preconditions" not in action:
                action["preconditions"] = precond
            actions.append(action)
        npcs: dict[str, Any] = base.get("npcs", {})
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
                if key == "dialog" and isinstance(value, dict):
                    base_dialog = npc_cfg.setdefault("dialog", {})
                    for node_id, node_cfg in value.items():
                        base_node = base_dialog.setdefault(node_id, {})
                        text = node_cfg.get("text")
                        if text is not None:
                            base_node["text"] = text
                        lang_opts = node_cfg.get("options")
                        if isinstance(lang_opts, dict):
                            base_opts = base_node.setdefault("options", [])
                            if base_opts:
                                for opt in base_opts:
                                    opt_id = opt.get("id")
                                    if opt_id and opt_id in lang_opts:
                                        opt["prompt"] = lang_opts[opt_id]
                            else:
                                for opt_id, prompt in lang_opts.items():
                                    base_opts.append({"id": opt_id, "prompt": prompt})
                    continue
                if isinstance(value, dict):
                    npc_cfg.setdefault(key, {}).update(value)
                else:
                    npc_cfg[key] = value
        items = _convert_tags(items)
        rooms = _convert_tags(rooms)
        endings = _convert_tags(endings)
        actions = [_convert_tags(a) for a in actions]
        npcs = _convert_tags(npcs)

        # Parse optional start_time from base world config ("HH:MM" or minutes)
        start_time = base.get("start_time")
        start_time_minutes: int | None = None
        if isinstance(start_time, int):
            start_time_minutes = start_time
        elif isinstance(start_time, str) and ":" in start_time:
            try:
                hh, mm = start_time.split(":", 1)
                start_time_minutes = (int(hh) % 24) * 60 + (int(mm) % 60)
            except Exception:
                start_time_minutes = None

        data = {
            "items": {item_id: Item(**cfg) for item_id, cfg in items.items()},
            "rooms": {room_id: Room(**cfg) for room_id, cfg in rooms.items()},
            "start": base["start"],
            "endings": endings,
            "actions": [Action(**a) for a in actions],
            "npcs": {npc_id: Npc(**cfg) for npc_id, cfg in npcs.items()},
            "intro": lang.get("intro", ""),
        }
        if start_time_minutes is not None:
            data["time"] = start_time_minutes
        return cls(data, debug=debug)

    def to_state(self) -> dict[str, Any]:
        """Return the minimal state describing differences from the base world."""
        state: dict[str, Any] = {"current": self.current}
        if self.inventory != self._base_inventory:
            state["inventory"] = self.inventory
        rooms_diff: dict[str, list[str]] = {}
        for room_id, room in self.rooms.items():
            items = list(room.items)
            base_items = self._base_rooms.get(room_id, [])
            if items != base_items:
                rooms_diff[room_id] = items
        if rooms_diff:
            state["rooms"] = rooms_diff
        exits_added: dict[str, dict[str, Any]] = {}
        for room_id, room in self.rooms.items():
            base_exits = self._base_exits.get(room_id, set())
            added: dict[str, Any] = {}
            for target, cfg in room.exits.items():
                if target not in base_exits:
                    pre = cfg.get("preconditions")
                    dur = cfg.get("duration")
                    entry: dict[str, Any] = {}
                    if pre:
                        entry["preconditions"] = pre
                    if dur is not None:
                        entry["duration"] = int(dur)
                    added[target] = entry
            if added:
                exits_added[room_id] = added
        if exits_added:
            state["exits"] = exits_added
        states_diff: dict[str, str] = {}
        for item_id, cur_state in self.item_states.items():
            if self._base_item_states.get(item_id) != cur_state:
                val = cur_state.value if isinstance(cur_state, StateTag) else cur_state
                states_diff[item_id] = val
        if states_diff:
            state["item_states"] = states_diff
        npc_states_diff: dict[str, str] = {}
        for npc_id, cur_state in self.npc_states.items():
            if self._base_npc_states.get(npc_id) != cur_state:
                val = cur_state.value if isinstance(cur_state, StateTag) else cur_state
                npc_states_diff[npc_id] = val
        if npc_states_diff:
            state["npc_states"] = npc_states_diff
        # Persist time only if progressed
        if self.time:
            state["time"] = int(self.time)
        return state

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_state(), fh)

    def load_state(self, path: str | Path) -> None:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        self.current = data.get("current", self.current)
        self.inventory = data.get("inventory", self.inventory)
        room_items = data.get("rooms", {})
        for room_id, room in self.rooms.items():
            items = room_items.get(room_id)
            if items is None:
                continue
            if items:
                room.items = items
            else:
                room.items = []
        exits_added = data.get("exits", {})
        for room_id, mapping in exits_added.items():
            for target, cfg in (mapping or {}).items():
                pre = cfg.get("preconditions") if isinstance(cfg, dict) else None
                dur = cfg.get("duration") if isinstance(cfg, dict) else None
                self.add_exit(room_id, target, pre, int(dur) if dur is not None else None)
        item_states = data.get("item_states", {})
        for item_id, state in item_states.items():
            if item_id in self.item_states:
                val = StateTag(state) if isinstance(state, str) and state in StateTag._value2member_map_ else state
                self.item_states[item_id] = val
                self.items[item_id].state = val
        npc_states = data.get("npc_states", {})
        for npc_id, state in npc_states.items():
            if npc_id in self.npc_states:
                val = StateTag(state) if isinstance(state, str) and state in StateTag._value2member_map_ else state
                self.npc_states[npc_id] = val
                self.npcs[npc_id].state = val
        # time restore
        time_val = data.get("time")
        if isinstance(time_val, int):
            self.time = int(time_val)

    def _check_item_condition(self, cond: dict[str, Any]) -> bool:
        item_id = cond.get("item")
        if not item_id:
            return False
        state = cond.get("state")
        if state is not None:
            expected = state.value if isinstance(state, StateTag) else state
            current = self.item_states.get(item_id)
            if isinstance(current, StateTag):
                current = current.value
            if current != expected:
                return False
        location = cond.get("location")
        if location:
            if location is LocationTag.INVENTORY:
                if item_id not in self.inventory:
                    return False
            elif location is LocationTag.CURRENT_ROOM:
                room = self.rooms.get(self.current)
                if not room or item_id not in room.items:
                    return False
            else:
                room_id = location
                room = self.rooms.get(room_id)
                if not room or item_id not in room.items:
                    return False
        return True

    def _check_npc_condition(self, cond: dict[str, Any]) -> bool:
        npc_id = cond.get("npc")
        state = cond.get("state")
        if not npc_id or state is None:
            return False
        return self.npc_state(npc_id) == state

    def check_preconditions(self, pre: dict[str, Any] | None) -> bool:
        if not pre:
            return True
        loc = pre.get("is_location")
        if loc and self.current != (loc.value if isinstance(loc, LocationTag) else loc):
            return False
        item_cond = pre.get("item_conditions")
        if item_cond:
            for ic in item_cond:
                if not self._check_item_condition(ic):
                    return False
        npc_met = pre.get("npc_met")
        if npc_met and not self._check_npc_condition({"npc": npc_met, "state": StateTag.MET}):
            return False
        npc_help = pre.get("npc_help")
        if npc_help and not self._check_npc_condition({"npc": npc_help, "state": StateTag.HELPED}):
            return False
        npc_state = pre.get("npc_state")
        if npc_state and not self._check_npc_condition(npc_state):
            return False
        npc_conditions = pre.get("npc_conditions")
        if npc_conditions:
            for nc in npc_conditions:
                if not self._check_npc_condition(nc):
                    return False
        return True

    def apply_item_condition(self, cond: dict[str, Any]) -> None:
        item_id = cond.get("item")
        if not item_id:
            return
        state = cond.get("state")
        if state is not None:
            self.set_item_state(item_id, state)
        location = cond.get("location")
        if location:
            if location is LocationTag.CURRENT_ROOM:
                location = self.current
            if item_id in self.inventory:
                self.inventory.remove(item_id)
                self.debug(f"inventory {self.inventory}")
            for room_id, room in self.rooms.items():
                items = room.items
                if item_id in items:
                    items.remove(item_id)
                    self.debug(f"room {room_id} items {items}")
            if location is LocationTag.INVENTORY:
                self.inventory.append(item_id)
                self.debug(f"inventory {self.inventory}")
            else:
                room_id = location
                room = self.rooms.setdefault(room_id, Room(names=[], description=""))
                room.items.append(item_id)
                self.debug(f"room {room_id} items {room.items}")

    def apply_npc_condition(self, cond: dict[str, Any]) -> None:
        npc_id = cond.get("npc")
        if not npc_id:
            return
        state = cond.get("state")
        if state is not None:
            self.set_npc_state(npc_id, state)
        location = cond.get("location")
        if location:
            if location is LocationTag.CURRENT_ROOM:
                location = self.current
            self.move_npc(npc_id, location)

    def apply_effect(self, effect: dict[str, Any] | None) -> None:
        if not effect:
            return
        item_cond = effect.get("item_conditions")
        if item_cond:
            for cond in item_cond:
                self.apply_item_condition(cond)
        npc_cond = effect.get("npc_conditions")
        if npc_cond:
            for cond in npc_cond:
                self.apply_npc_condition(cond)
        add_exit = effect.get("add_exits")
        if add_exit:
            for cfg in add_exit:
                room = cfg.get("room")
                target = cfg.get("target")
                pre = cfg.get("preconditions")
                if pre is not None and not isinstance(pre, dict):
                    raise TypeError("preconditions must be a mapping")
                if room and target:
                    duration = cfg.get("duration")
                    self.add_exit(room, target, pre, int(duration) if duration is not None else None)

    def describe_current(self, messages: dict[str, str] | None = None) -> str:
        header = self.describe_room_header(messages)
        visible = self.describe_visibility()
        return header if not visible else f"{header} {visible}"

    def describe_room_header(self, messages: dict[str, str] | None = None) -> str:
        """Return only the room description and exits, with sorted exits.

        Does not include items/NPCs to allow callers to control output order.
        """
        room = self.rooms[self.current]
        desc = room.description
        exits = room.exits
        if exits:
            exit_names = []
            for cfg in exits.values():
                names = cfg.get("names", [])
                if names:
                    exit_names.append(names[0])
            exit_names.sort(key=lambda s: s.casefold())
            if messages:
                desc += " " + messages["exits"].format(exits=", ".join(exit_names))
            else:  # pragma: no cover - fallback ohne messages
                desc += " Exits: " + ", ".join(exit_names)
        return desc

    def format_time(self) -> str:
        minutes = int(self.time) % 1440
        hh = minutes // 60
        mm = minutes % 60
        return f"{hh:02d}:{mm:02d}"

    def describe_visibility(self, messages: dict[str, str] | None = None) -> str | None:
        """Return a single consolidated 'You see here: ...' line for items and NPCs.

        Returns None if there is nothing visible.
        """
        room = self.rooms[self.current]
        names: list[str] = []
        for item_id in room.items:
            item = self.items.get(item_id)
            if item:
                eff = self.item_names(item_id)
                if eff:
                    names.append(eff[0])
        for npc_id in room.occupants:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            pre = npc.meet.get("preconditions")
            if pre and not self.check_preconditions(pre):
                continue
            if npc.names:
                names.append(npc.names[0])
        if not names:
            return None
        names.sort(key=lambda s: s.casefold())
        if messages and "you_see_here" in messages:
            return messages["you_see_here"].format(list=", ".join(names))
        return "You see here: " + ", ".join(names) + "."

    def describe_item(self, item_name: str) -> str | None:
        item_name_cf = item_name.casefold()
        room = self.rooms[self.current]
        for item_id in room.items:
            item = self.items.get(item_id)
            if not item:
                continue
            names = self.item_names(item_id)
            if any(name.casefold() == item_name_cf for name in names):
                state = self.item_states.get(item_id)
                if state:
                    state_key = state.value if isinstance(state, StateTag) else state
                    desc = item.states.get(state_key, {}).get("description")
                    if desc is not None:
                        return desc
                return item.description
        for item_id in self.inventory:
            item = self.items.get(item_id)
            if not item:
                continue
            names = self.item_names(item_id)
            if any(name.casefold() == item_name_cf for name in names):
                state = self.item_states.get(item_id)
                if state:
                    state_key = state.value if isinstance(state, StateTag) else state
                    desc = item.states.get(state_key, {}).get("description")
                    if desc is not None:
                        return desc
                return item.description
        return None

    def describe_npc(self, npc_name: str) -> str | None:
        """Return a description for an NPC in the current room.

        Preference order:
        - state-specific "examine" text if available
        - state-specific "text" fallback
        - None if NPC not present or no description
        """
        npc_name_cf = npc_name.casefold()
        room = self.rooms[self.current]
        for npc_id in room.occupants:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            # respect meet preconditions (visibility)
            pre = npc.meet.get("preconditions")
            if pre and not self.check_preconditions(pre):
                continue
            names = npc.names or []
            if not any(name.casefold() == npc_name_cf for name in names):
                continue
            state = self.npc_state(npc_id)
            state_key = state.value if isinstance(state, StateTag) else state
            cfg = (npc.states or {}).get(state_key or "", {})
            # Prefer explicit examine description, fallback to generic text
            desc = cfg.get("examine") or cfg.get("text")
            return desc
        return None

    def move(self, exit_name: str) -> bool:
        room = self.rooms[self.current]
        exits = room.exits
        exit_name_cf = exit_name.casefold()
        for target, cfg in exits.items():
            names = cfg.get("names", [])
            if any(name.casefold() == exit_name_cf for name in names):
                self.current = target
                self.debug(f"location {self.current}")
                return True
        return False

    def has_room(self, name: str) -> bool:
        if not name:
            return False
        name_cf = name.casefold()
        for room in self.rooms.values():
            room_names_cf = (n.casefold() for n in room.names)
            if name_cf in room_names_cf:
                return True
        return False

    def can_move(self, exit_name: str) -> bool:
        room = self.rooms[self.current]
        exits = room.exits
        exit_name_cf = exit_name.casefold()
        for cfg in exits.values():
            names = cfg.get("names", [])
            if any(name.casefold() == exit_name_cf for name in names):
                pre = cfg.get("preconditions")
                return self.check_preconditions(pre)
        return False

    def add_exit(self, room_id: str, target: str, pre: dict[str, Any] | None = None, duration: int | None = None) -> None:
        room = self.rooms.setdefault(room_id, Room(names=[], description=""))
        exits = room.exits
        target_room = self.rooms.get(target)
        names = target_room.names if target_room else [target]
        exits[target] = {"names": names}
        if pre:
            exits[target]["preconditions"] = pre
        if duration is not None:
            exits[target]["duration"] = int(duration)
        self.debug(f"add_exit {room_id}->{target}")

    # --- time management helpers ---
    def get_exit_duration(self, exit_name: str) -> int:
        room = self.rooms[self.current]
        exit_name_cf = exit_name.casefold()
        for cfg in room.exits.values():
            names = cfg.get("names", [])
            if any(name.casefold() == exit_name_cf for name in names):
                dur = cfg.get("duration")
                return int(dur) if isinstance(dur, int) else 1
        return 1

    def advance_time(self, units: int) -> None:
        if units and units > 0:
            self.time = (self.time + int(units)) % 1440
            self.debug(f"time +{units} -> {self.time}")

    def take(self, item_name: str) -> str | None:
        """Move an item from the current room into the inventory.

        Returns the canonical item name if the item was taken, otherwise ``None``.
        """
        room = self.rooms[self.current]
        items = room.items
        item_name_cf = item_name.casefold()
        for item_id in list(items):
            names = self.item_names(item_id)
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
            names = self.item_names(item_id)
            if any(name.casefold() == item_name_cf for name in names):
                self.inventory.remove(item_id)
                room = self.rooms[self.current]
                room.items.append(item_id)
                self.debug(f"inventory {self.inventory}")
                self.debug(f"room {self.current} items {room.items}")
                return True
        return False

    def add_npc_to_location(self, npc_id: str, location: str) -> None:
        room = self.rooms.setdefault(location, Room(names=[], description=""))
        if npc_id not in room.occupants:
            room.occupants.append(npc_id)

    def remove_npc_from_location(self, npc_id: str, location: str | None) -> None:
        if not location:
            return
        room = self.rooms.get(location)
        if room and npc_id in room.occupants:
            room.occupants.remove(npc_id)

    def move_npc(self, npc_id: str, location: str) -> None:
        if npc_id not in self.npcs:
            return
        for room in self.rooms.values():
            if npc_id in room.occupants:
                room.occupants.remove(npc_id)
                break
        self.add_npc_to_location(npc_id, location)

    def set_item_state(self, item_id: str, state: str) -> bool:
        """Set the state for an item if the state exists.

        Returns True if the state was changed, False otherwise."""
        item = self.items.get(item_id)
        if not item:
            return False
        states = item.states
        if not states or state not in states:
            return False
        self.item_states[item_id] = state
        item.state = state
        self.debug(f"item {item_id} state {state}")
        return True

    def set_npc_state(self, npc_id: str, state: str | StateTag) -> bool:
        """Set the state for an NPC if the state exists.

        Returns True if the state was changed, False otherwise."""
        npc = self.npcs.get(npc_id)
        if not npc:
            return False
        states = npc.states
        state_key = state.value if isinstance(state, StateTag) else state
        if not states or state_key not in states:
            return False
        value = StateTag(state_key) if state_key in StateTag._value2member_map_ else state_key
        self.npc_states[npc_id] = value
        npc.state = value
        self.debug(f"npc {npc_id} state {state_key}")
        return True

    def meet_npc(self, npc_id: str) -> bool:
        """Mark an NPC as met only if it was unknown."""
        npc = self.npcs.get(npc_id)
        if not npc:
            return False
        state = self.npc_states.get(npc_id)
        if state != "unknown":
            return False
        states = npc.states
        if StateTag.MET.value not in states:
            return False
        self.npc_states[npc_id] = StateTag.MET
        npc.state = StateTag.MET
        self.debug(f"npc {npc_id} state {StateTag.MET.value}")
        return True

    def npc_state(self, npc_id: str) -> str | StateTag | None:
        """Return the current state of an NPC."""
        return self.npc_states.get(npc_id)

    def describe_inventory(self, messages: dict[str, str]) -> str:
        if not self.inventory:
            return messages["inventory_empty"]
        item_names: list[str] = []
        for i in self.inventory:
            names = self.item_names(i)
            if names:
                item_names.append(names[0])
            else:
                item = self.items.get(i)
                item_names.append(item.names[0] if item and item.names else i)
        return messages["inventory_items"].format(items=", ".join(item_names))

    def check_endings(self) -> str | None:
        for ending in self.endings.values():
            pre = ending.get("preconditions")
            if self.check_preconditions(pre):
                return ending.get("description")
        return None
