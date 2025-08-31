from engine import game


def test_use_success(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    assert g.world.move("Room 2")
    g.command_processor.cmd_use("Sword", "Gem")
    assert g.world.item_states["gem"] == "green"
    success_msg = next(
        a["messages"]["success"]
        for a in g.world.actions
        if a.get("trigger") == "use" and a.get("item") == "sword" and a.get("target_item") == "gem"
    )
    assert io_backend.outputs[-3:] == [success_msg, "", "The gem is green."]


def test_use_item_in_room(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 2")
    assert g.world.take("Gem")
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    assert g.world.move("Room 2")
    assert g.world.drop("Sword")
    g.command_processor.cmd_use("Sword", "Gem")
    assert g.world.item_states["gem"] == "green"
    success_msg = next(
        a["messages"]["success"]
        for a in g.world.actions
        if a.get("trigger") == "use" and a.get("item") == "sword" and a.get("target_item") == "gem"
    )
    assert io_backend.outputs[-3:] == [success_msg, "", "The gem is green."]


def test_use_invalid(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    assert g.world.move("Room 2")
    assert g.world.take("Gem")
    assert g.world.move("Room 3")
    g.command_processor.cmd_use("Sword", "Gem")
    assert g.world.item_states["gem"] == "red"
    assert io_backend.outputs[-1] == g.language_manager.messages["use_failure"]
