import yaml
import pytest
from engine import game, parser


def test_save_on_eoferror(data_dir, monkeypatch, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)

    def fake_input(prompt: str = "> ") -> str:  # noqa: ARG001
        raise EOFError

    monkeypatch.setattr(io_backend, "get_input", fake_input)
    g.run()
    save_path = data_dir / "save.yaml"
    assert save_path.exists()
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["current"] == "start"


def test_save_on_exception(data_dir, monkeypatch, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    monkeypatch.setattr(io_backend, "get_input", lambda prompt="> ": "look")

    def boom(cmd: str) -> str:  # noqa: ARG001
        raise ValueError("boom")

    monkeypatch.setattr(parser, "parse", boom)
    with pytest.raises(ValueError):
        g.run()
    save_path = data_dir / "save.yaml"
    assert save_path.exists()
