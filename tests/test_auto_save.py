import yaml
import pytest
from engine import game, io, parser


GENERIC = {
    "items": {"sword": {}},
    "rooms": {"start": {"items": ["sword"], "exits": []}},
    "start": "start",
}

EN = {
    "items": {"sword": {"names": ["Sword"], "description": "A sharp blade."}},
    "rooms": {"start": {"names": ["Start"], "description": "Start room."}},
}


def test_save_on_eoferror(make_data_dir, monkeypatch):
    data_dir = make_data_dir(generic=GENERIC, en=EN)
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


def test_save_on_exception(make_data_dir, monkeypatch):
    data_dir = make_data_dir(generic=GENERIC, en=EN)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    monkeypatch.setattr(io, "get_input", lambda prompt="> ": "look")

    def boom(cmd: str) -> str:  # noqa: ARG001
        raise ValueError("boom")

    monkeypatch.setattr(parser, "parse", boom)
    with pytest.raises(ValueError):
        g.run()
    save_path = data_dir / "save.yaml"
    assert save_path.exists()
