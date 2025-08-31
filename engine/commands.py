"""Command handling for the game."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import cast

from . import world
from .interfaces import IOBackend
from .language import LanguageManager
from .persistence import LogEntry, SaveManager
from .world_model import StateTag


def require_args(n: int) -> Callable[[Callable[..., bool | None]], Callable[..., bool]]:
    """Ensure that ``n`` positional arguments are provided and non-empty."""

    def decorator(func: Callable[..., bool | None]) -> Callable[..., bool]:
        from inspect import signature

        sig = signature(func)
        params = list(sig.parameters.values())[1:]
        max_args = len(params)

        @wraps(func)
        def wrapper(self, *args: str) -> bool:
            probe = getattr(self, "_probe_mode", False)
            if len(args) < n or len(args) > max_args or any(not arg for arg in args[:n]):
                if probe:
                    return False
                self.cmd_unknown(args[0] if args else "")
                return True
            res = func(self, *args)
            return bool(res) if res is not None else True

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
        self.command_keys = list(self.command_info.keys())
        self.log = log or []
        self.cmd_patterns: list[tuple[re.Pattern[str], str, str]] = []
        self.reverse_cmds: dict[str, tuple[str, str]] = {}
        self._probe_mode: bool = False
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
                args_preview = {k: v for k, v in groups.items() if v}
                self.world.debug(f"command {cmd_key} args {args_preview}")
                arg_count = info.get("arguments", 0)
                if arg_count == 2:
                    a = groups.get("a", "").strip()
                    b = groups.get("b", "").strip()
                    two_handler = cast(Callable[[str, str], bool], handler)
                    two_handler(a, b)
                elif arg_count == 1:
                    arg = groups.get("a", "") or groups.get("b", "") or ""
                    one_handler = cast(Callable[[str], bool], handler)
                    one_handler(arg.strip())
                elif info.get("optional_arguments"):
                    arg = groups.get("a", "") or groups.get("b", "") or ""
                    opt_handler = cast(Callable[[str | None], bool], handler)
                    opt_handler(arg.strip() or None)
                else:
                    zero_handler = cast(Callable[[], bool], handler)
                    zero_handler()
                break
            else:
                self.cmd_unknown(raw)
        finally:
            self.io.output = original_output
        after = self.world.to_state()
        if before != after:
            self.log.append(LogEntry(raw, outputs))

    def try_execute(self, raw: str) -> bool:
        """Try to parse and validate a command without side effects.

        Returns True if parsing was successful (arguments resolvable),
        False otherwise. No user-visible output or world changes.
        """
        probe_prev = self._probe_mode
        self._probe_mode = True
        original_output = self.io.output
        try:
            # suppress outputs during probe
            def _suppress(text: str) -> None:  # noqa: D401, ARG001 - simple sink
                return None

            self.io.output = _suppress
            for pattern, cmd_key, _ in self.cmd_patterns:
                match = pattern.fullmatch(raw)
                if not match:
                    continue
                groups = match.groupdict()
                handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
                info = self.command_info.get(cmd_key, {})
                arg_count = info.get("arguments", 0)
                if arg_count == 2:
                    a = (groups.get("a") or "").strip()
                    b = (groups.get("b") or "").strip()
                    res = cast(Callable[[str, str], bool], handler)(a, b)
                elif arg_count == 1:
                    arg = (groups.get("a") or groups.get("b") or "").strip()
                    res = cast(Callable[[str], bool], handler)(arg)
                elif info.get("optional_arguments"):
                    arg = (groups.get("a") or groups.get("b") or "").strip() or None
                    res = cast(Callable[[str | None], bool], handler)(arg)
                else:
                    res = cast(Callable[[], bool], handler)()
                return bool(res)
            # No pattern matched: not a parse success
            return False
        finally:
            self._probe_mode = probe_prev
            self.io.output = original_output

    def can_execute(self, raw: str) -> bool:
        """Return True if ``raw`` matches any known command pattern."""
        return any(pattern.fullmatch(raw) for pattern, _cmd_key, _pattern_src in self.cmd_patterns)

    def can_execute_semantic(self, raw: str) -> bool:
        """Return True if ``raw`` matches and its arguments resolve to known entities.

        This is a lightweight pre-validation to decide whether to fall back to LLM.
        It does not execute side effects.
        """
        for pattern, cmd_key, _src in self.cmd_patterns:
            match = pattern.fullmatch(raw)
            if not match:
                continue
            groups = match.groupdict()
            info = self.command_info.get(cmd_key, {})
            arg_count = info.get("arguments", 0)
            # Zero-arg commands are always semantically valid
            if arg_count == 0 and not info.get("optional_arguments"):
                return True
            a = (groups.get("a") or "").strip()
            b = (groups.get("b") or "").strip()
            # Optional-arg commands: accept here; handler validates specifics
            if info.get("optional_arguments"):
                return True
            # One-arg commands
            if arg_count == 1:
                if cmd_key in {"take"}:
                    return self._find_item_id(a, in_inventory=False) is not None
                if cmd_key in {"drop", "destroy", "wear"}:
                    return self._find_item_id(a, in_inventory=True) is not None
                if cmd_key in {"examine"}:
                    return (self._find_item_id(a, in_inventory=False) is not None) or (self._find_item_id(a, in_inventory=True) is not None)
                if cmd_key in {"go"}:
                    return self.world.can_move(a)
                if cmd_key in {"talk"}:
                    return self._find_npc_id(a) is not None
                if cmd_key in {"language"}:
                    return bool(a)
                # Default: consider valid
                return True
            # Two-arg commands
            if arg_count == 2:
                if cmd_key in ACTION_COMMANDS:
                    cfg = ACTION_COMMANDS[cmd_key]
                    item_ok = self._find_item_id(a, in_inventory=cfg.item_in_inventory) is not None
                    finder = self._find_npc_id if cfg.target_is_npc else self._find_item_id
                    target_ok = finder(b) is not None
                    return item_ok and target_ok
                # Default: both non-empty
                return bool(a and b)
            # Default: valid
            return True
        return False

    # ------------------------------------------------------------------
    def _build_cmd_patterns(self) -> None:
        self.cmd_patterns.clear()
        self.reverse_cmds.clear()
        for key in self.command_keys:
            val = self.language_manager.commands.get(key, [])
            entries = val if isinstance(val, list) else [val]
            for entry in entries:
                info = self.language_manager.command_info.get(key, {})
                pattern, base = self._compile_command(entry, bool(info.get("optional_arguments")))
                self.cmd_patterns.append((pattern, key, entry))
                if base not in self.reverse_cmds:
                    self.reverse_cmds[base] = (key, entry)
        # Always allow calling commands by their ID (system/default form),
        # independent of the current language.
        for key in self.command_keys:
            info = self.language_manager.command_info.get(key, {})
            args = info.get("arguments", 0)
            if args == 2:
                regex = rf"^{re.escape(key)}\s+(?P<a>.+?)\s+(?P<b>.+)$"
            elif args == 1:
                regex = rf"^{re.escape(key)}\s+(?P<a>.+)$"
            elif info.get("optional_arguments"):
                regex = rf"^{re.escape(key)}(?:\s+(?P<a>.+))?$"
            else:
                regex = rf"^{re.escape(key)}$"
            self.cmd_patterns.append((re.compile(regex), key, key))
            if key not in self.reverse_cmds:
                self.reverse_cmds[key] = (key, key)
        self.cmd_patterns.sort(key=lambda x: len(x[0].pattern), reverse=True)
        self.reverse_cmds["language"] = ("language", "language")
        pattern = re.compile(r"^show_log(?:\s+(?P<a>\d+))?$")
        self.cmd_patterns.append((pattern, "show_log", "show_log"))
        self.reverse_cmds["show_log"] = ("show_log", "show_log")

    def _compile_command(self, pattern: str, optional: bool) -> tuple[re.Pattern[str], str]:
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
        regex = r"^" + r"\s+".join(parts)
        if optional and not placeholder_positions:
            regex += r"(?:\s+(?P<a>\d+))?"
        regex += r"$"
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

    def _action_command(self, cmd: str, item_name: str, target_name: str) -> None:
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

    def _execute_action(self, trigger: str, item_id: str, target_id: str | None = None) -> bool:
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
    def cmd_quit(self) -> bool:
        self.save_manager.save(self.world, self.language_manager.language, self.log)
        self.io.output(self.language_manager.messages["farewell"])
        self.stop()
        return True

    @require_args(0)
    def cmd_inventory(self) -> bool:
        self.io.output(self.world.describe_inventory(self.language_manager.messages))
        return True

    @require_args(1)
    def cmd_take(self, item_name: str) -> bool:
        if self._probe_mode:
            return self._find_item_id(item_name, in_inventory=False) is not None
        taken = self.world.take(item_name)
        if taken:
            self.io.output(self.language_manager.messages["taken"].format(item=taken))
        else:
            self.io.output(self.language_manager.messages["item_not_present"])
        self.check_end()
        return True

    @require_args(1)
    def cmd_drop(self, item: str) -> bool:
        if self._probe_mode:
            return self._find_item_id(item, in_inventory=True) is not None
        if self.world.drop(item):
            self.io.output(self.language_manager.messages["dropped"].format(item=item))
        else:
            self.io.output(self.language_manager.messages["not_carrying"])
        self.check_end()
        return True

    @require_args(1)
    def cmd_destroy(self, item_name: str) -> bool:
        if self._probe_mode:
            return self._find_item_id(item_name, in_inventory=True) is not None
        self._state_command("destroy", item_name)
        return True

    @require_args(1)
    def cmd_wear(self, item_name: str) -> bool:
        if self._probe_mode:
            return self._find_item_id(item_name, in_inventory=True) is not None
        self._state_command("wear", item_name)
        return True

    @require_args(0)
    def cmd_look(self) -> bool:
        header = self.world.describe_room_header(self.language_manager.messages)
        self.io.output(header)
        visible = self.world.describe_visibility(self.language_manager.messages)
        if visible:
            self.io.output("")
            self.io.output(visible)
        return True

    @require_args(1)
    def cmd_examine(self, item_name: str) -> bool:
        if self._probe_mode:
            return (
                self._find_item_id(item_name, in_inventory=False) is not None
                or self._find_item_id(item_name, in_inventory=True) is not None
            )
        self.describe_item(item_name)
        return True

    @require_args(1)
    def cmd_go(self, direction: str) -> bool:
        if self._probe_mode:
            return self.world.can_move(direction)
        if self.world.can_move(direction) and self.world.move(direction):
            header = self.world.describe_room_header(self.language_manager.messages)
            self.io.output(header)
            # Capture NPC event outputs to control blank line placement
            event_outs: list[str] = []
            original_output = self.io.output
            try:
                self.io.output = lambda text: event_outs.append(text)
                self.check_npc_event()
            finally:
                self.io.output = original_output
            if event_outs:
                self.io.output("")
                for line in event_outs:
                    self.io.output(line)
            visible = self.world.describe_visibility(self.language_manager.messages)
            if visible:
                self.io.output("")
                self.io.output(visible)
        else:
            self.io.output(self.language_manager.messages["cannot_move"])
        self.check_end()
        return True

    @require_args(0)
    def cmd_help(self, arg: str | None = None) -> bool:
        if not arg:
            # Build categorized columns: System, Basics, Interactions
            cmds = self.language_manager.commands

            def display_for(key: str) -> str:
                # Show first translation phrase with simple argument hints
                val = cmds.get(key, [])
                entries = val if isinstance(val, list) else [val]
                if not entries:
                    return key
                phrase = (entries[0] or "").strip()
                phrase = phrase.replace("$a", "<>").replace("$b", "<>")
                info = self.language_manager.command_info.get(key, {})
                if info.get("optional_arguments") and ("<>" not in phrase):
                    # Add an optional hint if pattern has no placeholders; use [n] for show_log
                    phrase += " [n]" if key == "show_log" else " [<>]"
                return phrase or key

            system_keys = ["quit", "help", "language", "show_log"]
            basic_keys = ["go", "look", "examine", "take", "drop", "inventory"]
            action_keys = ["talk", "use", "show", "destroy", "wear"]

            sys_list = [display_for(k) for k in system_keys if k in cmds]
            bas_list = [display_for(k) for k in basic_keys if k in cmds]
            act_list = [display_for(k) for k in action_keys if k in cmds]
            sys_list = sorted(set(sys_list), key=lambda s: s.casefold())
            bas_list = sorted(set(bas_list), key=lambda s: s.casefold())
            act_list = sorted(set(act_list), key=lambda s: s.casefold())

            # Headings (optional, localized if provided)
            msgs = self.language_manager.messages
            h_sys = msgs.get("help_section_system", "System")
            h_bas = msgs.get("help_section_basics", "Basics")
            h_act = msgs.get("help_section_actions", "Interactions")

            w1 = max([len(h_sys)] + [len(x) for x in sys_list]) if sys_list else len(h_sys)
            w2 = max([len(h_bas)] + [len(x) for x in bas_list]) if bas_list else len(h_bas)
            w3 = max([len(h_act)] + [len(x) for x in act_list]) if act_list else len(h_act)

            lines: list[str] = []
            lines.append(f"{h_sys.ljust(w1)}  {h_bas.ljust(w2)}  {h_act.ljust(w3)}")
            rows = max(len(sys_list), len(bas_list), len(act_list))
            for i in range(rows):
                a = sys_list[i] if i < len(sys_list) else ""
                b = bas_list[i] if i < len(bas_list) else ""
                c = act_list[i] if i < len(act_list) else ""
                lines.append(f"{a.ljust(w1)}  {b.ljust(w2)}  {c.ljust(w3)}")
            self.io.output("\n".join(lines))
            return True
        cmd_info = self.reverse_cmds.get(arg)
        if not cmd_info:
            self.cmd_unknown(arg)
            return True
        key, _ = cmd_info
        entries = self.language_manager.commands.get(key, [])
        entries = entries if isinstance(entries, list) else [entries]
        usages: list[str] = []
        for entry in entries:
            if self.language_manager.command_info.get(key, {}).get("optional_arguments") and "$" not in entry:
                continue
            usage = entry.replace("$a", "<>").replace("$b", "<>")
            usages.append(usage)
        header = self.language_manager.messages.get("help_usage", 'Usage of "{command}" and synonyms:')
        self.io.output(header.format(command=key) + "\n" + "\n".join(usages))
        return True

    @require_args(0)
    def cmd_show_log(self, count: str | None = None) -> bool:
        n = None
        if count:
            if not count.isdigit():
                return False if self._probe_mode else (self.cmd_unknown("show_log") or True)
            n = int(count)
        entries = self.log[-n:] if n else self.log
        lines: list[str] = []
        for entry in entries:
            lines.append(f"|> {entry.command}")
            lines.extend(f"| {o}" for o in entry.output)
        if lines:
            self.io.output("\n".join(lines))
        return True

    @require_args(1)
    def cmd_language(self, language: str) -> bool:
        language = language.strip()
        try:
            new_world = self.language_manager.switch(language, self.world, self.save_manager, self.log)
        except ValueError:
            self.io.output(self.language_manager.messages.get("language_unknown", "Unknown language"))
            return True
        self.world = new_world
        self._update_world(new_world)
        self._build_cmd_patterns()
        self.io.output(self.language_manager.messages["language_set"].format(language=language))
        return True

    @require_args(2)
    def cmd_show(self, item_name: str, npc_name: str) -> bool:
        if self._probe_mode:
            cfg = ACTION_COMMANDS["show"]
            item_ok = self._find_item_id(item_name, in_inventory=cfg.item_in_inventory) is not None
            target_ok = self._find_npc_id(npc_name) is not None
            return item_ok and target_ok
        self._action_command("show", item_name, npc_name)
        return True

    @require_args(1)
    def cmd_talk(self, npc_name: str) -> bool:
        if self._probe_mode:
            return self._find_npc_id(npc_name) is not None
        npc_id = self._find_npc_id(npc_name)
        if not npc_id:
            self.io.output(self.language_manager.messages["no_npc"])
            return True
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
        return True

    @require_args(2)
    def cmd_use(self, item_name: str, target_name: str) -> bool:
        if self._probe_mode:
            cfg = ACTION_COMMANDS["use"]
            item_ok = self._find_item_id(item_name, in_inventory=cfg.item_in_inventory) is not None
            target_ok = self._find_item_id(target_name, in_inventory=False) is not None
            return item_ok and target_ok
        self._action_command("use", item_name, target_name)
        return True

    def cmd_unknown(self, _arg: str | None = None) -> bool:
        if getattr(self, "_probe_mode", False):
            return False
        self.io.output(self.language_manager.messages["unknown_command"])
        return True


__all__ = ["CommandProcessor"]
