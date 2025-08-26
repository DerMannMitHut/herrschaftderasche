from engine import game, io


def test_look_item_describes(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.cmd_look("gem")
    assert outputs[-1] == "A shiny gem."


def test_look_item_not_present(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.cmd_look("sword")
    assert outputs[-1] == g.messages["item_not_present"]
