"""Core game loop."""

from pathlib import Path

from engine import io, parser, world, llm, i18n


class Game:
    def __init__(self, world_data_path: str, language: str) -> None:
        data_path = Path(world_data_path)
        self.save_path = data_path.parent.parent / "save.yaml"
        self.world = world.World.from_file(world_data_path)
        if self.save_path.exists():
            self.world.load_state(self.save_path)
        self.messages = i18n.load_messages(language)
        self.commands = i18n.load_commands(language)
        command_keys = i18n.load_command_keys()
        self.reverse_cmds: dict[str, str] = {}
        for key in command_keys:
            val = self.commands.get(key)
            if isinstance(val, list):
                for name in val:
                    self.reverse_cmds[name] = key
            else:
                self.reverse_cmds[val] = key
        self.running = True

    def run(self) -> None:
        io.output(self.world.describe_current(self.messages))
        while self.running:
            raw = io.get_input()
            raw = llm.interpret(raw)
            raw = parser.parse(raw)
            cmd_word, *rest = raw.split(" ", 1)
            cmd_key = self.reverse_cmds.get(cmd_word)
            arg = rest[0] if rest else ""
            handler = getattr(self, f"cmd_{cmd_key}", self.cmd_unknown)
            handler(arg)

    def cmd_quit(self, arg: str) -> None:
        self.world.save(self.save_path)
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

    def cmd_drop(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        item = arg
        drop_suffix = self.commands.get("drop_suffix", "")
        if drop_suffix and item.endswith(f" {drop_suffix}"):
            item = item[: -len(drop_suffix) - 1].strip()
        if self.world.drop(item):
            io.output(self.messages["dropped"].format(item=item))
        else:
            io.output(self.messages["not_carrying"])

    def cmd_go(self, arg: str) -> None:
        if not arg:
            self.cmd_unknown(arg)
            return
        direction = arg
        if self.world.move(direction):
            io.output(self.world.describe_current(self.messages))
        else:
            io.output(self.messages["cannot_move"])

    def cmd_unknown(self, arg: str) -> None:
        io.output(self.messages["unknown_command"])


def run(world_data_path: str, language: str = "en") -> None:
    Game(world_data_path, language).run()
