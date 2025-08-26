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
    assert w.to_state() == {"current": "ash_village"}

    # Move to the forest and take the flame blade
    assert w.move("forest")
    assert w.take("blade")
    assert w.to_state() == {
        "current": "grey_forest",
        "inventory": ["flame_blade"],
        "rooms": {"grey_forest": []},
    }

    # Drop the blade in the black tower; inventory reverts to base so it's omitted
    assert w.move("village")
    assert w.move("tower")
    assert w.drop("blade")
    assert w.to_state() == {
        "current": "black_tower",
        "rooms": {"grey_forest": [], "black_tower": ["ashen_crown", "flame_blade"]},
    }


def test_load_state_applies_differences(tmp_path):
    w = World.from_files(GENERIC, EN)
    w.move("forest")
    w.take("blade")
    w.move("village")
    w.move("tower")
    w.drop("blade")
    save_path = tmp_path / "save.yaml"
    w.save(save_path)

    # Load the state into a fresh world and ensure it matches
    new = World.from_files(GENERIC, EN)
    new.load_state(save_path)

    assert new.current == "black_tower"
    assert new.inventory == []
    assert new.rooms["grey_forest"].get("items", []) == []
    assert new.rooms["black_tower"].get("items", []) == ["ashen_crown", "flame_blade"]
    # The saved state should be minimal
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert "inventory" not in data
    assert data["rooms"] == {"grey_forest": [], "black_tower": ["ashen_crown", "flame_blade"]}
