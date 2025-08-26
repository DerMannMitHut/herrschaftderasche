"""Core game loop."""

from engine import io, parser, world, llm, i18n


def run(world_data_path: str, language: str = "en") -> None:
    w = world.World.from_file(world_data_path)
    messages = i18n.load_messages(language)
    go_cmd = messages["cmd_go"]
    take_cmd = messages["cmd_take"]
    drop_cmd = messages["cmd_drop"]
    inventory_cmd = messages["cmd_inventory"]
    exit_cmds = {messages["cmd_quit"], messages["cmd_exit"]}
    io.output(w.describe_current(messages))
    while True:
        command = io.get_input()
        command = llm.interpret(command)
        command = parser.parse(command)
        if command in exit_cmds:
            io.output(messages["farewell"])
            break
        if command == inventory_cmd:
            io.output(w.describe_inventory(messages))
            continue
        if command.startswith(f"{take_cmd} "):
            item = command.split(" ", 1)[1]
            if w.take(item):
                io.output(messages["taken"].format(item=item))
            else:
                io.output(messages["item_not_present"])
            continue
        if command.startswith(f"{drop_cmd} "):
            item = command.split(" ", 1)[1]
            if item.endswith(" ab"):
                item = item[:-3].strip()
            if w.drop(item):
                io.output(messages["dropped"].format(item=item))
            else:
                io.output(messages["not_carrying"])
            continue
        if command.startswith(f"{go_cmd} "):
            direction = command.split(" ", 1)[1]
            if w.move(direction):
                io.output(w.describe_current(messages))
            else:
                io.output(messages["cannot_move"])
        else:
            io.output(messages["unknown_command"])
