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
    assert outputs[-1] == g.messages["language_set"].format(language="de")
    assert g.world.items["key"]["names"][0] == "Schlüssel"
