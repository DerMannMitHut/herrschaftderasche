"""LLM fallback should trigger when classic parse can't resolve args."""

from __future__ import annotations

from pathlib import Path

from engine import game
from engine.interfaces import LLMBackend
from tests.conftest import DummyIO


class MappingLLM(LLMBackend):
    """Map German 'nimm den Schlüssel' to an executable command.

    We return the engine's command ID form so it works regardless of language
    patterns (the engine allows calling commands by their ID).
    """

    def __init__(self, mapped: str) -> None:
        self.mapped = mapped

    def set_context(self, world, language, log) -> None:  # noqa: D401, ARG002
        return None

    def interpret(self, command: str) -> str:  # noqa: D401, ARG002
        return self.mapped


def test_llm_fallback_on_unresolvable_argument_triggers_mapping():
    # Use real DE data that includes the small key in the hut.
    data_path = Path("data/de/world.de.yaml").resolve()
    io = DummyIO(inputs=["nimm den Schlüssel", "inventar", "beenden"])  # de commands
    # Map to command ID form to avoid language coupling in the test.
    llm = MappingLLM("take Kleiner Schlüssel")

    g = game.Game(str(data_path), "de", io_backend=io, llm_backend=llm)
    g.run()

    # After running, the small key should be in inventory and inventory printed.
    assert "small_key" in g.world.inventory
    # And the output should show the inventory line with the German item name.
    assert any("Du trägst:" in line and "Kleiner Schlüssel" in line for line in io.outputs)
