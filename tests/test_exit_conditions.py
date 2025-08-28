from pathlib import Path
import shutil

from engine import game, io


def test_ruins_inaccessible_without_map(data_dir, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "data" / "generic" / "world.yaml", data_dir / "generic" / "world.yaml")
    shutil.copy(root / "data" / "en" / "world.yaml", data_dir / "en" / "world.yaml")

    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))

    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_go("Forest")
    assert g.world.current == "forest"

    g.cmd_go("Ruins")
    assert g.world.current == "forest"
    assert outputs[-1] == g.messages["cannot_move"]

    g.cmd_take("Map Fragment")
    g.cmd_use("Map Fragment", "Map Fragment")
    g.cmd_go("Ruins")
    assert g.world.current == "ruins"

