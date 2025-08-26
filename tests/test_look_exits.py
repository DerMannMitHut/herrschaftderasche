import yaml
from engine import game, io


def make_game(tmp_path):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {
        "items": {"gem": {}},
        "rooms": {
            "room1": {"exits": ["room2", "room3"]},
            "room2": {"items": ["gem"], "exits": ["room1", "room3"]},
            "room3": {"exits": ["room1", "room2"]},
        },
        "start": "room1",
    }
    en = {
        "items": {"gem": {"names": ["Gem"], "description": "A shiny gem."}},
        "rooms": {
            "room1": {"names": ["Room 1"], "description": "Room 1."},
            "room2": {"names": ["Room 2"], "description": "Room 2."},
            "room3": {"names": ["Room 3"], "description": "Room 3."},
        },
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    return game.Game(str(tmp_path / "en" / "world.yaml"), "en")


def test_room_description_lists_exits(tmp_path, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = make_game(tmp_path)
    g.cmd_look("")
    assert outputs[-1] == "Room 1. Exits: Room 2, Room 3."


def test_room_description_lists_items_and_exits(tmp_path, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = make_game(tmp_path)
    assert g.world.move("Room 2")
    g.cmd_look("")
    assert outputs[-1] == "Room 2. You see here: Gem. Exits: Room 1, Room 3."
