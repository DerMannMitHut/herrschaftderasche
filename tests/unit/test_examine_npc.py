from engine import game


def test_examine_npc_shows_state_text(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    # Move to the room where the NPC is present (room2 -> "Room 2")
    assert g.command_processor.cmd_go("Room 2")
    # Clear any meeting text from outputs fixture to isolate examine output
    io_backend.outputs.clear()

    ok = g.command_processor.cmd_examine("Old Man")
    assert ok is True
    # Fallback to state's generic text if no explicit "examine" provided
    assert io_backend.outputs[-1] == "The old man nods at you."


def test_examine_npc_not_present_outputs_message(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    # In start room, NPC is not present
    ok = g.command_processor.cmd_examine("Old Man")
    assert ok is True  # command understood as NPC name
    assert io_backend.outputs[-1] == g.language_manager.messages["no_npc"]
