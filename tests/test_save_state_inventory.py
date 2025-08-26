from engine.world import World
import yaml


def make_world() -> World:
    data = {
        "items": {
            "sword": {"names": ["sword"]},
            "crown": {"names": ["crown"]},
        },
        "rooms": {
            "room1": {
                "description": "Room 1.",
                "exits": {"room2": ["Room 2"], "room3": ["Room 3"]},
            },
            "room2": {
                "description": "Room 2.",
                "items": ["sword"],
                "exits": {"room1": ["Room 1"], "room3": ["Room 3"]},
            },
            "room3": {
                "description": "Room 3.",
                "items": ["crown"],
                "exits": {"room1": ["Room 1"], "room2": ["Room 2"]},
            },
        },
        "start": "room1",
    }
    return World(data)


def test_to_state_only_differences():
    w = make_world()
    assert w.to_state() == {"current": "room1"}

    assert w.move("Room 2")
    assert w.take("sword")
    assert w.to_state() == {
        "current": "room2",
        "inventory": ["sword"],
        "rooms": {"room2": []},
    }

    assert w.move("Room 1")
    assert w.move("Room 3")
    assert w.drop("sword")
    assert w.to_state() == {
        "current": "room3",
        "rooms": {"room2": [], "room3": ["crown", "sword"]},
    }


def test_load_state_applies_differences(tmp_path):
    w = make_world()
    w.move("Room 2")
    w.take("sword")
    w.move("Room 1")
    w.move("Room 3")
    w.drop("sword")
    save_path = tmp_path / "save.yaml"
    w.save(save_path)

    new = make_world()
    new.load_state(save_path)

    assert new.current == "room3"
    assert new.inventory == []
    assert new.rooms["room2"].get("items", []) == []
    assert new.rooms["room3"].get("items", []) == ["crown", "sword"]
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert "inventory" not in data
    assert data["rooms"] == {"room2": [], "room3": ["crown", "sword"]}
