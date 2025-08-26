import yaml
import pytest
from pathlib import Path
from engine import game, io, parser


def make_data_dir(tmp_path: Path) -> Path:
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {
        "items": {"sword": {}},
        "rooms": {"start": {"items": ["sword"], "exits": []}},
        "start": "start",
    }
    en = {
        "items": {"sword": {"names": ["Sword"], "description": "A sharp blade."}},
        "rooms": {"start": {"names": ["Start"], "description": "Start room."}},
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    return tmp_path


def test_save_on_eoferror(tmp_path, monkeypatch):
    data_dir = make_data_dir(tmp_path)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")

    def fake_input(prompt: str = "> ") -> str:  # noqa: ARG001
        raise EOFError

    monkeypatch.setattr(io, "get_input", fake_input)
    g.run()
    save_path = data_dir / "save.yaml"
    assert save_path.exists()
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["current"] == "start"


def test_save_on_exception(tmp_path, monkeypatch):
    data_dir = make_data_dir(tmp_path)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    monkeypatch.setattr(io, "get_input", lambda prompt="> ": "look")

    def boom(cmd: str) -> str:  # noqa: ARG001
        raise ValueError("boom")

    monkeypatch.setattr(parser, "parse", boom)
    with pytest.raises(ValueError):
        g.run()
    save_path = data_dir / "save.yaml"
    assert save_path.exists()
