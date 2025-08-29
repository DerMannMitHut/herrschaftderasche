import pytest

from engine import game, io


def test_game_init_missing_world(data_dir, monkeypatch):
    (data_dir / "generic" / "world.yaml").unlink()
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert any("Missing world file" in o for o in outputs)


def test_game_init_corrupted_world(data_dir, monkeypatch):
    with open(data_dir / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        fh.write("- : - invalid yaml")
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert any("Invalid world file" in o for o in outputs)


def test_game_init_corrupted_save(data_dir, monkeypatch):
    with open(data_dir / "save.yaml", "w", encoding="utf-8") as fh:
        fh.write("- : - invalid yaml")
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert any("save file" in o for o in outputs)

