"""Core game loop."""

from engine import io, parser, world, llm, i18n


def run(world_data_path: str, language: str = "en") -> None:
    w = world.World.from_file(world_data_path)
    messages = i18n.load_messages(language)
    command_keys = i18n.load_command_keys()
    commands = i18n.load_commands(language)
    reverse_cmds = {}
    for key in command_keys:
        val = commands.get(key)
        if isinstance(val, list):
            for name in val:
                reverse_cmds[name] = key
        else:
            reverse_cmds[val] = key
    io.output(w.describe_current(messages))
    while True:
        raw = io.get_input()
        raw = llm.interpret(raw)
        raw = parser.parse(raw)
        cmd_word, *rest = raw.split(" ", 1)
        cmd_key = reverse_cmds.get(cmd_word)
        arg = rest[0] if rest else ""
        if cmd_key == "quit":
            io.output(messages["farewell"])
            break
        if cmd_key == "inventory":
            io.output(w.describe_inventory(messages))
            continue
        if cmd_key == "take" and arg:
            item = arg
            if w.take(item):
                io.output(messages["taken"].format(item=item))
            else:
                io.output(messages["item_not_present"])
            continue
        if cmd_key == "drop" and arg:
            item = arg
            drop_suffix = commands.get("drop_suffix", "")
            if drop_suffix and item.endswith(f" {drop_suffix}"):
                item = item[: -len(drop_suffix) - 1].strip()
            if w.drop(item):
                io.output(messages["dropped"].format(item=item))
            else:
                io.output(messages["not_carrying"])
            continue
        if cmd_key == "go" and arg:
            direction = arg
            if w.move(direction):
                io.output(w.describe_current(messages))
            else:
                io.output(messages["cannot_move"])
        else:
            io.output(messages["unknown_command"])
