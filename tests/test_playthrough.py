import shutil
from pathlib import Path
import yaml
from engine import game, io


def test_game_reaches_ending(data_dir, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "data" / "generic" / "world.yaml", data_dir / "generic" / "world.yaml")
    shutil.copy(root / "data" / "en" / "world.yaml", data_dir / "en" / "world.yaml")

    with open(data_dir / "en" / "world.yaml", encoding="utf-8") as fh:
        en = yaml.safe_load(fh)
    ending_text = en["endings"]["crown_returned"]

    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))

    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")

    commands = [
        lambda: g.cmd_take("Small Key"),
        lambda: g.cmd_go("Forest"),
        lambda: g.cmd_go("Ash Village"),
        lambda: g.cmd_take("Map Fragment"),
        lambda: g.cmd_go("Forest"),
        lambda: g.cmd_talk("Ashram"),
        lambda: g.cmd_show("Map Fragment", "Ashram"),
        lambda: g.cmd_go("Hut"),
        lambda: g.cmd_go("Ruins"),
        lambda: g.cmd_use("Small Key", "Locked Chest"),
        lambda: g.cmd_examine("Locked Chest"),
        lambda: g.cmd_go("Forest"),
        lambda: g.cmd_go("Ash Village"),
    ]

    for func in commands:
        func()

    assert outputs[-1] == ending_text
