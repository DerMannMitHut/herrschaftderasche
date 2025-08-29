from engine import game, io


def test_look_item_describes(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.command_processor.cmd_examine("gem")
    assert outputs[-1] == "A red gem."


def test_look_item_not_present(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.command_processor.cmd_examine("sword")
    assert outputs[-1] == g.language_manager.messages["item_not_present"]
