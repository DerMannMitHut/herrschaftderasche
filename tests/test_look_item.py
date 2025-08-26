import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from engine import game, io


def test_look_item_describes(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(ROOT_DIR / "data" / "en" / "world.yaml"), "en")
    g.world.move("forest")
    g.cmd_look("blade")
    assert outputs[-1] == "A sword forged in the heart of fire. The blade glows faintly in the dark."


def test_look_item_not_present(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(ROOT_DIR / "data" / "en" / "world.yaml"), "en")
    g.world.move("forest")
    g.cmd_look("crown")
    assert outputs[-1] == g.messages["item_not_present"]

