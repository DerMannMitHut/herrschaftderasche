import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from engine import game, io


def test_language_switch(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game("data/en/world.yaml", "en")
    g.cmd_language("de")
    assert g.messages["farewell"] == "Auf Wiedersehen!"
    assert g.commands["look"][0] == "umschau"
    assert g.reverse_cmds["hilfe"] == "help"
    assert g.reverse_cmds["language"] == "language"
    assert g.reverse_cmds["sprache"] == "language"
    assert outputs[-1] == g.messages["language_set"].format(language="de")
    assert g.world.items["key"]["names"][0] == "Schlüssel"


def test_language_persistence(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game("data/en/world.yaml", "en")
    g.cmd_language("de")
    g.cmd_quit("")
    g2 = game.Game("data/en/world.yaml", "en")
    assert g2.language == "de"
    assert g2.messages["farewell"] == "Auf Wiedersehen!"
    assert g2.reverse_cmds["language"] == "language"


def test_language_command_base_word(monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game("data/de/world.yaml", "de")
    cmd = g.reverse_cmds["language"]
    getattr(g, f"cmd_{cmd}")("en")
    assert g.language == "en"
    assert outputs[-1] == g.messages["language_set"].format(language="en")
