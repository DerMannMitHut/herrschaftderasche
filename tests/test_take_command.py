from engine import game


def test_take_uses_canonical_name(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 3")
    g.command_processor.cmd_take("sword")
    assert (
        io_backend.outputs[-1]
        == g.language_manager.messages["taken"].format(item="Sword")
    )
