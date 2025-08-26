import yaml
from engine import game, io


def make_game(tmp_path):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {
        "items": {"gem": {}},
        "rooms": {
            "room1": {"exits": ["room2"]},
            "room2": {"items": ["gem"], "exits": ["room1"]},
        },
        "start": "room1",
    }
    en = {
        "items": {"gem": {"names": ["Gem"], "description": "A shiny gem."}},
        "rooms": {
            "room1": {"names": ["Room 1"], "description": "Room 1."},
            "room2": {"names": ["Room 2"], "description": "Room 2."},
        },
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    return game.Game(str(tmp_path / "en" / "world.yaml"), "en")


def test_look_item_describes(tmp_path, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = make_game(tmp_path)
    assert g.world.move("Room 2")
    g.cmd_look("gem")
    assert outputs[-1] == "A shiny gem."


def test_look_item_not_present(tmp_path, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = make_game(tmp_path)
    assert g.world.move("Room 2")
    g.cmd_look("sword")
    assert outputs[-1] == g.messages["item_not_present"]
