import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from engine import game, io


def test_look_item_describes(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game("data/en/world.yaml", "en")
    g.cmd_look("key")
    assert outputs[-1] == "A small brass key."


def test_look_item_not_present(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game("data/en/world.yaml", "en")
    g.world.move("forest")
    g.cmd_look("key")
    assert outputs[-1] == g.messages["item_not_present"]

