from engine import game
from engine.world_model import StateTag


def test_talk_requires_npc_name(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Room 2")
    ok = g.command_processor.cmd_talk("")
    assert ok is False


def test_talk_dialog_sets_state(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Room 2")
    io_backend.inputs = ["1"]
    g.command_processor.cmd_talk("Old Man")
    assert "You tell the old man about your quest. He agrees to help." in io_backend.outputs
    assert g.world.npc_state("old_man") == StateTag.HELPED
