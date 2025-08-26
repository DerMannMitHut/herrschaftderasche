import sys
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from engine.world import World

GENERIC = ROOT_DIR / 'data' / 'generic' / 'world.yaml'
EN = ROOT_DIR / 'data' / 'en' / 'world.yaml'

def test_to_state_only_differences():
    w = World.from_files(GENERIC, EN)
    # Unchanged world should only store current position
    assert w.to_state() == {"current": "hut"}

    # Taking the key removes it from hut and puts it into inventory
    assert w.take("key")
    assert w.to_state() == {
        "current": "hut",
        "inventory": ["key"],
        "rooms": {"hut": []},
    }

    # Drop the key in the forest; inventory reverts to base so it's omitted
    assert w.move("forest")
    assert w.drop("key")
    assert w.to_state() == {
        "current": "forest",
        "rooms": {"hut": [], "forest": ["key"]},
    }


def test_load_state_applies_differences(tmp_path):
    w = World.from_files(GENERIC, EN)
    w.take("key")
    w.move("forest")
    w.drop("key")
    save_path = tmp_path / "save.yaml"
    w.save(save_path)

    # Load the state into a fresh world and ensure it matches
    new = World.from_files(GENERIC, EN)
    new.load_state(save_path)

    assert new.current == "forest"
    assert new.inventory == []
    assert new.rooms["hut"].get("items", []) == []
    assert new.rooms["forest"].get("items", []) == ["key"]
    # The saved state should be minimal
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert "inventory" not in data
    assert data["rooms"] == {"hut": [], "forest": ["key"]}
