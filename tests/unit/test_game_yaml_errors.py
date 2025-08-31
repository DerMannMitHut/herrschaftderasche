import pytest

from engine import game


def test_game_init_missing_world(data_dir, io_backend):
    (data_dir / "generic" / "world.yaml").unlink()
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert any("Missing world file" in o for o in io_backend.outputs)


def test_game_init_corrupted_world(data_dir, io_backend):
    with open(data_dir / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        fh.write("- : - invalid yaml")
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert any("Invalid world file" in o for o in io_backend.outputs)


def test_game_init_corrupted_save(data_dir, io_backend):
    with open(data_dir / "save.yaml", "w", encoding="utf-8") as fh:
        fh.write("- : - invalid yaml")
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    assert any("save file" in o for o in io_backend.outputs)

