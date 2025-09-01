from __future__ import annotations

import requests
from engine import game, world
from engine.language import LanguageManager
from engine.llm import OllamaLLM


def test_take_with_german_article(data_dir, io_backend):
    g = game.Game(str(data_dir / "de" / "world.de.yaml"), "de", io_backend=io_backend)
    # Move to room3 where the item resides in the test fixture
    assert g.world.move("Raum 3")
    # Use an article; the command synonyms include 'nimm $a'
    assert g.command_processor.execute("nimm das schwert") is True
    # Item should be in inventory and a 'taken' message produced
    assert any("Schwert" in o for o in io_backend.outputs)


def test_drop_with_german_article(data_dir, io_backend):
    g = game.Game(str(data_dir / "de" / "world.de.yaml"), "de", io_backend=io_backend)
    # Put item into inventory directly for the drop
    g.world.inventory.append("sword")
    assert g.command_processor.execute("lege das schwert ab") is True
    # After dropping, inventory should be empty
    assert "sword" not in g.world.inventory


def test_llm_maps_look_object_to_examine(monkeypatch, data_dir):
    # Build minimal world and language context
    generic = data_dir / "generic" / "world.yaml"
    en = data_dir / "en" / "world.en.yaml"

    class _IO:
        def get_input(self, prompt: str = "> ") -> str:  # noqa: D401 - simple stub
            _ = prompt
            return ""

        def output(self, text: str) -> None:  # noqa: D401 - simple stub
            _ = text
            return None

    io = _IO()
    w = world.World.from_files(generic, en)
    lm = LanguageManager(data_dir, "en", io)

    llm = OllamaLLM()
    llm.set_context(w, lm, [])

    class _Resp:
        def json(self):  # noqa: D401 - simple stub
            # Simulate LLM choosing 'look' with an object at high confidence
            return {"message": {"content": '{"confidence": 2, "verb": "look", "object": "Gem"}'}}

    def fake_post(_url, **_kwargs):  # noqa: D401 - simple stub
        return _Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    mapped = llm.interpret("see the gem")
    assert mapped == "examine Gem"
