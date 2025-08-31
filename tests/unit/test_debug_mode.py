from engine import game
from engine.world_model import StateTag


def test_debug_outputs_after_state_changes(data_dir, capsys):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", debug=True)
    capsys.readouterr()
    g.command_processor.cmd_go("Room 2")
    err = capsys.readouterr().err
    assert "-- location room2" in err
    assert "-- npc old_man state met" in err

    g.command_processor.cmd_take("Gem")
    err = capsys.readouterr().err
    assert "-- inventory ['gem']" in err
    assert "-- room room2 items []" in err

    g.world.set_item_state("gem", "green")
    err = capsys.readouterr().err
    assert "-- item gem state green" in err

    g.world.set_npc_state("old_man", StateTag.HELPED)
    err = capsys.readouterr().err
    assert "-- npc old_man state helped" in err
