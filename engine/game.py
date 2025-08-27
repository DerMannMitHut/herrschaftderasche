"""Core game loop."""

from pathlib import Path

import yaml

from engine import io, parser, world, llm, i18n


class Game:
    def __init__(self, world_data_path: str, language: str) -> None:
        data_path = Path(world_data_path)
        self.data_dir = data_path.parent.parent
        self.save_path = self.data_dir / "save.yaml"
        generic_path = self.data_dir / "generic" / "world.yaml"
        self.world = world.World.from_files(generic_path, world_data_path)
        self.language = language
        if self.save_path.exists():
            with open(self.save_path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            self.language = data.get("language", language)
            self.world.load_state(self.save_path)
            self.save_path.unlink()
        self.messages = i18n.load_messages(self.language)
        self.commands = i18n.load_commands(self.language)
        self.command_keys = i18n.load_command_keys()
        self.cmd_patterns: list[tuple[str, str, str]] = []
        self.reverse_cmds: dict[str, tuple[str, str]] = {}
        for key in self.command_keys:
            val = self.commands.get(key)
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, list):
                        name, suffix = entry
                    else:
                        name, suffix = entry, ""
                    self.cmd_patterns.append((name, key, suffix))
                    self.reverse_cmds[name] = (key, suffix)
            else:
                self.cmd_patterns.append((val, key, ""))
                self.reverse_cmds[val] = (key, "")
        self.cmd_patterns.sort(key=lambda x: len(x[0]), reverse=True)
        self.reverse_cmds["language"] = ("language", "")
        self.running = True

    def run(self) -> None:
        io.output(self.world.describe_current(self.messages))
        self._check_end()
        try:
            while self.running:
                raw = io.get_input()
                raw = llm.interpret(raw)
                raw = parser.parse(raw)
                for name, cmd_key, suffix in self.cmd_patterns:
                    if raw == name or raw.startswith(name + " "):
                        arg = raw[len(name):].strip()
                        arg = self._strip_suffix(arg, suffix)
                        handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
                        handler(arg)
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
        item = arg
        if self.world.take(item):
            io.output(self.messages["taken"].format(item=item))
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
        else:
            io.output(self.messages["cannot_move"])
        self._check_end()

    def cmd_help(self, arg: str) -> None:
        names: list[str] = []
        for key in self.command_keys:
            val = self.commands.get(key)
            if isinstance(val, list):
                first = val[0]
                if isinstance(first, list):
                    names.append(first[0])
                else:
                    names.append(first)
            else:
                names.append(val)
        io.output(self.messages["help"].format(commands=", ".join(names)))

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
            new_world = world.World.from_files(generic_path, world_path)
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
        for key in self.command_keys:
            val = self.commands.get(key)
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, list):
                        name, suffix = entry
                    else:
                        name, suffix = entry, ""
                    self.cmd_patterns.append((name, key, suffix))
                    self.reverse_cmds[name] = (key, suffix)
            else:
                self.cmd_patterns.append((val, key, ""))
                self.reverse_cmds[val] = (key, "")
        self.cmd_patterns.sort(key=lambda x: len(x[0]), reverse=True)
        self.reverse_cmds["language"] = ("language", "")
        io.output(self.messages["language_set"].format(language=language))

    def cmd_use(self, arg: str) -> None:
        if " on " not in arg:
            self.cmd_unknown(arg)
            return
        item_name, target_name = [part.strip() for part in arg.split(" on ", 1)]
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
        for use in self.world.uses:
            if use.get("item") == item_id and use.get("target_item") == target_id:
                if not self.world.check_preconditions(use.get("preconditions")):
                    continue
                effect = use.get("effect", {})
                self.world.apply_effect(effect)
                message = use.get("success")
                if message:
                    io.output(message)
                else:
                    io.output(self.messages["use_failure"])
                self._check_end()
                return
        io.output(self.messages["use_failure"])
        self._check_end()

    def cmd_unknown(self, arg: str) -> None:
        io.output(self.messages["unknown_command"])

    def _check_end(self) -> None:
        ending = self.world.check_endings()
        if ending:
            io.output(ending)
            self.running = False


def run(world_data_path: str, language: str = "en") -> None:
    Game(world_data_path, language).run()
