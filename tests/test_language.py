from engine import game, io


def test_language_switch(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_language("de")
    assert g.messages["farewell"] == "Auf Wiedersehen!"
    assert g.commands["look"][0] == "umschau"
    assert g.commands["examine"][0] == "ansehen"
    assert g.reverse_cmds["hilfe"][0] == "help"
    assert g.reverse_cmds["language"][0] == "language"
    assert g.reverse_cmds["sprache"][0] == "language"
    assert outputs[-1] == g.messages["language_set"].format(language="de")
    assert g.world.items["sword"]["names"][0] == "Schwert"


def test_language_persistence(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_language("de")
    g.cmd_quit("")
    g2 = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g2.language == "de"
    assert g2.messages["farewell"] == "Auf Wiedersehen!"
    assert g2.reverse_cmds["language"][0] == "language"
    assert g2.world.items["sword"]["names"][0] == "Schwert"


def test_language_command_base_word(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "de" / "world.yaml"), "de")
    cmd, _ = g.reverse_cmds["language"]
    getattr(g, f"cmd_{cmd}")("en")
    assert g.language == "en"
    assert outputs[-1] == g.messages["language_set"].format(language="en")
