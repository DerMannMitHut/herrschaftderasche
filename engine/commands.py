"""Command handling for the game."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import wraps
from typing import Callable, cast

from . import world
from .language import LanguageManager
from .persistence import LogEntry, SaveManager
from .world_model import StateTag
from .interfaces import IOBackend


def require_args(n: int) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """Ensure that ``n`` positional arguments are provided and non-empty."""

    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        from inspect import signature

        sig = signature(func)
        params = list(sig.parameters.values())[1:]
        max_args = len(params)

        @wraps(func)
        def wrapper(self, *args: str) -> None:
            if len(args) < n or len(args) > max_args:
                self.cmd_unknown(args[0] if args else "")
                return
            if any(not arg for arg in args[:n]):
                self.cmd_unknown(args[0] if args else "")
                return
            func(self, *args)

        return wrapper

    return decorator

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
        io: IOBackend,
        log: list[LogEntry] | None = None,
    ) -> None:
        self.world = world
        self.language_manager = language
        self.save_manager = saver
        self.check_end = check_end
        self.check_npc_event = check_npc_event
        self.stop = stop
        self._update_world = update_world
        self.io = io
        self.command_info = language.command_info
        self.command_info["show_log"] = {"optional_arguments": True}
        self.command_keys = [k for k in self.command_info.keys() if k != "show_log"]
        self.log = log or []
        self.cmd_patterns: list[tuple[re.Pattern[str], str, str]] = []
        self.reverse_cmds: dict[str, tuple[str, str]] = {}
        self._build_cmd_patterns()

    # ------------------------------------------------------------------
    def execute(self, raw: str) -> None:
        """Execute the command contained in ``raw``."""

        before = self.world.to_state()
        outputs: list[str] = []
        original_output = self.io.output

        def capture(text: str) -> None:
            outputs.append(text)
            original_output(text)

        self.io.output = capture
        try:
            for pattern, cmd_key, _ in self.cmd_patterns:
                match = pattern.fullmatch(raw)
                if not match:
                    continue
                groups = match.groupdict()
                handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
                info = self.command_info.get(cmd_key, {})
                # Trace the resolved command and normalized arguments
                try:
                    # keep trace concise; avoid dumping large structures
                    args_preview = {k: v for k, v in groups.items() if v}
                    self.world.debug(f"command {cmd_key} args {args_preview}")
                except Exception:  # pragma: no cover - best-effort tracing
                    pass
                arg_count = info.get("arguments", 0)
                if arg_count == 2:
                    a = groups.get("a", "").strip()
                    b = groups.get("b", "").strip()
                    two_handler = cast(Callable[[str, str], None], handler)
                    two_handler(a, b)
                elif arg_count == 1:
                    arg = groups.get("a", "") or groups.get("b", "") or ""
                    one_handler = cast(Callable[[str], None], handler)
                    one_handler(arg.strip())
                elif info.get("optional_arguments"):
                    arg = groups.get("a", "") or groups.get("b", "") or ""
                    opt_handler = cast(Callable[[str | None], None], handler)
                    opt_handler(arg.strip() or None)
                else:
                    zero_handler = cast(Callable[[], None], handler)
                    zero_handler()
                break
            else:
                self.cmd_unknown(raw)
        finally:
            self.io.output = original_output
        after = self.world.to_state()
        if before != after:
            self.log.append(LogEntry(raw, outputs))

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
        pattern = re.compile(r"^show_log(?:\s+(?P<a>\d+))?$")
        self.cmd_patterns.append((pattern, "show_log", "show_log"))
        self.reverse_cmds["show_log"] = ("show_log", "show_log")

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
        cfg = STATE_COMMANDS[cmd]
        item_id = self._find_item_id(item_name, in_inventory=True)
        if not item_id:
            self.io.output(self.language_manager.messages["not_carrying"])
            self.check_end()
            return
        if not self.world.set_item_state(item_id, cfg.state):
            self.io.output(self.language_manager.messages["use_failure"])
            self.check_end()
            return
        self.world.inventory.remove(item_id)
        self.world.debug(f"inventory {self.world.inventory}")
        self.io.output(self.language_manager.messages[cfg.message_key].format(item=item_name))
        self.check_end()

    def _action_command(
        self, cmd: str, item_name: str, target_name: str
    ) -> None:
        cfg = ACTION_COMMANDS[cmd]
        item_id = self._find_item_id(item_name, in_inventory=cfg.item_in_inventory)
        if not item_id:
            self.io.output(self.language_manager.messages[cfg.item_missing_key])
            self.check_end()
            return
        finder = self._find_npc_id if cfg.target_is_npc else self._find_item_id
        target_id = finder(target_name)
        if not target_id:
            self.io.output(self.language_manager.messages[cfg.target_missing_key])
            self.check_end()
            return
        if self._execute_action(cfg.trigger, item_id, target_id):
            self.check_end()
            return
        self.io.output(self.language_manager.messages[cfg.failure_key])
        self.check_end()

    def _execute_action(
        self, trigger: str, item_id: str, target_id: str | None = None
    ) -> bool:
        for action in self.world.actions:
            if action.trigger != trigger:
                continue
            if action.item and action.item != item_id:
                continue
            if action.target_item and action.target_item != target_id:
                continue
            if action.target_npc and action.target_npc != target_id:
                continue
            if not self.world.check_preconditions(action.preconditions):
                continue
            effect = action.effect or {}
            self.world.apply_effect(effect)
            message = action.messages.get("success")
            if message:
                self.io.output(message)
            return True
        return False

    def describe_item(self, item_name: str) -> None:
        if not item_name:
            self.cmd_unknown(item_name)
            return
        item_id = self._find_item_id(item_name)
        if not item_id:
            self.io.output(self.language_manager.messages["item_not_present"])
            return
        desc = self.world.describe_item(item_name)
        if desc:
            self.io.output(desc)
        self._execute_action("examine", item_id)
        self.check_end()

    # ------------------------------------------------------------------
    # Command handlers
    @require_args(0)
    def cmd_quit(self) -> None:
        self.save_manager.save(
            self.world, self.language_manager.language, self.log
        )
        self.io.output(self.language_manager.messages["farewell"])
        self.stop()

    @require_args(0)
    def cmd_inventory(self) -> None:
        self.io.output(self.world.describe_inventory(self.language_manager.messages))

    @require_args(1)
    def cmd_take(self, item_name: str) -> None:
        taken = self.world.take(item_name)
        if taken:
            self.io.output(self.language_manager.messages["taken"].format(item=taken))
        else:
            self.io.output(self.language_manager.messages["item_not_present"])
        self.check_end()

    @require_args(1)
    def cmd_drop(self, item: str) -> None:
        if self.world.drop(item):
            self.io.output(self.language_manager.messages["dropped"].format(item=item))
        else:
            self.io.output(self.language_manager.messages["not_carrying"])
        self.check_end()

    @require_args(1)
    def cmd_destroy(self, item_name: str) -> None:
        self._state_command("destroy", item_name)

    @require_args(1)
    def cmd_wear(self, item_name: str) -> None:
        self._state_command("wear", item_name)

    @require_args(0)
    def cmd_look(self) -> None:
        header = self.world.describe_room_header(self.language_manager.messages)
        self.io.output(header)
        visible = self.world.describe_visibility()
        if visible:
            self.io.output("")
            self.io.output(visible)

    @require_args(1)
    def cmd_examine(self, item_name: str) -> None:
        self.describe_item(item_name)

    @require_args(1)
    def cmd_go(self, direction: str) -> None:
        if self.world.can_move(direction) and self.world.move(direction):
            header = self.world.describe_room_header(self.language_manager.messages)
            self.io.output(header)
            self.io.output("")
            self.check_npc_event()
            visible = self.world.describe_visibility()
            if visible:
                self.io.output("")
                self.io.output(visible)
        else:
            self.io.output(self.language_manager.messages["cannot_move"])
        self.check_end()

    @require_args(0)
    def cmd_help(self, arg: str | None = None) -> None:
        if not arg:
            names: list[str] = []
            for key in self.command_keys:
                val = self.language_manager.commands.get(key, [])
                entries = val if isinstance(val, list) else [val]
                if not entries:
                    continue
                first = entries[0]
                names.append(first.split()[0])
            self.io.output(
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
        self.io.output(header.format(command=key) + "\n" + "\n".join(usages))

    @require_args(0)
    def cmd_show_log(self, count: str | None = None) -> None:
        n = None
        if count:
            if not count.isdigit():
                self.cmd_unknown("show_log")
                return
            n = int(count)
        entries = self.log[-n:] if n else self.log
        lines: list[str] = []
        for entry in entries:
            lines.append(f"|> {entry.command}")
            lines.extend(f"| {o}" for o in entry.output)
        if lines:
            self.io.output("\n".join(lines))

    @require_args(1)
    def cmd_language(self, language: str) -> None:
        language = language.strip()
        try:
            new_world = self.language_manager.switch(
                language, self.world, self.save_manager, self.log
            )
        except ValueError:
            self.io.output(
                self.language_manager.messages.get(
                    "language_unknown", "Unknown language"
                )
            )
            return
        self.world = new_world
        self._update_world(new_world)
        self._build_cmd_patterns()
        self.io.output(
            self.language_manager.messages["language_set"].format(language=language)
        )

    @require_args(2)
    def cmd_show(self, item_name: str, npc_name: str) -> None:
        self._action_command("show", item_name, npc_name)

    @require_args(1)
    def cmd_talk(self, npc_name: str) -> None:
        npc_id = self._find_npc_id(npc_name)
        if not npc_id:
            self.io.output(self.language_manager.messages["no_npc"])
            return
        npc = self.world.npcs[npc_id]
        state = self.world.npc_state(npc_id)
        state_key = state.value if isinstance(state, StateTag) else state
        talk_cfg = npc.get("states", {}).get(state_key, {})
        text = talk_cfg.get("talk")
        if text:
            self.io.output(text)
        else:
            self.io.output(self.language_manager.messages["no_npc"])
        if state != StateTag.HELPED:
            self.world.set_npc_state(npc_id, StateTag.HELPED)

    @require_args(2)
    def cmd_use(self, item_name: str, target_name: str) -> None:
        self._action_command("use", item_name, target_name)

    def cmd_unknown(self, arg: str | None = None) -> None:
        self.io.output(self.language_manager.messages["unknown_command"])


__all__ = ["CommandProcessor"]
