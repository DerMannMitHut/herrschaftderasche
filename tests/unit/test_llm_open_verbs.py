"""Tests for language-based open verb normalization in the LLM."""

from engine import world
from engine.language import LanguageManager
from engine.llm import OllamaLLM
from tests.conftest import DummyIO


def test_open_like_verbs_use_language(data_dir):
    """Open verbs defined in translations map to the 'use' command."""

    generic = data_dir / "generic" / "world.yaml"
    lang_world = data_dir / "en" / "world.en.yaml"
    w = world.World.from_files(generic, lang_world)
    lm = LanguageManager(data_dir, "de", DummyIO())
    llm = OllamaLLM()
    llm.set_context(w, lm, [])

    verb, obj, add = llm._normalize_mapping("öffne", "Kiste", "Schlüssel")

    assert (verb, obj, add) == ("use", "Schlüssel", "Kiste")
