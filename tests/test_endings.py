import yaml
from engine import game, io


def test_end_condition_inventory_and_location(tmp_path, monkeypatch):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {
        "items": {"crown": {}},
        "rooms": {
            "room1": {"items": ["crown"], "exits": ["room2"]},
            "room2": {"items": [], "exits": []},
        },
        "start": "room1",
        "endings": {
            "win": "inventory has crown AND room1 lacks crown AND at room2"
        },
    }
    en = {
        "items": {"crown": {"names": ["Crown"], "description": ""}},
        "rooms": {
            "room1": {"names": ["Room1"], "description": "Room1"},
            "room2": {"names": ["Room2"], "description": "Room2"},
        },
        "endings": {"win": "You win!"},
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(tmp_path / "en" / "world.yaml"), "en")
    g.cmd_take("Crown")
    g.cmd_go("Room2")
    assert outputs[-1] == "You win!"


def test_end_condition_inventory_lacks(tmp_path, monkeypatch):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {
        "items": {"crown": {}},
        "rooms": {
            "room1": {"items": ["crown"], "exits": ["room2"]},
            "room2": {"items": [], "exits": []},
        },
        "start": "room1",
        "endings": {"fail": "inventory lacks crown AND at room2"},
    }
    en = {
        "items": {"crown": {"names": ["Crown"], "description": ""}},
        "rooms": {
            "room1": {"names": ["Room1"], "description": "Room1"},
            "room2": {"names": ["Room2"], "description": "Room2"},
        },
        "endings": {"fail": "No crown, no victory."},
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(tmp_path / "en" / "world.yaml"), "en")
    g.cmd_go("Room2")
    assert outputs[-1] == "No crown, no victory."


def test_end_condition_or_room_has(tmp_path, monkeypatch):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {
        "items": {"sword": {}},
        "rooms": {
            "room1": {"items": [], "exits": ["room2"]},
            "room2": {"items": ["sword"], "exits": []},
        },
        "start": "room1",
        "endings": {
            "done": "inventory has sword OR room2 has sword AND at room2"
        },
    }
    en = {
        "items": {"sword": {"names": ["Sword"], "description": ""}},
        "rooms": {
            "room1": {"names": ["Room1"], "description": "Room1"},
            "room2": {"names": ["Room2"], "description": "Room2"},
        },
        "endings": {"done": "You see the sword and know your quest is over."},
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(tmp_path / "en" / "world.yaml"), "en")
    g.cmd_go("Room2")
    assert outputs[-1] == "You see the sword and know your quest is over."

