import shutil
from pathlib import Path

from engine import game


def test_talk_with_ashram_unlocks_ruins_exit(data_dir):
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "data" / "generic" / "world.yaml", data_dir / "generic" / "world.yaml")
    shutil.copy(root / "data" / "en" / "world.yaml", data_dir / "en" / "world.yaml")

    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")

    g.cmd_go("Forest")
    assert "ruins" not in g.world.rooms["forest"].get("exits", {})

    g.cmd_take("Map Fragment")
    g.cmd_talk("Ashram")

    assert g.world.item_states.get("map_fragment") == "readable"
    assert "ruins" in g.world.rooms["forest"].get("exits", {})

    g.cmd_go("Ruins")
    assert g.world.current == "ruins"
