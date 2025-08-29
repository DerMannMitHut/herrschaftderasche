from pathlib import Path
import shutil

from engine import game


def test_ruins_inaccessible_without_map(data_dir, io_backend):
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / "data" / "generic" / "world.yaml", data_dir / "generic" / "world.yaml")
    shutil.copy(root / "data" / "en" / "world.yaml", data_dir / "en" / "world.yaml")

    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
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

