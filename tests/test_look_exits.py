import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from engine import game, io


def test_room_description_lists_exits(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(ROOT_DIR / "data" / "en" / "world.yaml"), "en")
    g.cmd_look("")
    assert outputs[-1] == (
        "A small village at the edge of the ash wastes. Most huts lie in ruins, only a few people remain. "
        "Exits: Grey Forest, Black Tower."
    )


def test_room_description_lists_items_and_exits(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(ROOT_DIR / "data" / "en" / "world.yaml"), "en")
    g.world.move("forest")
    g.cmd_look("")
    assert outputs[-1] == (
        "Charred trees rise like blackened fingers into the sky. Beneath the ash, tender green sprouts push through. "
        "You see here: Flame Blade. Exits: Ash Village, Glow Chasm."
    )
