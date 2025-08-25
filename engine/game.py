"""Core game loop."""

from engine import io, parser, world, llm


def run(world_data_path: str) -> None:
    w = world.World.from_file(world_data_path)
    io.output(w.describe_current())
    while True:
        command = io.get_input()
        command = llm.interpret(command)
        command = parser.parse(command)
        if command in {"quit", "exit"}:
            io.output("Auf Wiedersehen!")
            break
        if command.startswith("gehe "):
            direction = command.split(" ", 1)[1]
            if w.move(direction):
                io.output(w.describe_current())
            else:
                io.output("Dort kannst du nicht hin.")
        else:
            io.output("Das habe ich nicht verstanden.")
