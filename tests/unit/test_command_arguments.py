from engine import game


def test_missing_argument(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    ok = g.command_processor.cmd_take("")
    assert ok is False


def test_too_many_arguments(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    ok = g.command_processor.execute("inventory extra")
    assert ok is False
