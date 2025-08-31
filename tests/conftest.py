import sys
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from engine.interfaces import IOBackend, LLMBackend  # noqa: E402


class DummyIO(IOBackend):
    def __init__(self, inputs: list[str] | None = None) -> None:
        self.inputs = inputs or []
        self.outputs: list[str] = []

    def get_input(self, prompt: str = "> ") -> str:  # noqa: ARG002 - test stub
        return self.inputs.pop(0) if self.inputs else ""

    def output(self, text: str) -> None:
        self.outputs.append(text)


class DummyLLM(LLMBackend):
    def interpret(self, command: str) -> str:  # noqa: D401 - simple stub
        return command

    def set_context(self, world, language, log) -> None:  # noqa: ARG002 - test stub
        return None


@pytest.fixture
def io_backend() -> DummyIO:
    return DummyIO()


@pytest.fixture
def llm_backend() -> DummyLLM:
    return DummyLLM()


@pytest.fixture
def data_dir(tmp_path):
    generic = {
        "items": {
            "sword": {},
            "gem": {"state": "red", "states": {"red": {}, "green": {}}},
        },
        "rooms": {
            "start": {"exits": ["room2", "room3"]},
            "room2": {"items": ["gem"], "exits": ["start", "room3"]},
            "room3": {"items": ["sword"], "exits": ["start", "room2"]},
        },
        "npcs": {
            "old_man": {
                "state": "unknown",
                "states": {"unknown": {}, "met": {}, "helped": {}},
                "meet": {"location": "room2"},
            }
        },
        "actions": {
            "cut_gem": {
                "trigger": "use",
                "item": "sword",
                "target_item": "gem",
                "preconditions": {"is_location": "room2"},
                "effect": {"item_conditions": [{"item": "gem", "state": "green"}]},
            }
        },
        "start": "start",
        "endings": {"green_gem": {"preconditions": {"item_conditions": [{"item": "gem", "state": "green"}]}}},
    }

    en = {
        "items": {
            "sword": {
                "names": ["Sword"],
                "description": "A sharp blade.",
            },
            "gem": {
                "names": ["Gem"],
                "states": {
                    "red": {"description": "A red gem."},
                    "green": {"description": "A green gem."},
                },
            },
        },
        "rooms": {
            "start": {"names": ["Room 1"], "description": "Room 1."},
            "room2": {"names": ["Room 2"], "description": "Room 2."},
            "room3": {"names": ["Room 3"], "description": "Room 3."},
        },
        "npcs": {
            "old_man": {
                "names": ["Old Man"],
                "meet": {"text": "The old man greets you."},
                "states": {
                    "met": {
                        "text": "The old man nods at you.",
                        "talk": "You tell the old man about your quest. He agrees to help.",
                    },
                    "helped": {
                        "text": "The old man smiles at you.",
                        "talk": "The old man has already offered his aid.",
                    },
                },
            }
        },
        "actions": {"cut_gem": {"messages": {"success": "The gem now gleams green."}}},
        "endings": {"green_gem": "The gem is green."},
    }

    de = {
        "items": {
            "sword": {
                "names": ["Schwert"],
                "description": "Eine scharfe Klinge.",
            },
            "gem": {
                "names": ["Juwel"],
                "states": {
                    "red": {"description": "Ein rotes Juwel."},
                    "green": {"description": "Ein grünes Juwel."},
                },
            },
        },
        "rooms": {
            "start": {"names": ["Raum 1"], "description": "Raum 1."},
            "room2": {"names": ["Raum 2"], "description": "Raum 2."},
            "room3": {"names": ["Raum 3"], "description": "Raum 3."},
        },
        "npcs": {
            "old_man": {
                "names": ["Alter Mann"],
                "meet": {"text": "Der alte Mann grüßt dich."},
                "states": {
                    "met": {
                        "text": "Der alte Mann nickt dir zu.",
                        "talk": "Du erzählst dem alten Mann von deiner Suche. Er hilft dir.",
                    },
                    "helped": {
                        "text": "Der alte Mann lächelt dich an.",
                        "talk": "Der alte Mann hat dir bereits geholfen.",
                    },
                },
            }
        },
        "actions": {"cut_gem": {"messages": {"success": "Das Juwel leuchtet jetzt grün."}}},
        "endings": {"green_gem": "Das Juwel ist grün."},
    }

    (tmp_path / "generic").mkdir()
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)

    for lang, data in {"en": en, "de": de}.items():
        lang_dir = tmp_path / lang
        lang_dir.mkdir()
        with open(lang_dir / f"world.{lang}.yaml", "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh)

    return tmp_path
