from engine import game


def test_look_item_describes(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 2")
    g.command_processor.cmd_examine("gem")
    assert io_backend.outputs[-1] == "A red gem."


def test_look_item_not_present(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 2")
    g.command_processor.cmd_examine("sword")
    assert io_backend.outputs[-1] == g.language_manager.messages["item_not_present"]
