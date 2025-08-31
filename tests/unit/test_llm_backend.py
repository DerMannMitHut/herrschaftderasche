"""Tests for the Ollama LLM backend."""

from __future__ import annotations

import requests
from engine import world
from engine.language import LanguageManager
from engine.llm import OllamaLLM
from engine.persistence import LogEntry
from tests.conftest import DummyIO


def _make_world(data_dir):
    generic = data_dir / "generic" / "world.yaml"
    lang = data_dir / "en" / "world.en.yaml"
    io = DummyIO()
    w = world.World.from_files(generic, lang)
    lm = LanguageManager(data_dir, "en", io)
    return w, lm


def test_ollama_llm_builds_context(monkeypatch, data_dir):
    """System prompt should contain room, NPC and state information."""

    w, lm = _make_world(data_dir)
    llm = OllamaLLM()
    log = [LogEntry("look", ["Room 1."])]
    llm.set_context(w, lm, log)

    captured: dict = {}

    def fake_post(_url, json, _timeout):  # noqa: D401 - simple stub
        captured["json"] = json

        class Resp:
            def json(self) -> dict:  # pragma: no cover - trivial
                return {"message": {"content": '{"verb": "look"}'}}

        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    llm.interpret("look around")

    system_prompt = captured["json"]["messages"][0]["content"]
    assert "Room 1." in system_prompt
    assert "Old Man" in system_prompt
    assert "red" in system_prompt
    assert "look" in system_prompt


def test_ollama_llm_fallback(monkeypatch, data_dir):
    """If the request fails the original command is returned."""

    w, lm = _make_world(data_dir)
    llm = OllamaLLM()
    llm.set_context(w, lm, [])

    def fake_post(*_args, **_kwargs):  # pragma: no cover - simple stub
        raise OSError

    monkeypatch.setattr(requests, "post", fake_post)
    assert llm.interpret("test command") == "test command"
