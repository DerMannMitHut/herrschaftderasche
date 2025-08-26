import sys
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


@pytest.fixture
def data_dir(tmp_path):
    generic = {
        "items": {"sword": {}, "gem": {}},
        "rooms": {
            "start": {"exits": ["room2", "room3"]},
            "room2": {"items": ["gem"], "exits": ["start", "room3"]},
            "room3": {"items": ["sword"], "exits": ["start", "room2"]},
        },
        "start": "start",
    }

    en = {
        "items": {
            "sword": {"names": ["Sword"], "description": "A sharp blade."},
            "gem": {"names": ["Gem"], "description": "A shiny gem."},
        },
        "rooms": {
            "start": {"names": ["Room 1"], "description": "Room 1."},
            "room2": {"names": ["Room 2"], "description": "Room 2."},
            "room3": {"names": ["Room 3"], "description": "Room 3."},
        },
    }

    de = {
        "items": {
            "sword": {"names": ["Schwert"], "description": "Eine scharfe Klinge."},
            "gem": {"names": ["Juwel"], "description": "Ein glänzendes Juwel."},
        },
        "rooms": {
            "start": {"names": ["Raum 1"], "description": "Raum 1."},
            "room2": {"names": ["Raum 2"], "description": "Raum 2."},
            "room3": {"names": ["Raum 3"], "description": "Raum 3."},
        },
    }

    (tmp_path / "generic").mkdir()
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)

    for lang, data in {"en": en, "de": de}.items():
        lang_dir = tmp_path / lang
        lang_dir.mkdir()
        with open(lang_dir / "world.yaml", "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh)

    return tmp_path
