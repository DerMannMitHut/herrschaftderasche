from engine import game, io


GENERIC = {
    "items": {"gem": {}},
    "rooms": {
        "room1": {"exits": ["room2", "room3"]},
        "room2": {"items": ["gem"], "exits": ["room1", "room3"]},
        "room3": {"exits": ["room1", "room2"]},
    },
    "start": "room1",
}

EN = {
    "items": {"gem": {"names": ["Gem"], "description": "A shiny gem."}},
    "rooms": {
        "room1": {"names": ["Room 1"], "description": "Room 1."},
        "room2": {"names": ["Room 2"], "description": "Room 2."},
        "room3": {"names": ["Room 3"], "description": "Room 3."},
    },
}


def test_room_description_lists_exits(make_data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    data_dir = make_data_dir(generic=GENERIC, en=EN)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_look("")
    assert outputs[-1] == "Room 1. Exits: Room 2, Room 3."


def test_room_description_lists_items_and_exits(make_data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    data_dir = make_data_dir(generic=GENERIC, en=EN)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.cmd_look("")
    assert outputs[-1] == "Room 2. You see here: Gem. Exits: Room 1, Room 3."
