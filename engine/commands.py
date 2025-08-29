"""Command handling for the game."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, cast

from . import io, world
from .language import LanguageManager
from .persistence import SaveManager


@dataclass
class StateChange:
    state: str
    message_key: str


STATE_COMMANDS: dict[str, StateChange] = {
    "destroy": StateChange("destroyed", "destroyed"),
    "wear": StateChange("worn", "worn"),
}


@dataclass
class ActionConfig:
    trigger: str
    item_in_inventory: bool
    target_is_npc: bool
    item_missing_key: str
    target_missing_key: str
    failure_key: str


ACTION_COMMANDS: dict[str, ActionConfig] = {
    "use": ActionConfig(
        trigger="use",
        item_in_inventory=False,
        target_is_npc=False,
        item_missing_key="use_failure",
        target_missing_key="use_failure",
        failure_key="use_failure",
    ),
    "show": ActionConfig(
        trigger="show",
        item_in_inventory=True,
        target_is_npc=True,
        item_missing_key="not_carrying",
        target_missing_key="no_npc",
        failure_key="use_failure",
    ),
}


class CommandProcessor:
    """Parse and execute player commands."""

    def __init__(
        self,
        world: world.World,
        language: LanguageManager,
        saver: SaveManager,
        check_end: Callable[[], None],
        check_npc_event: Callable[[], None],
        stop: Callable[[], None],
        update_world: Callable[[world.World], None],
    ) -> None:
        self.world = world
        self.language_manager = language
        self.save_manager = saver
        self.check_end = check_end
        self.check_npc_event = check_npc_event
        self.stop = stop
        self._update_world = update_world
        self.command_info = language.command_info
        self.command_keys = list(self.command_info.keys())
        self.cmd_patterns: list[tuple[re.Pattern[str], str, str]] = []
        self.reverse_cmds: dict[str, tuple[str, str]] = {}
        self._build_cmd_patterns()

    # ------------------------------------------------------------------
    def execute(self, raw: str) -> None:
        """Execute the command contained in ``raw``."""

        for pattern, cmd_key, _ in self.cmd_patterns:
            match = pattern.fullmatch(raw)
            if not match:
                continue
            groups = match.groupdict()
            handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
            info = self.command_info.get(cmd_key, {})
            if info.get("arguments") == 2:
                a = groups.get("a", "").strip()
                b = groups.get("b", "").strip()
                two_handler = cast(Callable[[str, str], None], handler)
                two_handler(a, b)
            else:
                arg = groups.get("a", "") or groups.get("b", "") or ""
                one_handler = cast(Callable[[str], None], handler)
                one_handler(arg.strip())
            break
        else:
            self.cmd_unknown(raw)

    # ------------------------------------------------------------------
    def _build_cmd_patterns(self) -> None:
        self.cmd_patterns.clear()
        self.reverse_cmds.clear()
        for key in self.command_keys:
            val = self.language_manager.commands.get(key, [])
            entries = val if isinstance(val, list) else [val]
            for entry in entries:
                pattern, base = self._compile_command(entry)
                self.cmd_patterns.append((pattern, key, entry))
                if base not in self.reverse_cmds:
                    self.reverse_cmds[base] = (key, entry)
        self.cmd_patterns.sort(key=lambda x: len(x[0].pattern), reverse=True)
        self.reverse_cmds["language"] = ("language", "language")

    def _compile_command(self, pattern: str) -> tuple[re.Pattern[str], str]:
        tokens = pattern.split()
        placeholder_positions = [i for i, t in enumerate(tokens) if t in ("$a", "$b")]
        last_placeholder = placeholder_positions[-1] if placeholder_positions else -1
        base = None
        parts: list[str] = []
        for idx, token in enumerate(tokens):
            if token == "$a":
                part = r"(?P<a>.+)" if idx == last_placeholder else r"(?P<a>.+?)"
            elif token == "$b":
                part = r"(?P<b>.+)" if idx == last_placeholder else r"(?P<b>.+?)"
            else:
                if base is None:
                    base = token
                part = re.escape(token)
            parts.append(part)
        regex = r"^" + r"\s+".join(parts) + r"$"
        return re.compile(regex), base or pattern

    # ------------------------------------------------------------------
    def _strip_suffix(self, arg: str, suffix: str) -> str:
        if suffix and arg.endswith(f" {suffix}"):
            return arg[: -len(suffix) - 1].strip()
        return arg

    def _find_item_id(self, name: str, *, in_inventory: bool = False) -> str | None:
        if not name:
            return None
        name_cf = name.casefold()
        if not in_inventory:
            room = self.world.rooms[self.world.current]
            for item_id in room.get("items", []):
                names = self.world.items.get(item_id, {}).get("names", [])
                if any(n.casefold() == name_cf for n in names):
                    return item_id
        for item_id in self.world.inventory:
            names = self.world.items.get(item_id, {}).get("names", [])
            if any(n.casefold() == name_cf for n in names):
                return item_id
        return None

    def _find_npc_id(self, name: str) -> str | None:
        if not name:
            return None
        name_cf = name.casefold()
        for npc_id, npc in self.world.npcs.items():
            names = npc.get("names", [])
            if not any(n.casefold() == name_cf for n in names):
                continue
            if npc.get("meet", {}).get("location") != self.world.current:
                return None
            return npc_id
        return None

    def _state_command(self, cmd: str, item_name: str) -> None:
        if not item_name:
            self.cmd_unknown(item_name)
            return
        cfg = STATE_COMMANDS[cmd]
        item_id = self._find_item_id(item_name, in_inventory=True)
        if not item_id:
            io.output(self.language_manager.messages["not_carrying"])
            self.check_end()
            return
        if not self.world.set_item_state(item_id, cfg.state):
            io.output(self.language_manager.messages["use_failure"])
            self.check_end()
            return
        self.world.inventory.remove(item_id)
        self.world.debug(f"inventory {self.world.inventory}")
        io.output(self.language_manager.messages[cfg.message_key].format(item=item_name))
        self.check_end()

    def _action_command(
        self, cmd: str, item_name: str, target_name: str
    ) -> None:
        cfg = ACTION_COMMANDS[cmd]
        if not item_name or not target_name:
            self.cmd_unknown(cmd)
            return
        item_id = self._find_item_id(item_name, in_inventory=cfg.item_in_inventory)
        if not item_id:
            io.output(self.language_manager.messages[cfg.item_missing_key])
            self.check_end()
            return
        finder = self._find_npc_id if cfg.target_is_npc else self._find_item_id
        target_id = finder(target_name)
        if not target_id:
            io.output(self.language_manager.messages[cfg.target_missing_key])
            self.check_end()
            return
        if self._execute_action(cfg.trigger, item_id, target_id):
            self.check_end()
            return
        io.output(self.language_manager.messages[cfg.failure_key])
        self.check_end()

    def _execute_action(
        self, trigger: str, item_id: str, target_id: str | None = None
    ) -> bool:
        for action in self.world.actions:
            if action.get("trigger") != trigger:
                continue
            if action.get("item") and action.get("item") != item_id:
                continue
            if action.get("target_item") and action.get("target_item") != target_id:
                continue
            if action.get("target_npc") and action.get("target_npc") != target_id:
                continue
            if not self.world.check_preconditions(action.get("preconditions")):
                continue
            effect = action.get("effect", {})
            self.world.apply_effect(effect)
            message = action.get("messages", {}).get("success")
            if message:
                io.output(message)
            return True
        return False

    def describe_item(self, item_name: str) -> None:
        if not item_name:
            self.cmd_unknown(item_name)
            return
        item_id = self._find_item_id(item_name)
        if not item_id:
            io.output(self.language_manager.messages["item_not_present"])
            return
        desc = self.world.describe_item(item_name)
        if desc:
            io.output(desc)
        self._execute_action("examine", item_id)
        self.check_end()

    # ------------------------------------------------------------------
    # Command handlers
    def cmd_quit(self, arg: str) -> None:  # noqa: ARG002 - required signature
        self.save_manager.save(self.world, self.language_manager.language)
        io.output(self.language_manager.messages["farewell"])
        self.stop()

    def cmd_inventory(self, arg: str) -> None:  # noqa: ARG002
        io.output(self.world.describe_inventory(self.language_manager.messages))

    def cmd_take(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item_name = arg
        taken = self.world.take(item_name)
        if taken:
            io.output(self.language_manager.messages["taken"].format(item=taken))
        else:
            io.output(self.language_manager.messages["item_not_present"])
        self.check_end()

    def cmd_drop(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item = arg
        if self.world.drop(item):
            io.output(self.language_manager.messages["dropped"].format(item=item))
        else:
            io.output(self.language_manager.messages["not_carrying"])
        self.check_end()

    def cmd_destroy(self, arg: str) -> None:
        self._state_command("destroy", arg)

    def cmd_wear(self, arg: str) -> None:
        self._state_command("wear", arg)

    def cmd_look(self, arg: str) -> None:
        if arg:
            self.cmd_unknown(arg)
            return
        io.output(self.world.describe_current(self.language_manager.messages))

    def cmd_examine(self, arg: str) -> None:
        self.describe_item(arg)

    def cmd_go(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        direction = arg
        if self.world.can_move(direction) and self.world.move(direction):
            io.output(self.world.describe_current(self.language_manager.messages))
            self.check_npc_event()
        else:
            io.output(self.language_manager.messages["cannot_move"])
        self.check_end()

    def cmd_help(self, arg: str) -> None:
        if not arg:
            names: list[str] = []
            for key in self.command_keys:
                val = self.language_manager.commands.get(key, [])
                entries = val if isinstance(val, list) else [val]
                first = entries[0]
                names.append(first.split()[0])
            io.output(
                self.language_manager.messages["help"].format(commands=", ".join(names))
            )
            return
        cmd_info = self.reverse_cmds.get(arg)
        if not cmd_info:
            self.cmd_unknown(arg)
            return
        key, _ = cmd_info
        entries = self.language_manager.commands.get(key, [])
        entries = entries if isinstance(entries, list) else [entries]
        usages: list[str] = []
        for entry in entries:
            if self.language_manager.command_info.get(key, {}).get(
                "optional_arguments"
            ) and "$" not in entry:
                continue
            usage = entry.replace("$a", "<>").replace("$b", "<>")
            usages.append(usage)
        header = self.language_manager.messages.get(
            "help_usage", "Usage of \"{command}\" and synonyms:"
        )
        io.output(header.format(command=key) + "\n" + "\n".join(usages))

    def cmd_language(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        language = arg.strip()
        try:
            new_world = self.language_manager.switch(language, self.world, self.save_manager)
        except ValueError:
            io.output(
                self.language_manager.messages.get(
                    "language_unknown", "Unknown language"
                )
            )
            return
        self.world = new_world
        self._update_world(new_world)
        self._build_cmd_patterns()
        io.output(
            self.language_manager.messages["language_set"].format(language=language)
        )

    def cmd_show(self, item_name: str, npc_name: str) -> None:
        self._action_command("show", item_name, npc_name)

    def cmd_talk(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        npc_id = self._find_npc_id(arg)
        if not npc_id:
            io.output(self.language_manager.messages["no_npc"])
            return
        npc = self.world.npcs[npc_id]
        state = self.world.npc_state(npc_id)
        talk_cfg = npc.get("states", {}).get(state, {})
        text = talk_cfg.get("talk")
        if text:
            io.output(text)
        else:
            io.output(self.language_manager.messages["no_npc"])
        if state != "helped":
            self.world.set_npc_state(npc_id, "helped")

    def cmd_use(self, item_name: str, target_name: str) -> None:
        self._action_command("use", item_name, target_name)

    def cmd_unknown(self, arg: str) -> None:  # noqa: ARG002 - compatibility
        io.output(self.language_manager.messages["unknown_command"])


__all__ = ["CommandProcessor"]

