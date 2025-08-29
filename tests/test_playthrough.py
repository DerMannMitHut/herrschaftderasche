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

    cp = g.command_processor
    commands = [
        lambda: cp.cmd_take("Small Key"),
        lambda: cp.cmd_go("Forest"),
        lambda: cp.cmd_go("Ash Village"),
        lambda: cp.cmd_talk("Villager"),
        lambda: cp.cmd_take("Map Fragment"),
        lambda: cp.cmd_go("Forest"),
        lambda: cp.cmd_talk("Ashram"),
        lambda: cp.cmd_show("Map Fragment", "Ashram"),
        lambda: cp.cmd_go("Hut"),
        lambda: cp.cmd_go("Ruins"),
        lambda: cp.cmd_use("Small Key", "Locked Chest"),
        lambda: cp.cmd_examine("Locked Chest"),
        lambda: cp.cmd_go("Forest"),
        lambda: cp.cmd_go("Ash Village"),
    ]

    for func in commands:
        func()

    assert outputs[-1] == ending_text
