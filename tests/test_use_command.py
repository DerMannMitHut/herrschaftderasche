from engine import game, io


def test_use_success(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    assert g.world.move("Room 2")
    g.cmd_use("Sword", "Gem")
    assert g.world.item_states["gem"] == "green"
    success_msg = next(
        a.messages["success"]
        for a in g.world.actions
        if a.trigger == "use"
        and a.item == "sword"
        and a.target_item == "gem"
    )
    assert outputs[-2:] == [success_msg, "The gem is green."]


def test_use_item_in_room(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    assert g.world.take("Gem")
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    assert g.world.move("Room 2")
    assert g.world.drop("Sword")
    g.cmd_use("Sword", "Gem")
    assert g.world.item_states["gem"] == "green"
    success_msg = next(
        a.messages["success"]
        for a in g.world.actions
        if a.trigger == "use"
        and a.item == "sword"
        and a.target_item == "gem"
    )
    assert outputs[-2:] == [success_msg, "The gem is green."]


def test_use_invalid(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    assert g.world.move("Room 2")
    assert g.world.take("Gem")
    assert g.world.move("Room 3")
    g.cmd_use("Sword", "Gem")
    assert g.world.item_states["gem"] == "red"
    assert outputs[-1] == g.messages["use_failure"]

