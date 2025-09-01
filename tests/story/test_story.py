import shutil
from pathlib import Path

import yaml
from engine import game


def _project_root(file: str) -> Path:
    p = Path(file).resolve()
    return p.parents[2] if p.parents[1].name == "tests" else p.parents[1]


def copy_story_world(data_dir) -> None:
    root = _project_root(__file__)
    shutil.copy(root / "data" / "generic" / "world.yaml", data_dir / "generic" / "world.yaml")
    shutil.copy(root / "data" / "en" / "world.en.yaml", data_dir / "en" / "world.en.yaml")


def test_ruins_inaccessible_without_map(data_dir, io_backend):
    copy_story_world(data_dir)
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Forest")
    assert g.world.current == "forest"

    g.command_processor.cmd_go("Ruins")
    assert g.world.current == "forest"
    assert io_backend.outputs[-1] == g.language_manager.messages["cannot_move"]

    g.command_processor.cmd_go("Ash Village")
    g.command_processor.cmd_talk("Villager")
    g.command_processor.cmd_take("Map Fragment")
    g.command_processor.cmd_go("Forest")
    g.command_processor.cmd_talk("Ashram")
    g.command_processor.cmd_show("Map Fragment", "Ashram")
    g.command_processor.cmd_go("Hut")
    g.command_processor.cmd_go("Ruins")
    assert g.world.current == "ruins"


def test_examine_closed_chest_reveals_no_crown(data_dir, io_backend):
    copy_story_world(data_dir)
    with open(data_dir / "en" / "world.en.yaml", encoding="utf-8") as fh:
        en = yaml.safe_load(fh)

    closed_desc = en["items"]["chest"]["states"]["closed"]["description"]
    open_success = en["actions"]["open_chest"]["messages"]["success"]
    open_desc = en["items"]["chest"]["states"]["open"]["description"]
    crown_msg = en["actions"]["find_crown"]["messages"]["success"]

    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    cp = g.command_processor
    g.world.current = "ruins"

    cp.cmd_examine("Locked Chest")
    assert io_backend.outputs == [closed_desc]
    assert "ashen_crown" not in g.world.inventory

    g.world.inventory.append("small_key")
    cp.cmd_use("Small Key", "Locked Chest")
    cp.cmd_examine("Locked Chest")

    assert io_backend.outputs[-3:] == [open_success, open_desc, crown_msg]
    assert "ashen_crown" in g.world.inventory


def test_game_reaches_ending(data_dir, io_backend):
    copy_story_world(data_dir)
    with open(data_dir / "en" / "world.en.yaml", encoding="utf-8") as fh:
        en = yaml.safe_load(fh)
    ending_text = en["endings"]["crown_returned"]

    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)

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

    assert io_backend.outputs[-1] == ending_text
