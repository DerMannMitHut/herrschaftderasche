from engine import game, io


def test_missing_argument(monkeypatch, data_dir):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.command_processor.cmd_take("")
    assert outputs[-1] == g.language_manager.messages["unknown_command"]


def test_too_many_arguments(monkeypatch, data_dir):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.command_processor.execute("inventory extra")
    assert outputs[-1] == g.language_manager.messages["unknown_command"]
