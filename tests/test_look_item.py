from engine import game, io


GENERIC = {
    "items": {"gem": {}},
    "rooms": {
        "room1": {"exits": ["room2"]},
        "room2": {"items": ["gem"], "exits": ["room1"]},
    },
    "start": "room1",
}

EN = {
    "items": {"gem": {"names": ["Gem"], "description": "A shiny gem."}},
    "rooms": {
        "room1": {"names": ["Room 1"], "description": "Room 1."},
        "room2": {"names": ["Room 2"], "description": "Room 2."},
    },
}


def test_look_item_describes(make_data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    data_dir = make_data_dir(generic=GENERIC, en=EN)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.cmd_look("gem")
    assert outputs[-1] == "A shiny gem."


def test_look_item_not_present(make_data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    data_dir = make_data_dir(generic=GENERIC, en=EN)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.cmd_look("sword")
    assert outputs[-1] == g.messages["item_not_present"]
