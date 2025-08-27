import shutil
from pathlib import Path
import yaml
from engine import game, io


def test_game_reaches_ending(data_dir, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "data" / "generic" / "world.yaml", data_dir / "generic" / "world.yaml")
    shutil.copy(root / "data" / "en" / "world.yaml", data_dir / "en" / "world.yaml")

    with open(data_dir / "generic" / "world.yaml", encoding="utf-8") as fh:
        generic = yaml.safe_load(fh)
    with open(data_dir / "en" / "world.yaml", encoding="utf-8") as fh:
        en = yaml.safe_load(fh)

    open_ruins_effect = generic["uses"]["open_ruins"]["effect"]
    open_ruins_message = en["uses"]["open_ruins"]["success"]
    ending_text = en["endings"]["crown_returned"]

    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))

    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")

    commands = [
        "take Map Fragment",
        "go Forest",
        "take Small Key",
        "go Ruins",
        "take Locked Chest",
        "use Small Key on Locked Chest",
        "effect open_ruins",
        "take Ashen Crown",
        "go Forest",
        "go Ash Village",
    ]

    for entry in commands:
        parts = entry.split(" ", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        if cmd == "effect":
            g.world.apply_effect(open_ruins_effect)
            io.output(open_ruins_message)
        else:
            getattr(g, f"cmd_{cmd}")(arg)

    assert outputs[-1] == ending_text
