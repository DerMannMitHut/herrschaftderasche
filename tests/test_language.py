from engine import game, io


GENERIC = {
    "items": {"sword": {}},
    "rooms": {"start": {"items": ["sword"], "exits": []}},
    "start": "start",
}

EN = {
    "items": {"sword": {"names": ["Sword"], "description": "A sharp blade."}},
    "rooms": {"start": {"names": ["Start"], "description": "Start room."}},
}

DE = {
    "items": {"sword": {"names": ["Schwert"], "description": "Eine scharfe Klinge."}},
    "rooms": {"start": {"names": ["Start"], "description": "Startraum."}},
}


def test_language_switch(make_data_dir, monkeypatch):
    data_dir = make_data_dir(generic=GENERIC, en=EN, de=DE)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_language("de")
    assert g.messages["farewell"] == "Auf Wiedersehen!"
    assert g.commands["look"][0] == "umschau"
    assert g.reverse_cmds["hilfe"] == "help"
    assert g.reverse_cmds["language"] == "language"
    assert g.reverse_cmds["sprache"] == "language"
    assert outputs[-1] == g.messages["language_set"].format(language="de")
    assert g.world.items["sword"]["names"][0] == "Schwert"


def test_language_persistence(make_data_dir, monkeypatch):
    data_dir = make_data_dir(generic=GENERIC, en=EN, de=DE)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_language("de")
    g.cmd_quit("")
    g2 = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g2.language == "de"
    assert g2.messages["farewell"] == "Auf Wiedersehen!"
    assert g2.reverse_cmds["language"] == "language"


def test_language_command_base_word(make_data_dir, monkeypatch):
    data_dir = make_data_dir(generic=GENERIC, en=EN, de=DE)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "de" / "world.yaml"), "de")
    cmd = g.reverse_cmds["language"]
    getattr(g, f"cmd_{cmd}")("en")
    assert g.language == "en"
    assert outputs[-1] == g.messages["language_set"].format(language="en")
