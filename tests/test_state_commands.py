import pytest
from engine import game, io


@pytest.mark.parametrize("command", ["destroy", "wear"])
def test_state_command_requires_existing_state(data_dir, monkeypatch, command):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 3")
    assert g.world.take("Sword")
    getattr(g.command_processor, f"cmd_{command}")("Sword")
    assert outputs[-1] == g.language_manager.messages["use_failure"]
    assert "sword" in g.world.inventory
