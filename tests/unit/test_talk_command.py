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
    g.command_processor.cmd_talk("Old Man")
    assert any(o.startswith("O1:") for o in io_backend.outputs)
    g.command_processor.cmd_say("O1")
    assert "You tell the old man about your quest. He agrees to help." in io_backend.outputs
    assert g.world.npc_state("old_man") == StateTag.HELPED


def test_say_without_dialog_returns_false(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    ok = g.command_processor.cmd_say("O1")
    assert ok is False


def test_invalid_option_shows_message(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Room 2")
    g.command_processor.cmd_talk("Old Man")
    io_backend.outputs.clear()
    g.command_processor.cmd_say("O2")
    assert "You can't say that." in io_backend.outputs


def test_options_listed_in_look(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_go("Room 2")
    g.command_processor.cmd_talk("Old Man")
    io_backend.outputs.clear()
    g.command_processor.cmd_look()
    assert "O1: I need your help." in io_backend.outputs
