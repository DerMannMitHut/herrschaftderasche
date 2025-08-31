import yaml
from engine import game
from engine.world_model import LocationTag


def test_end_condition_inventory_and_location(data_dir, io_backend):
    generic = {
        "items": {"crown": {}},
        "rooms": {
            "room1": {"items": ["crown"], "exits": ["room2"]},
            "room2": {"items": [], "exits": []},
        },
        "start": "room1",
        "endings": {
            "win": {
                "preconditions": {
                    "is_location": "room2",
                    "item_conditions": [
                        {
                            "item": "crown",
                            "location": LocationTag.INVENTORY.value,
                        }
                    ],
                }
            }
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
    with open(data_dir / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(data_dir / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_take("Crown")
    g.command_processor.cmd_go("Room2")
    assert io_backend.outputs[-1] == "You win!"


def test_end_condition_inventory_lacks(data_dir, io_backend):
    generic = {
        "items": {"crown": {}},
        "rooms": {
            "room1": {"items": ["crown"], "exits": ["room2"]},
            "room2": {"items": [], "exits": []},
        },
        "start": "room1",
        "endings": {
            "fail": {
                "preconditions": {
                    "is_location": "room2",
                    "item_conditions": [{"item": "crown", "location": "room1"}],
                }
            }
        },
    }
    en = {
        "items": {"crown": {"names": ["Crown"], "description": ""}},
        "rooms": {
            "room1": {"names": ["Room1"], "description": "Room1"},
            "room2": {"names": ["Room2"], "description": "Room2"},
        },
        "endings": {"fail": "No crown, no victory."},
    }
    with open(data_dir / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(data_dir / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Room2")
    assert io_backend.outputs[-1] == "No crown, no victory."


def test_end_condition_or_room_has(data_dir, io_backend):
    generic = {
        "items": {"sword": {}},
        "rooms": {
            "room1": {"items": [], "exits": ["room2"]},
            "room2": {"items": ["sword"], "exits": []},
        },
        "start": "room1",
        "endings": {
            "done": {
                "preconditions": {
                    "is_location": "room2",
                    "item_conditions": [{"item": "sword", "location": "room2"}],
                }
            }
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
    with open(data_dir / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(data_dir / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Room2")
    assert io_backend.outputs[-1] == "You see the sword and know your quest is over."


def test_end_condition_item_state(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g._check_end()
    assert io_backend.outputs == []
    assert g.world.set_item_state("gem", "green")
    g._check_end()
    assert io_backend.outputs[-1] == "The gem is green."
