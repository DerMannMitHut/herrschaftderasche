"""Integrity checks for game data and save files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from . import world
from .world_model import CommandCategory, LocationTag, StateTag


def check_translations(language: str, data_dir: Path) -> list[str]:
    """Check translation files for completeness and report warnings.

    Returns a list of warning messages."""

    warnings: list[str] = []

    base_messages_path = data_dir / "en" / "messages.en.yaml"
    lang_messages_path = data_dir / language / f"messages.{language}.yaml"
    if base_messages_path.exists() and lang_messages_path.exists():
        with open(base_messages_path, encoding="utf-8") as fh:
            base_msgs = yaml.safe_load(fh) or {}
        with open(lang_messages_path, encoding="utf-8") as fh:
            lang_msgs = yaml.safe_load(fh) or {}
        for key in base_msgs:
            if key not in lang_msgs:
                warnings.append(f"Missing translation for message '{key}'")
        for key in lang_msgs:
            if key not in base_msgs:
                warnings.append(f"Unused message translation '{key}' ignored")

    base_cmds_path = data_dir / "generic" / "commands.yaml"
    lang_cmds_path = data_dir / language / f"commands.{language}.yaml"
    if base_cmds_path.exists() and lang_cmds_path.exists():
        with open(base_cmds_path, encoding="utf-8") as fh:
            base_cmd_keys = yaml.safe_load(fh) or []
        with open(lang_cmds_path, encoding="utf-8") as fh:
            lang_cmds = yaml.safe_load(fh) or {}
        for key in base_cmd_keys:
            if key not in lang_cmds:
                warnings.append(f"Missing translation for command '{key}'")
        for key in lang_cmds:
            if key not in base_cmd_keys:
                warnings.append(f"Unused command translation '{key}' ignored")

        # Validate command categories (must exist and be one of the enum values)
        try:
            allowed = {c.value for c in CommandCategory}
        except Exception:
            allowed = {"system", "basics", "actions"}
        for key, cfg in base_cmd_keys.items() if isinstance(base_cmd_keys, dict) else []:
            if not isinstance(cfg, dict):
                warnings.append(f"Command '{key}' definition must be a mapping")
                continue
            category = cfg.get("category")
            if not category:
                warnings.append(f"Command '{key}' missing category")
            elif category not in allowed:
                warnings.append(f"Command '{key}' has invalid category '{category}' (allowed: {', '.join(sorted(allowed))})")

    base_world_path = data_dir / "generic" / "world.yaml"
    lang_world_path = data_dir / language / f"world.{language}.yaml"
    if base_world_path.exists() and lang_world_path.exists():
        with open(base_world_path, encoding="utf-8") as fh:
            base_world = yaml.safe_load(fh) or {}
        with open(lang_world_path, encoding="utf-8") as fh:
            lang_world = yaml.safe_load(fh) or {}
        base_items = base_world.get("items", {})
        lang_items = lang_world.get("items", {})
        for item_id in base_items:
            if item_id not in lang_items:
                warnings.append(f"Missing translation for item '{item_id}'")
        for item_id in lang_items:
            if item_id not in base_items:
                warnings.append(f"Translation for unused item '{item_id}' ignored")
        base_rooms = base_world.get("rooms", {})
        lang_rooms = lang_world.get("rooms", {})
        for room_id in base_rooms:
            if room_id not in lang_rooms:
                warnings.append(f"Missing translation for room '{room_id}'")
        for room_id in lang_rooms:
            if room_id not in base_rooms:
                warnings.append(f"Translation for unused room '{room_id}' ignored")
        base_actions = base_world.get("actions", {})
        lang_actions = lang_world.get("actions", {})
        for action_id in base_actions:
            if action_id not in lang_actions:
                warnings.append(f"Missing translation for action '{action_id}'")
        for action_id in lang_actions:
            if action_id not in base_actions:
                warnings.append(f"Translation for unused action '{action_id}' ignored")

    return warnings


def validate_world_structure(w: world.World) -> list[str]:
    """Validate cross references inside the world and return error messages."""

    errors: list[str] = []

    for room_id, room in w.rooms.items():
        exits = room.get("exits", {})
        for target, cfg in exits.items():
            if target not in w.rooms:
                errors.append(f"Room '{room_id}' has exit to missing room '{target}'")
            # validate optional exit duration
            if isinstance(cfg, dict):
                dur = cfg.get("duration")
                if dur is not None and (not isinstance(dur, int) or dur < 1):
                    errors.append(f"Room '{room_id}' exit to '{target}' has invalid duration '{dur}' (must be positive integer)")
        for item in room.get("items", []):
            if item not in w.items:
                errors.append(f"Room '{room_id}' contains missing item '{item}'")

    if w.current not in w.rooms:
        errors.append(f"Start room '{w.current}' does not exist")

    for action in w.actions:
        # action duration validation (if provided)
        act_dur = action.get("duration")
        if act_dur is not None and (not isinstance(act_dur, int) or act_dur < 1):
            errors.append(f"Action '{action}' has invalid duration '{act_dur}' (must be positive integer)")
        item = action.get("item")
        if item not in w.items:
            errors.append(f"Action '{action}' references missing item '{item}'")
        target_item = action.get("target_item")
        if target_item and target_item not in w.items:
            errors.append(f"Action '{action}' references missing target item '{target_item}'")
        target_npc = action.get("target_npc")
        if target_npc and target_npc not in w.npcs:
            errors.append(f"Action '{action}' references missing target NPC '{target_npc}'")
        pre = action.get("preconditions") or {}
        loc = pre.get("is_location")
        if loc and loc not in w.rooms:
            errors.append(f"Action '{action}' precondition references missing room '{loc}'")
        conds = pre.get("item_conditions") or []
        for cond in conds:
            cond_item = cond.get("item")
            if cond_item and cond_item not in w.items:
                errors.append(f"Action '{action}' precondition references missing item '{cond_item}'")
            cond_loc = cond.get("location")
            if cond_loc:
                if isinstance(cond_loc, LocationTag):
                    if cond_loc is not LocationTag.INVENTORY and cond_loc.value not in w.rooms:
                        errors.append(f"Action '{action}' precondition references missing location '{cond_loc.value}'")
                elif cond_loc not in w.rooms:
                    errors.append(f"Action '{action}' precondition references missing location '{cond_loc}'")
        npc_conds = pre.get("npc_conditions") or []
        for cond in npc_conds:
            cond_npc = cond.get("npc")
            if cond_npc and cond_npc not in w.npcs:
                errors.append(f"Action '{action}' precondition references missing NPC '{cond_npc}'")
            cond_state = cond.get("state")
            if cond_npc and cond_state:
                state_key = cond_state.value if isinstance(cond_state, StateTag) else cond_state
                if state_key not in w.npcs.get(cond_npc, {}).get("states", {}):
                    errors.append(f"Action '{action}' precondition references missing state '{state_key}' for NPC '{cond_npc}'")
        eff = action.get("effect") or {}
        conds = eff.get("item_conditions") or []
        for cond in conds:
            eff_item = cond.get("item")
            if eff_item and eff_item not in w.items:
                errors.append(f"Action '{action}' effect references missing item '{eff_item}'")
            eff_state = cond.get("state")
            if eff_item and eff_state and eff_state not in w.items.get(eff_item, {}).get("states", {}):
                errors.append(f"Action '{action}' effect references missing state '{eff_state}' for item '{eff_item}'")
            eff_loc = cond.get("location")
            if eff_loc:
                if isinstance(eff_loc, LocationTag):
                    if eff_loc is not LocationTag.INVENTORY and eff_loc.value not in w.rooms:
                        errors.append(f"Action '{action}' effect references missing location '{eff_loc.value}'")
                elif eff_loc not in w.rooms:
                    errors.append(f"Action '{action}' effect references missing location '{eff_loc}'")
        npc_conds = eff.get("npc_conditions") or []
        for cond in npc_conds:
            cond_npc = cond.get("npc")
            if cond_npc and cond_npc not in w.npcs:
                errors.append(f"Action '{action}' effect references missing NPC '{cond_npc}'")
            cond_state = cond.get("state")
            if cond_npc and cond_state:
                state_key = cond_state.value if isinstance(cond_state, StateTag) else cond_state
                if state_key not in w.npcs.get(cond_npc, {}).get("states", {}):
                    errors.append(f"Action '{action}' effect references missing state '{state_key}' for NPC '{cond_npc}'")
            cond_loc = cond.get("location")
            if cond_loc:
                if isinstance(cond_loc, LocationTag):
                    if cond_loc is not LocationTag.CURRENT_ROOM and cond_loc.value not in w.rooms:
                        errors.append(f"Action '{action}' effect references missing location '{cond_loc.value}'")
                elif cond_loc not in w.rooms:
                    errors.append(f"Action '{action}' effect references missing location '{cond_loc}'")
        add_exits = eff.get("add_exits") or []
        for cfg in add_exits:
            room = cfg.get("room")
            target = cfg.get("target")
            if room and room not in w.rooms:
                errors.append(f"Action '{action}' effect references missing room '{room}' for add_exits")
            if target and target not in w.rooms:
                errors.append(f"Action '{action}' effect references missing target room '{target}' for add_exits")
            dur = cfg.get("duration")
            if dur is not None and (not isinstance(dur, int) or dur < 1):
                errors.append(
                    f"Action '{action}' effect add_exits has invalid duration '{dur}' for {room}->{target} (must be positive integer)"
                )
            pre = cfg.get("preconditions")
            if pre is not None:
                if isinstance(pre, list):
                    errors.append("Action '{action}' effect exit precondition must be a mapping")
                    pre = None
                if pre:
                    loc = pre.get("is_location")
                    if loc and loc not in w.rooms:
                        errors.append(f"Action '{{action}}' effect exit precondition references missing room '{loc}'")
                    conds = pre.get("item_conditions") or []
                    for cond in conds:
                        cond_item = cond.get("item")
                        if cond_item and cond_item not in w.items:
                            errors.append(f"Action '{{action}}' effect exit precondition references missing item '{cond_item}'")

    for npc_id, npc in w.npcs.items():
        meet = npc.get("meet", {})
        loc = meet.get("location")
        if loc and loc not in w.rooms:
            errors.append(f"NPC '{npc_id}' references missing room '{loc}'")
        state = npc.get("state")
        state_key = state.value if isinstance(state, StateTag) else state
        if state_key and state_key not in npc.get("states", {}):
            errors.append(f"NPC '{npc_id}' has undefined state '{state_key}'")

    for end_id, ending in w.endings.items():
        pre = ending.get("preconditions") or {}
        if isinstance(pre, list):
            errors.append(f"Ending '{end_id}' preconditions must be a mapping")
            pre = {}
        loc = pre.get("is_location")
        if loc and loc not in w.rooms:
            errors.append(f"Ending '{end_id}' precondition references missing room '{loc}'")
        conds = pre.get("item_conditions") or []
        for cond in conds:
            cond_item = cond.get("item")
            if cond_item and cond_item not in w.items:
                errors.append(f"Ending '{end_id}' references missing item '{cond_item}'")
            cond_loc = cond.get("location")
            if cond_loc:
                if isinstance(cond_loc, LocationTag):
                    if cond_loc is not LocationTag.INVENTORY and cond_loc.value not in w.rooms:
                        errors.append(f"Ending '{end_id}' references missing location '{cond_loc.value}'")
                elif cond_loc not in w.rooms:
                    errors.append(f"Ending '{end_id}' references missing location '{cond_loc}'")
            state = cond.get("state")
            if cond_item and state and state not in w.items.get(cond_item, {}).get("states", {}):
                errors.append(f"Ending '{end_id}' references missing state '{state}' for item '{cond_item}'")
        npc_conds = pre.get("npc_conditions") or []
        for cond in npc_conds:
            cond_npc = cond.get("npc")
            if cond_npc and cond_npc not in w.npcs:
                errors.append(f"Ending '{end_id}' references missing NPC '{cond_npc}'")
            cond_state = cond.get("state")
            if cond_npc and cond_state:
                state_key = cond_state.value if isinstance(cond_state, StateTag) else cond_state
                if state_key not in w.npcs.get(cond_npc, {}).get("states", {}):
                    errors.append(f"Ending '{end_id}' references missing state '{state_key}' for NPC '{cond_npc}'")

    return errors


def validate_save(data: dict[str, Any], w: world.World) -> list[str]:
    """Validate that a save file only references existing data."""

    errors: list[str] = []

    cur = data.get("current")
    if cur and cur not in w.rooms:
        errors.append(f"Save references missing room '{cur}'")

    for item_id in data.get("inventory", []):
        if item_id not in w.items:
            errors.append(f"Save references missing item '{item_id}' in inventory")

    for room_id, items in data.get("rooms", {}).items():
        if room_id not in w.rooms:
            errors.append(f"Save references missing room '{room_id}'")
        else:
            for item_id in items or []:
                if item_id not in w.items:
                    errors.append(f"Save references missing item '{item_id}' in room '{room_id}'")

    for item_id, state in data.get("item_states", {}).items():
        if item_id not in w.items:
            errors.append(f"Save references missing item '{item_id}' in item_states")
        else:
            states = w.items.get(item_id, {}).get("states", {})
            if state not in states:
                errors.append(f"Save references missing state '{state}' for item '{item_id}'")

    for npc_id, state in data.get("npc_states", {}).items():
        if npc_id not in w.npcs:
            errors.append(f"Save references missing NPC '{npc_id}' in npc_states")
        else:
            states = w.npcs.get(npc_id, {}).get("states", {})
            if state not in states:
                errors.append(f"Save references missing state '{state}' for NPC '{npc_id}'")

    return errors
