from engine import game


def test_missing_argument(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_take("")
    assert io_backend.outputs[-1] == g.language_manager.messages["unknown_command"]


def test_too_many_arguments(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.execute("inventory extra")
    assert io_backend.outputs[-1] == g.language_manager.messages["unknown_command"]
