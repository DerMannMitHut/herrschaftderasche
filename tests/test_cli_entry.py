import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_cli_module_entry(data_dir, tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    main_src = Path(__file__).resolve().parents[1] / "game" / "main.py"
    shutil.copy(main_src, game_dir / "main.py")
    (game_dir / "__init__.py").write_text("")
    shutil.copytree(data_dir, tmp_path / "data")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-m", "game.main", "--language", "en"],
        input="",
        text=True,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Room 1." in result.stdout
