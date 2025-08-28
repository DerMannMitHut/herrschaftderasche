"""Core game loop."""

from pathlib import Path
import re
from typing import Callable, cast

import yaml

from engine import io, parser, world, llm, i18n, integrity


class Game:
    def __init__(self, world_data_path: str, language: str, debug: bool = False) -> None:
        data_path = Path(world_data_path)
        self.data_dir = data_path.parent.parent
        self.save_path = self.data_dir / "save.yaml"
        generic_path = self.data_dir / "generic" / "world.yaml"
        self.debug = debug

        save_data: dict[str, object] = {}
        if self.save_path.exists():
            with open(self.save_path, encoding="utf-8") as fh:
                save_data = yaml.safe_load(fh) or {}
        self.language = str(save_data.get("language", language))
        lang_world_path = self.data_dir / self.language / "world.yaml"

        warnings = integrity.check_translations(self.language, self.data_dir)
        for msg in warnings:
            io.output(f"WARNING: {msg}")

        self.world = world.World.from_files(generic_path, lang_world_path, debug=debug)

        errors = integrity.validate_world_structure(self.world)
        if save_data:
            errors.extend(integrity.validate_save(save_data, self.world))

        if errors:
            for msg in errors:
                io.output(f"ERROR: {msg}")
            raise SystemExit("Integrity check failed")

        if save_data:
            self.world.load_state(self.save_path)
            self.save_path.unlink()

        self.messages = i18n.load_messages(self.language)
        self.commands = i18n.load_commands(self.language)
        self.command_info = i18n.load_command_info()
        self.command_keys = list(self.command_info.keys())
        self.cmd_patterns: list[tuple[re.Pattern[str], str, str]] = []
        self.reverse_cmds: dict[str, tuple[str, str]] = {}
        self._build_cmd_patterns()
        self.running = True

    def run(self) -> None:
        io.output(self.world.describe_current(self.messages))
        self._check_npc_event()
        self._check_end()
        try:
            while self.running:
                raw = io.get_input()
                raw = llm.interpret(raw)
                raw = parser.parse(raw)
                for pattern, cmd_key, _ in self.cmd_patterns:
                    match = pattern.fullmatch(raw)
                    if not match:
                        continue
                    groups = match.groupdict()
                    handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
                    if cmd_key == "use":
                        a = groups.get("a", "").strip()
                        b = groups.get("b", "").strip()
                        use_handler = cast(Callable[[str, str], None], handler)
                        use_handler(a, b)
                    else:
                        arg = groups.get("a", "") or groups.get("b", "") or ""
                        other_handler = cast(Callable[[str], None], handler)
                        other_handler(arg.strip())
                    break
                else:
                    self.cmd_unknown(raw)
        except (EOFError, KeyboardInterrupt):
            io.output(self.messages["farewell"])
        finally:
            self._save_state()

    def _save_state(self) -> None:
        data = self.world.to_state()
        data["language"] = self.language
        with open(self.save_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh)

    def _strip_suffix(self, arg: str, suffix: str) -> str:
        if suffix and arg.endswith(f" {suffix}"):
            return arg[: -len(suffix) - 1].strip()
        return arg

    def cmd_quit(self, arg: str) -> None:
        self._save_state()
        io.output(self.messages["farewell"])
        self.running = False

    def cmd_inventory(self, arg: str) -> None:
        io.output(self.world.describe_inventory(self.messages))

    def cmd_take(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item_name = arg
        taken = self.world.take(item_name)
        if taken:
            io.output(self.messages["taken"].format(item=taken))
        else:
            io.output(self.messages["item_not_present"])
        self._check_end()

    def cmd_drop(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item = arg
        if self.world.drop(item):
            io.output(self.messages["dropped"].format(item=item))
        else:
            io.output(self.messages["not_carrying"])
        self._check_end()

    def cmd_destroy(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item = arg
        item_cf = item.casefold()
        for item_id in list(self.world.inventory):
            names = self.world.items.get(item_id, {}).get("names", [])
            if any(name.casefold() == item_cf for name in names):
                self.world.inventory.remove(item_id)
                self.world.debug(f"inventory {self.world.inventory}")
                self.world.set_item_state(item_id, "destroyed")
                io.output(self.messages["destroyed"].format(item=item))
                break
        else:
            io.output(self.messages["not_carrying"])
        self._check_end()

    def cmd_wear(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item = arg
        item_cf = item.casefold()
        for item_id in list(self.world.inventory):
            names = self.world.items.get(item_id, {}).get("names", [])
            if any(name.casefold() == item_cf for name in names):
                self.world.inventory.remove(item_id)
                self.world.debug(f"inventory {self.world.inventory}")
                self.world.set_item_state(item_id, "worn")
                io.output(self.messages["worn"].format(item=item))
                break
        else:
            io.output(self.messages["not_carrying"])
        self._check_end()

    def cmd_look(self, arg: str) -> None:
        if arg:
            self.cmd_unknown(arg)
            return
        io.output(self.world.describe_current(self.messages))

    def cmd_examine(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        desc = self.world.describe_item(arg)
        if desc:
            io.output(desc)
        else:
            io.output(self.messages["item_not_present"])

    def cmd_go(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        direction = arg
        if self.world.move(direction):
            io.output(self.world.describe_current(self.messages))
            self._check_npc_event()
        else:
            io.output(self.messages["cannot_move"])
        self._check_end()

    def cmd_help(self, arg: str) -> None:
        if not arg:
            names: list[str] = []
            for key in self.command_keys:
                val = self.commands.get(key, [])
                entries = val if isinstance(val, list) else [val]
                first = entries[0]
                names.append(first.split()[0])
            io.output(self.messages["help"].format(commands=", ".join(names)))
            return
        cmd_info = self.reverse_cmds.get(arg)
        if not cmd_info:
            self.cmd_unknown(arg)
            return
        key, _ = cmd_info
        entries = self.commands.get(key, [])
        entries = entries if isinstance(entries, list) else [entries]
        usages: list[str] = []
        for entry in entries:
            if self.command_info.get(key, {}).get("optional_arguments") and "$" not in entry:
                continue
            usage = entry.replace("$a", "<>").replace("$b", "<>")
            usages.append(usage)
        header = self.messages.get("help_usage", "Usage of \"{command}\" and synonyms:")
        io.output(header.format(command=key) + "\n" + "\n".join(usages))

    def cmd_language(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        language = arg.strip()
        try:
            messages = i18n.load_messages(language)
            commands = i18n.load_commands(language)
            world_path = self.data_dir / language / "world.yaml"
            generic_path = self.data_dir / "generic" / "world.yaml"
            new_world = world.World.from_files(
                generic_path, world_path, debug=self.debug
            )
        except FileNotFoundError:
            io.output(self.messages.get("language_unknown", "Unknown language"))
            return
        self._save_state()
        new_world.load_state(self.save_path)
        self.save_path.unlink()
        self.world = new_world
        self.language = language
        self.messages = messages
        self.commands = commands
        self.cmd_patterns = []
        self.reverse_cmds = {}
        self._build_cmd_patterns()
        io.output(self.messages["language_set"].format(language=language))

    def cmd_talk(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        npc_name_cf = arg.casefold()
        for npc_id, npc in self.world.npcs.items():
            names = npc.get("names", [])
            if not any(name.casefold() == npc_name_cf for name in names):
                continue
            meet = npc.get("meet", {})
            if meet.get("location") != self.world.current:
                io.output(self.messages["no_npc"])
                return
            state = self.world.npc_state(npc_id)
            states = npc.get("states", {})
            talk_cfg = states.get(state, {})
            text = talk_cfg.get("talk")
            if text:
                io.output(text)
            else:
                io.output(self.messages["no_npc"])
            if state != "helped":
                self.world.set_npc_state(npc_id, "helped")
            return
        io.output(self.messages["no_npc"])

    def cmd_use(self, item_name: str, target_name: str) -> None:
        if not item_name or not target_name:
            self.cmd_unknown("use")
            return
        item_id = None
        target_id = None
        item_name_cf = item_name.casefold()
        target_name_cf = target_name.casefold()
        for inv_id in self.world.inventory:
            names = self.world.items.get(inv_id, {}).get("names", [])
            if item_id is None and any(name.casefold() == item_name_cf for name in names):
                item_id = inv_id
            if target_id is None and any(name.casefold() == target_name_cf for name in names):
                target_id = inv_id
        if not item_id or not target_id:
            io.output(self.messages["use_failure"])
            self._check_end()
            return
        for action in self.world.actions:
            if action.get("trigger") != "use":
                continue
            if action.get("item") == item_id and action.get("target_item") == target_id:
                if not self.world.check_preconditions(action.get("preconditions")):
                    continue
                effect = action.get("effect", {})
                self.world.apply_effect(effect)
                message = action.get("messages", {}).get("success")
                if message:
                    io.output(message)
                else:
                    io.output(self.messages["use_failure"])
                self._check_end()
                return
        io.output(self.messages["use_failure"])
        self._check_end()

    def _build_cmd_patterns(self) -> None:
        for key in self.command_keys:
            val = self.commands.get(key, [])
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

    def cmd_unknown(self, arg: str) -> None:
        io.output(self.messages["unknown_command"])

    def _check_end(self) -> None:
        ending = self.world.check_endings()
        if ending:
            io.output(ending)
            self.running = False

    def _check_npc_event(self) -> None:
        for npc_id, npc in self.world.npcs.items():
            meet = npc.get("meet", {})
            loc = meet.get("location")
            text = meet.get("text")
            if loc == self.world.current and self.world.npc_state(npc_id) != "met":
                if text:
                    io.output(text)
                self.world.meet_npc(npc_id)


def run(world_data_path: str, language: str = "en", debug: bool = False) -> None:
    Game(world_data_path, language, debug=debug).run()
