"""Validation tests for LLM configuration files."""

from __future__ import annotations

import pytest
import yaml
from engine import i18n


def _prepare_i18n(monkeypatch, data_dir):
    engine_dir = data_dir / "engine"
    engine_dir.mkdir()
    monkeypatch.setattr(i18n, "__file__", str(engine_dir / "i18n.py"))


def test_load_llm_config_missing_field(data_dir, monkeypatch, io_backend):
    _prepare_i18n(monkeypatch, data_dir)
    path = data_dir / "data" / "en"
    path.mkdir(parents=True)
    cfg = {
        "context": "ctx",
        "guidance": "guide",
        "ignore_articles": ["the"],
        "ignore_contractions": [],
        "second_object_preps": ["with"],
    }
    with open(path / "llm.en.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh)
    with pytest.raises(SystemExit):
        i18n.load_llm_config("en", io_backend)
    assert any("Missing or empty fields" in o for o in io_backend.outputs)


def test_load_llm_config_empty_field(data_dir, monkeypatch, io_backend):
    _prepare_i18n(monkeypatch, data_dir)
    path = data_dir / "data" / "en"
    path.mkdir(parents=True)
    cfg = {
        "prompt": "",
        "context": "ctx",
        "guidance": "guide",
        "ignore_articles": ["the"],
        "ignore_contractions": [],
        "second_object_preps": ["with"],
    }
    with open(path / "llm.en.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh)
    with pytest.raises(SystemExit):
        i18n.load_llm_config("en", io_backend)
    assert any("Missing or empty fields" in o for o in io_backend.outputs)
