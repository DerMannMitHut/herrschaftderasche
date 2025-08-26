from engine.world import World
import yaml
import pytest


def make_world() -> World:
    data = {
        "items": {
            "crown": {
                "names": ["crown"],
                "state": "broken",
                "states": {
                    "broken": {"description": "A broken crown."},
                    "repaired": {"description": "A repaired crown."},
                },
            }
        },
        "rooms": {
            "room1": {"description": "Room 1.", "items": ["crown"], "exits": {}}
        },
        "start": "room1",
    }
    return World(data)


def test_describe_item_state_changes():
    w = make_world()
    assert w.describe_item("crown") == "A broken crown."
    assert w.set_item_state("crown", "repaired")
    assert w.describe_item("crown") == "A repaired crown."


def test_item_state_saved_and_loaded(tmp_path):
    w = make_world()
    assert w.set_item_state("crown", "repaired")
    save_path = tmp_path / "save.yaml"
    w.save(save_path)

    new = make_world()
    new.load_state(save_path)
    assert new.item_states["crown"] == "repaired"
    assert new.describe_item("crown") == "A repaired crown."
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["item_states"] == {"crown": "repaired"}


@pytest.mark.parametrize(
    "language,item_name,broken_phrase,repaired_phrase,exit_name",
    [
        ("en", "Ashen Crown", "broken crown", "repaired crown", "Black Tower"),
        ("de", "Aschenkrone", "zerbrochene krone", "reparierte krone", "Schwarzer Turm"),
    ],
)
def test_states_from_files(language, item_name, broken_phrase, repaired_phrase, exit_name):
    w = World.from_files("data/generic/world.yaml", f"data/{language}/world.yaml")
    assert w.item_states["ashen_crown"] == "broken"
    assert w.move(exit_name)
    desc = w.describe_item(item_name)
    assert desc is not None
    assert broken_phrase in desc.lower()
    assert w.set_item_state("ashen_crown", "repaired")
    desc = w.describe_item(item_name)
    assert desc is not None
    assert repaired_phrase in desc.lower()
