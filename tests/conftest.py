import sys
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


@pytest.fixture
def make_data_dir(tmp_path):
    def _make_data_dir(*, generic, **languages):
        (tmp_path / "generic").mkdir()
        with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
            yaml.safe_dump(generic, fh)
        for lang, data in languages.items():
            lang_dir = tmp_path / lang
            lang_dir.mkdir()
            with open(lang_dir / "world.yaml", "w", encoding="utf-8") as fh:
                yaml.safe_dump(data, fh)
        return tmp_path

    return _make_data_dir
