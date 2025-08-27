from engine import game


def test_talk_changes_state_and_outputs_text(data_dir, capsys):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_go("Room 2")
    capsys.readouterr()
    g.cmd_talk("")
    out = capsys.readouterr().out
    assert "You tell the old man about your quest. He agrees to help." in out
    assert g.world.npc_state("old_man") == "helped"
    g.cmd_talk("")
    out = capsys.readouterr().out
    assert "The old man has already offered his aid." in out
