import pytest
from engine import game


@pytest.mark.parametrize("command", ["destroy", "wear"])
def test_state_command_requires_existing_state(data_dir, io_backend, command):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    getattr(g.command_processor, f"cmd_{command}")("Sword")
    assert io_backend.outputs[-1] == g.language_manager.messages["use_failure"]
    assert "sword" in g.world.inventory
