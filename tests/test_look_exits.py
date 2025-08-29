from engine import game, io


def test_room_description_lists_exits(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.command_processor.cmd_look()
    assert outputs[-1] == "Room 1. Exits: Room 2, Room 3."


def test_room_description_lists_items_npcs_and_exits(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 2")
    g.command_processor.cmd_look()
    assert (
        outputs[-1]
        == "Room 2. You see here: Gem. You see here: Old Man. Exits: Room 1, Room 3."
    )
