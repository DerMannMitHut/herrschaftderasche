"""Integrity checks for game data and save files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from . import world


def check_translations(language: str, data_dir: Path) -> List[str]:
    """Check translation files for completeness and report warnings.

    Returns a list of warning messages."""

    warnings: List[str] = []

    # Messages ---------------------------------------------------------------
    base_messages_path = data_dir / "en" / "messages.yaml"
    lang_messages_path = data_dir / language / "messages.yaml"
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

    # Commands ---------------------------------------------------------------
    base_cmds_path = data_dir / "generic" / "commands.yaml"
    lang_cmds_path = data_dir / language / "commands.yaml"
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

    # World translations -----------------------------------------------------
    base_world_path = data_dir / "generic" / "world.yaml"
    lang_world_path = data_dir / language / "world.yaml"
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
                warnings.append(
                    f"Missing translation for action '{action_id}'"
                )
        for action_id in lang_actions:
            if action_id not in base_actions:
                warnings.append(
                    f"Translation for unused action '{action_id}' ignored"
                )

    return warnings


def validate_world_structure(w: world.World) -> List[str]:
    """Validate cross references inside the world and return error messages."""

    errors: List[str] = []

    # Rooms, exits and items -------------------------------------------------
    for room_id, room in w.rooms.items():
        exits = room.get("exits", {})
        for target in exits:
            if target not in w.rooms:
                errors.append(
                    f"Room '{room_id}' has exit to missing room '{target}'"
                )
        for item in room.get("items", []):
            if item not in w.items:
                errors.append(
                    f"Room '{room_id}' contains missing item '{item}'"
                )

    # Start room -------------------------------------------------------------
    if w.current not in w.rooms:
        errors.append(f"Start room '{w.current}' does not exist")

    # Actions ----------------------------------------------------------------
    for action in w.actions:
        trigger = action.get("trigger")
        if not trigger:
            errors.append("Action missing trigger")
        if trigger != "use":
            continue
        item = action.get("item")
        if item and item not in w.items:
            errors.append(f"Action references missing item '{item}'")
        target_item = action.get("target_item")
        if target_item and target_item not in w.items:
            errors.append(
                f"Action references missing target item '{target_item}'"
            )
        pre = action.get("preconditions", {})
        loc = pre.get("is_location")
        if loc and loc not in w.rooms:
            errors.append(
                f"Action precondition references missing room '{loc}'"
            )
        cond = pre.get("item_condition", {})
        cond_item = cond.get("item")
        if cond_item and cond_item not in w.items:
            errors.append(
                f"Action precondition references missing item '{cond_item}'"
            )
        cond_loc = cond.get("location")
        if cond_loc and cond_loc != "INVENTORY" and cond_loc not in w.rooms:
            errors.append(
                f"Action precondition references missing location '{cond_loc}'"
            )
        eff = action.get("effect", {}).get("item_condition", [])
        if isinstance(eff, dict):
            eff = [eff]
        for cond in eff:
            eff_item = cond.get("item")
            if eff_item and eff_item not in w.items:
                errors.append(
                    f"Action effect references missing item '{eff_item}'"
                )
            eff_state = cond.get("state")
            if eff_item and eff_state and eff_state not in w.items.get(eff_item, {}).get("states", {}):
                errors.append(
                    f"Action effect references missing state '{eff_state}' for item '{eff_item}'"
                )
            eff_loc = cond.get("location")
            if eff_loc and eff_loc != "INVENTORY" and eff_loc not in w.rooms:
                errors.append(
                    f"Action effect references missing location '{eff_loc}'"
                )

    # NPCs -------------------------------------------------------------------
    for npc_id, npc in w.npcs.items():
        meet = npc.get("meet", {})
        loc = meet.get("location")
        if loc and loc not in w.rooms:
            errors.append(
                f"NPC '{npc_id}' references missing room '{loc}'"
            )
        state = npc.get("state")
        if state and state not in npc.get("states", {}):
            errors.append(
                f"NPC '{npc_id}' has undefined state '{state}'"
            )

    # Endings ----------------------------------------------------------------
    for end_id, ending in w.endings.items():
        pre = ending.get("preconditions", {})
        loc = pre.get("is_location")
        if loc and loc not in w.rooms:
            errors.append(
                f"Ending '{end_id}' precondition references missing room '{loc}'"
            )
        cond = pre.get("item_condition", {})
        cond_item = cond.get("item")
        if cond_item and cond_item not in w.items:
            errors.append(
                f"Ending '{end_id}' references missing item '{cond_item}'"
            )
        cond_loc = cond.get("location")
        if cond_loc and cond_loc != "INVENTORY" and cond_loc not in w.rooms:
            errors.append(
                f"Ending '{end_id}' references missing location '{cond_loc}'"
            )
        state = cond.get("state")
        if cond_item and state and state not in w.items.get(cond_item, {}).get("states", {}):
            errors.append(
                f"Ending '{end_id}' references missing state '{state}' for item '{cond_item}'"
            )

    return errors


def validate_save(data: Dict[str, Any], w: world.World) -> List[str]:
    """Validate that a save file only references existing data."""

    errors: List[str] = []

    cur = data.get("current")
    if cur and cur not in w.rooms:
        errors.append(f"Save references missing room '{cur}'")

    for item_id in data.get("inventory", []):
        if item_id not in w.items:
            errors.append(
                f"Save references missing item '{item_id}' in inventory"
            )

    for room_id, items in data.get("rooms", {}).items():
        if room_id not in w.rooms:
            errors.append(
                f"Save references missing room '{room_id}'"
            )
        else:
            for item_id in items or []:
                if item_id not in w.items:
                    errors.append(
                        f"Save references missing item '{item_id}' in room '{room_id}'"
                    )

    for item_id, state in data.get("item_states", {}).items():
        if item_id not in w.items:
            errors.append(
                f"Save references missing item '{item_id}' in item_states"
            )
        else:
            states = w.items.get(item_id, {}).get("states", {})
            if state not in states:
                errors.append(
                    f"Save references missing state '{state}' for item '{item_id}'"
                )

    for npc_id, state in data.get("npc_states", {}).items():
        if npc_id not in w.npcs:
            errors.append(
                f"Save references missing NPC '{npc_id}' in npc_states"
            )
        else:
            states = w.npcs.get(npc_id, {}).get("states", {})
            if state not in states:
                errors.append(
                    f"Save references missing state '{state}' for NPC '{npc_id}'"
                )

    return errors
