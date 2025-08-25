"""Core game loop."""

from engine import io, parser, world, llm, i18n


def run(world_data_path: str, language: str = "en") -> None:
    w = world.World.from_file(world_data_path)
    messages = i18n.load_messages(language)
    go_cmd = messages["cmd_go"]
    exit_cmds = {messages["cmd_quit"], messages["cmd_exit"]}
    io.output(w.describe_current())
    while True:
        command = io.get_input()
        command = llm.interpret(command)
        command = parser.parse(command)
        if command in exit_cmds:
            io.output(messages["farewell"])
            break
        if command.startswith(f"{go_cmd} "):
            direction = command.split(" ", 1)[1]
            if w.move(direction):
                io.output(w.describe_current())
            else:
                io.output(messages["cannot_move"])
        else:
            io.output(messages["unknown_command"])
