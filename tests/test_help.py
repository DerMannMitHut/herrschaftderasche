import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from engine import game, io


def test_help_lists_commands(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game("data/en/world.yaml", "en")
    g.cmd_help("")
    names = []
    for key in g.command_keys:
        val = g.commands.get(key)
        if isinstance(val, list):
            names.append(val[0])
        else:
            names.append(val)
    expected = g.messages["help"].format(commands=", ".join(names))
    assert outputs[-1] == expected
