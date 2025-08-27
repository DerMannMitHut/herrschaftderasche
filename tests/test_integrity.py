import shutil
from pathlib import Path

import pytest
import yaml

from engine import game


def copy_data(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[1] / "data"
    dest = tmp_path / "data"
    shutil.copytree(src, dest)
    return dest


def test_invalid_exit_causes_error(tmp_path, capsys):
    data_dir = copy_data(tmp_path)
    generic_world_path = data_dir / "generic" / "world.yaml"
    with open(generic_world_path, encoding="utf-8") as fh:
        world_data = yaml.safe_load(fh)
    world_data["rooms"]["ash_village"]["exits"].append("nowhere")
    with open(generic_world_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(world_data, fh)

    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    out = capsys.readouterr().out
    assert "nowhere" in out


def test_invalid_save_reference_leaves_file(tmp_path, capsys):
    data_dir = copy_data(tmp_path)
    save_path = data_dir / "save.yaml"
    with open(save_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump({"current": "ash_village", "inventory": ["unknown"], "language": "en"}, fh)

    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    out = capsys.readouterr().out
    assert "unknown" in out
    assert save_path.exists()
