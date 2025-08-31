from engine import game


def test_room_description_lists_exits(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_look()
    assert io_backend.outputs[-1] == "Room 1. Exits: Room 2, Room 3."


def test_room_description_lists_items_npcs_and_exits(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 2")
    g.command_processor.cmd_look()
    assert io_backend.outputs[-3] == "Room 2. Exits: Room 1, Room 3."
    assert io_backend.outputs[-2] == ""
    assert io_backend.outputs[-1] == "You see here: Gem, Old Man."
