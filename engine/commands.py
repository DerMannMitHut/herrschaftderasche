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
from .world_model import CommandCategory, StateTag


def require_args(n: int) -> Callable[[Callable[..., bool | None]], Callable[..., bool]]:
    """Ensure that ``n`` positional arguments are provided and non-empty."""

    def decorator(func: Callable[..., bool | None]) -> Callable[..., bool]:
        from inspect import signature

        sig = signature(func)
        params = list(sig.parameters.values())[1:]
        max_args = len(params)

        @wraps(func)
        def wrapper(self, *args: str) -> bool:
            if len(args) < n or len(args) > max_args or any(not arg for arg in args[:n]):
                return False
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
        self._build_cmd_patterns()
        cfg = getattr(language, "llm_config", {}) or {}
        arts = cfg.get("ignore_articles") or []
        contr = cfg.get("ignore_contractions") or []
        self._ignore_articles: set[str] = {str(a).casefold() for a in arts}
        self._ignore_contractions: set[str] = {str(c).casefold() for c in contr}
        self._last_duration: int | None = None
        self._dialog_npc: str | None = None
        self._dialog_node: str | None = None
        self._npc_prefixes = self._build_npc_prefixes()
        self._dialog_option_map: dict[str, str] = {}

    def execute(self, raw: str) -> bool:
        """Execute ``raw`` and return True if parsing succeeded, else False.

        On False, no user output should have been produced; caller may use LLM.
        """

        before = self.world.to_state()
        prev_time = self.world.time
        outputs: list[str] = []
        original_output = self.io.output

        def capture(text: str) -> None:
            outputs.append(text)
            original_output(text)

        self.io.output = capture
        parse_ok: bool | None = None
        try:
            for pattern, cmd_key, _ in self.cmd_patterns:
                match = pattern.fullmatch(raw)
                if not match:
                    continue
                groups = match.groupdict()
                handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
                info = self.command_info.get(cmd_key, {})
                args_preview = {k: v for k, v in groups.items() if v}
                self.world.debug(f"command {cmd_key} args {args_preview}")
                arg_count = info.get("arguments", 0)
                ok = True
                if arg_count == 2:
                    a = groups.get("a", "").strip()
                    b = groups.get("b", "").strip()
                    two_handler = cast(Callable[[str, str], bool], handler)
                    ok = two_handler(a, b)
                elif arg_count == 1:
                    arg = groups.get("a", "") or groups.get("b", "") or ""
                    one_handler = cast(Callable[[str], bool], handler)
                    ok = one_handler(arg.strip())
                elif info.get("optional_arguments"):
                    arg = groups.get("a", "") or groups.get("b", "") or ""
                    opt_handler = cast(Callable[[str | None], bool], handler)
                    ok = opt_handler(arg.strip() or None)
                else:
                    zero_handler = cast(Callable[[], bool], handler)
                    ok = zero_handler()
                parse_ok = bool(ok)
                break
        finally:
            self.io.output = original_output
        after = self.world.to_state()
        if parse_ok:
            duration = self._last_duration if isinstance(self._last_duration, int) else 1
            self.world.advance_time(duration)
            self._last_duration = None
            # If hour changed, output current time once
            prev_hour = (int(prev_time) % 1440) // 60
            cur_hour = (int(self.world.time) % 1440) // 60
            if prev_hour != cur_hour:
                ts = self.world.format_time()
                msg = self.language_manager.messages.get("time", "{time}").format(time=ts)
                outputs.append(msg)
                original_output(msg)
        if before != after:
            self.log.append(LogEntry(raw, outputs))
        return bool(parse_ok)

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

    def _strip_suffix(self, arg: str, suffix: str) -> str:
        if suffix and arg.endswith(f" {suffix}"):
            return arg[: -len(suffix) - 1].strip()
        return arg

    def _strip_leading_tokens(self, text: str) -> str:
        parts = text.strip().split()
        while parts and parts[0].casefold() in (self._ignore_articles | self._ignore_contractions):
            parts.pop(0)
        return " ".join(parts)

    def _find_item_id(self, name: str, *, in_inventory: bool = False) -> str | None:
        if not name:
            return None
        name = self._strip_leading_tokens(name)
        name_cf = name.casefold()
        if not in_inventory:
            room = self.world.rooms[self.world.current]
            for item_id in room.get("items", []):
                names = self.world.item_names(item_id)
                if any(n.casefold() == name_cf for n in names):
                    return item_id
        for item_id in self.world.inventory:
            names = self.world.item_names(item_id)
            if any(n.casefold() == name_cf for n in names):
                return item_id
        return None

    def _find_npc_id(self, name: str) -> str | None:
        if not name:
            return None
        name = self._strip_leading_tokens(name)
        name_cf = name.casefold()
        room = self.world.rooms[self.world.current]
        for npc_id in room.occupants:
            npc = self.world.npcs.get(npc_id)
            if not npc:
                continue
            # respect visibility preconditions
            pre = npc.get("meet", {}).get("preconditions")
            if pre and not self.world.check_preconditions(pre):
                continue
            names = npc.get("names", [])
            if any(n.casefold() == name_cf for n in names):
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
        if not item_id and not cfg.item_in_inventory:
            # Fallback: allow referring to any known item when inventory presence not required
            item_id = self._match_any_item_id(item_name)
        if not item_id:
            self.io.output(self.language_manager.messages[cfg.item_missing_key])
            return
        finder = self._find_npc_id if cfg.target_is_npc else self._find_item_id
        target_id = finder(target_name)
        if not target_id:
            self.io.output(self.language_manager.messages[cfg.target_missing_key])
            return
        if self._execute_action(cfg.trigger, item_id, target_id):
            # If an ending is now reachable, print it here (without stopping the loop).
            ending = self.world.check_endings()
            if ending:
                self.io.output("")
                self.io.output(ending)
            return
        self.io.output(self.language_manager.messages[cfg.failure_key])

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
            dur = getattr(action, "duration", None)
            if dur is not None:
                try:
                    self._last_duration = int(dur)
                except Exception:
                    self._last_duration = None
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
        if self._match_any_item_id(item_name) is None:
            return False
        # Prefer a canonical item name from the current room to avoid issues
        # with articles or inflections present in user input.
        preferred = item_name
        room = self.world.rooms[self.world.current]
        item_id = None
        # Try to find the item in the room, ignoring leading articles/contractions
        item_id = self._find_item_id(item_name, in_inventory=False)
        if item_id and item_id in room.items:
            names = self.world.item_names(item_id)
            if names:
                preferred = names[0]
        taken = self.world.take(preferred)
        if taken:
            self.io.output(self.language_manager.messages["taken"].format(item=taken))
        else:
            self.io.output(self.language_manager.messages["item_not_present"])
        self.check_end()
        return True

    @require_args(1)
    def cmd_drop(self, item: str) -> bool:
        if self._match_any_item_id(item) is None:
            return False
        # Normalize to canonical inventory name to handle leading articles
        preferred = item
        inv_id = self._find_item_id(item, in_inventory=True)
        if inv_id and inv_id in self.world.inventory:
            names = self.world.item_names(inv_id)
            if names:
                preferred = names[0]
        if self.world.drop(preferred):
            self.io.output(self.language_manager.messages["dropped"].format(item=item))
        else:
            self.io.output(self.language_manager.messages["not_carrying"])
        self.check_end()
        return True

    @require_args(1)
    def cmd_destroy(self, item_name: str) -> bool:
        if self._match_any_item_id(item_name) is None:
            return False
        self._state_command("destroy", item_name)
        return True

    @require_args(1)
    def cmd_wear(self, item_name: str) -> bool:
        if self._match_any_item_id(item_name) is None:
            return False
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
        if self._dialog_npc:
            self.io.output("")
            self._list_dialog_options()
        return True

    @require_args(1)
    def cmd_examine(self, item_name: str) -> bool:
        # Prefer items, but allow NPCs at the same location
        if self._match_any_item_id(item_name):
            self.describe_item(item_name)
            return True
        if self._match_any_npc_id(item_name):
            self.describe_npc(item_name)
            return True
        return False

    @require_args(1)
    def cmd_go(self, direction: str) -> bool:
        direction = self._strip_leading_tokens(direction)
        if not self.world.has_room(direction):
            return False
        # Determine a friendly display name for the destination (first exit name)
        dest_display = direction
        target_room_id = None
        room = self.world.rooms[self.world.current]
        dir_cf = direction.casefold()
        for _target, cfg in room.exits.items():
            names = cfg.get("names", [])
            if any(n.casefold() == dir_cf for n in names):
                if names:
                    dest_display = names[0]
                target_room_id = _target
                break

        move_duration = self.world.get_exit_duration(direction)
        if self.world.can_move(direction) and self.world.move(direction):
            self._last_duration = move_duration
            # Confirmation message for movement using language-specific article only
            art_tpl = self.language_manager.messages.get("going_to_article")
            if art_tpl and target_room_id:
                room_obj = self.world.rooms.get(target_room_id)
                if room_obj:
                    art = room_obj.get("to_article")
                    if art:
                        self.io.output(art_tpl.format(article=art, place=dest_display))
            header = self.world.describe_room_header(self.language_manager.messages)
            self.io.output(header)
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
            if self._dialog_npc:
                self.io.output("")
                self._list_dialog_options()
        else:
            self.io.output(self.language_manager.messages["cannot_move"])
        self.check_end()
        return True

    @require_args(0)
    def cmd_help(self, arg: str | None = None) -> bool:
        if not arg:
            cmds = self.language_manager.commands

            def display_for(key: str) -> str:
                val = cmds.get(key, [])
                entries = val if isinstance(val, list) else [val]
                if not entries:
                    return key
                phrase = (entries[0] or "").strip()
                phrase = phrase.replace("$a", "<>").replace("$b", "<>")
                info = self.language_manager.command_info.get(key, {})
                if info.get("optional_arguments") and ("<>" not in phrase):
                    phrase += " [n]" if key == "show_log" else " [<>]"
                return phrase or key

            info_map = self.language_manager.command_info
            sys_keys = [k for k, inf in info_map.items() if (inf or {}).get("category") == CommandCategory.SYSTEM.value]
            bas_keys = [k for k, inf in info_map.items() if (inf or {}).get("category") == CommandCategory.BASICS.value]
            act_keys = [k for k, inf in info_map.items() if (inf or {}).get("category") == CommandCategory.ACTIONS.value]

            sys_list = sorted({display_for(k) for k in sys_keys if k in cmds}, key=lambda s: s.casefold())
            bas_list = sorted({display_for(k) for k in bas_keys if k in cmds}, key=lambda s: s.casefold())
            act_list = sorted({display_for(k) for k in act_keys if k in cmds}, key=lambda s: s.casefold())

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
    def cmd_time(self) -> bool:
        ts = self.world.format_time()
        self.io.output(self.language_manager.messages.get("time", "{time}").format(time=ts))
        return True

    @require_args(0)
    def cmd_show_log(self, count: str | None = None) -> bool:
        n = None
        if count:
            if not count.isdigit():
                return False
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
        if self._match_any_item_id(item_name) is None or self._match_any_npc_id(npc_name) is None:
            return False
        self._action_command("show", item_name, npc_name)
        return True

    def _advance_dialog(self, option_id: str | None) -> bool:
        npc_id = self._dialog_npc
        node_id = self._dialog_node
        if not npc_id or not node_id:
            return False
        npc = self.world.npcs.get(npc_id)
        if not npc:
            self._dialog_npc = None
            self._dialog_node = None
            return False
        dialog = getattr(npc, "dialog", {})
        node = dialog.get(node_id)
        if not node:
            self._dialog_npc = None
            self._dialog_node = None
            return False
        if option_id is not None:
            opt = next((o for o in node.options if o.id.casefold() == option_id.casefold()), None)
            if not opt:
                return False
            eff = opt.effect or {}
            state = eff.get("set_npc_state")
            if state is not None:
                self.world.set_npc_state(npc_id, state)
            other = {k: v for k, v in eff.items() if k != "set_npc_state"}
            if other:
                self.world.apply_effect(other)
            self._dialog_node = opt.next
            node_id = self._dialog_node
            if not node_id:
                self._dialog_npc = None
                self.check_end()
                return True
            node = dialog.get(node_id)
            if not node:
                self._dialog_npc = None
                return True
        eff = node.effect or {}
        state = eff.get("set_npc_state")
        if state is not None:
            self.world.set_npc_state(npc_id, state)
        other = {k: v for k, v in eff.items() if k != "set_npc_state"}
        if other:
            self.world.apply_effect(other)
        text = node.text
        if text:
            self.io.output(text)
        self._list_dialog_options()
        if not self._dialog_option_map:
            self._dialog_npc = None
            self._dialog_node = None
        self.check_end()
        return True

    @require_args(1)
    def cmd_talk(self, npc_name: str) -> bool:
        self._dialog_option_map.clear()
        if self._match_any_npc_id(npc_name) is None:
            return False
        npc_id = self._find_npc_id(npc_name)
        if not npc_id:
            self.io.output(self.language_manager.messages["no_npc"])
            return True
        npc = self.world.npcs[npc_id]
        dialog = getattr(npc, "dialog", {})
        if dialog:
            self._dialog_npc = npc_id
            self._dialog_node = "start"
            self._advance_dialog(None)
            return True
        self._dialog_npc = None
        self._dialog_node = None
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
        self.check_end()
        return True

    @require_args(1)
    def cmd_say(self, option_id: str) -> bool:
        option_id = option_id.strip()
        if not option_id or not self._dialog_npc:
            return False
        internal = self._dialog_option_map.get(option_id.casefold())
        if not internal:
            msg = self.language_manager.messages.get("invalid_dialog_option")
            if msg:
                self.io.output(msg)
            return True
        return self._advance_dialog(internal)

    @require_args(2)
    def cmd_use(self, item_name: str, target_name: str) -> bool:
        if self._match_any_item_id(item_name) is None or self._match_any_item_id(target_name) is None:
            return False
        self._action_command("use", item_name, target_name)
        return True

    def cmd_unknown(self, _arg: str | None = None) -> bool:
        return False

    def _match_any_item_id(self, name: str) -> str | None:
        if not name:
            return None
        name = self._strip_leading_tokens(name)
        name_cf = name.casefold()
        for item_id in self.world.items:
            names = self.world.item_names(item_id)
            if any(n.casefold() == name_cf for n in names):
                return item_id
        return None

    def _match_any_npc_id(self, name: str) -> str | None:
        if not name:
            return None
        name = self._strip_leading_tokens(name)
        name_cf = name.casefold()
        for npc_id, npc in self.world.npcs.items():
            names = getattr(npc, "names", [])
            if any(n.casefold() == name_cf for n in names):
                return npc_id
        return None

    def _build_npc_prefixes(self) -> dict[str, str]:
        prefixes: dict[str, str] = {}
        names = {nid: npc.names[0] for nid, npc in self.world.npcs.items() if npc.names}
        for nid, name in names.items():
            prefix_len = 1
            lowered = name.casefold()
            while any(other_id != nid and other_name.casefold().startswith(lowered[:prefix_len]) for other_id, other_name in names.items()):
                prefix_len += 1
            prefixes[nid] = name[:prefix_len]
        return prefixes

    def _list_dialog_options(self) -> None:
        npc_id = self._dialog_npc
        node_id = self._dialog_node
        if not npc_id or not node_id:
            return
        npc = self.world.npcs.get(npc_id)
        if not npc:
            return
        node = getattr(npc, "dialog", {}).get(node_id)
        if not node:
            return
        options = list(getattr(node, "options", []))
        if not options:
            return
        prefix = self._npc_prefixes.get(npc_id, "")
        self._dialog_option_map.clear()
        for idx, opt in enumerate(options, start=1):
            display_id = f"{prefix}{idx}"
            self._dialog_option_map[display_id.casefold()] = opt.id
            prompt = opt.prompt or opt.id
            self.io.output(f"{display_id}: {prompt}")

    def list_dialog_options(self) -> None:
        self._list_dialog_options()

    def describe_npc(self, npc_name: str) -> None:
        """Describe an NPC if present and visible; otherwise output no_npc."""
        if not npc_name:
            self.cmd_unknown(npc_name)
            return
        npc_id = self._find_npc_id(npc_name)
        if not npc_id:
            self.io.output(self.language_manager.messages["no_npc"])
            return
        desc = self.world.describe_npc(npc_name)
        if desc:
            self.io.output(desc)
        self.check_end()


__all__ = ["CommandProcessor"]
