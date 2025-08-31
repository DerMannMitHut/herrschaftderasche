from engine import game


def test_log_records_state_changes_and_show_log(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert "show_log" in g.language_manager.commands
    assert "show_log" in g.language_manager.command_info
    g.command_processor.execute("look")
    assert g.command_processor.log == []
    g.command_processor.execute("go room 2")
    g.command_processor.execute("take gem")
    assert [e.command for e in g.command_processor.log] == ["go room 2", "take gem"]
    g.command_processor.execute("show_log 1")
    assert io_backend.outputs[-1].splitlines()[0] == "|> take gem"


def test_log_persisted_in_savegame(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.execute("go room 2")
    g.save_manager.save(
        g.world, g.language_manager.language, g.command_processor.log
    )
    io2 = io_backend.__class__()
    g2 = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io2)
    assert [e.command for e in g2.command_processor.log] == ["go room 2"]
