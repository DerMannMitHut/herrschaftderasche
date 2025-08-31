from engine import game
from engine.world_model import StateTag


def test_talk_requires_npc_name(data_dir, capsys):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en")
    g.command_processor.cmd_go("Room 2")
    capsys.readouterr()
    g.command_processor.cmd_talk("")
    out = capsys.readouterr().out
    assert "I didn't understand that." in out


def test_talk_changes_state_and_outputs_text(data_dir, capsys):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en")
    g.command_processor.cmd_go("Room 2")
    capsys.readouterr()
    g.command_processor.cmd_talk("Old Man")
    out = capsys.readouterr().out
    assert "You tell the old man about your quest. He agrees to help." in out
    assert g.world.npc_state("old_man") == StateTag.HELPED
    g.command_processor.cmd_talk("Old Man")
    out = capsys.readouterr().out
    assert "The old man has already offered his aid." in out
