import pytest
import yaml

from engine import game, io, integrity, world


def test_invalid_exit_causes_error(data_dir, capsys):
    generic_world_path = data_dir / "generic" / "world.yaml"
    with open(generic_world_path, encoding="utf-8") as fh:
        world_data = yaml.safe_load(fh)
    world_data["rooms"]["start"]["exits"].append("nowhere")
    with open(generic_world_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(world_data, fh)

    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    out = capsys.readouterr().out
    assert "nowhere" in out


def test_invalid_save_reference_leaves_file(data_dir, capsys):
    save_path = data_dir / "save.yaml"
    with open(save_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump({"current": "start", "inventory": ["unknown"], "language": "en"}, fh)

    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    out = capsys.readouterr().out
    assert "unknown" in out
    assert save_path.exists()


def test_invalid_npc_location_causes_error(data_dir, capsys):
    generic_world_path = data_dir / "generic" / "world.yaml"
    with open(generic_world_path, encoding="utf-8") as fh:
        world_data = yaml.safe_load(fh)
    world_data["npcs"]["old_man"]["meet"]["location"] = "nowhere"
    with open(generic_world_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(world_data, fh)
    with pytest.raises(SystemExit):
        game.Game(str(data_dir / "en" / "world.yaml"), "en")
    out = capsys.readouterr().out
    assert "nowhere" in out


def test_missing_action_translation_warns(data_dir, monkeypatch):
    en_path = data_dir / "en" / "world.yaml"
    with open(en_path, encoding="utf-8") as fh:
        en_world = yaml.safe_load(fh)
    en_world["actions"].pop("cut_gem")
    with open(en_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(en_world, fh)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert any("Missing translation for action 'cut_gem'" in o for o in outputs)


def test_validate_save_finds_errors(data_dir):
    w = world.World.from_files(
        data_dir / "generic" / "world.yaml", data_dir / "en" / "world.yaml"
    )
    data = {
        "current": "nowhere",
        "inventory": ["ghost"],
        "rooms": {"room2": ["ghost"], "nowhere": ["sword"]},
        "item_states": {"ghost": "none", "sword": "rusty"},
        "npc_states": {"unknown": "happy", "old_man": "sleeping"},
    }
    errors = integrity.validate_save(data, w)
    assert any("missing room 'nowhere'" in e for e in errors)
    assert any("missing item 'ghost' in inventory" in e for e in errors)
    assert any("missing item 'ghost' in room 'room2'" in e for e in errors)
    assert any("missing item 'ghost' in item_states" in e for e in errors)
    assert any("missing state 'rusty' for item 'sword'" in e for e in errors)
    assert any("missing NPC 'unknown'" in e for e in errors)
    assert any("missing state 'sleeping' for NPC 'old_man'" in e for e in errors)


def test_check_translations_reports_warnings(data_dir):
    en_dir = data_dir / "en"
    de_dir = data_dir / "de"
    generic_dir = data_dir / "generic"
    with open(en_dir / "messages.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump({"farewell": "bye", "hello": "hi"}, fh)
    with open(de_dir / "messages.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump({"farewell": "tschüss", "extra": "x"}, fh)
    with open(generic_dir / "commands.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(["go", "quit"], fh)
    with open(de_dir / "commands.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump({"go": "geh", "jump": "spring"}, fh)
    with open(de_dir / "world.yaml", encoding="utf-8") as fh:
        de_world = yaml.safe_load(fh)
    de_world["items"].pop("sword")
    de_world["items"]["ghost"] = {}
    de_world["rooms"].pop("start")
    de_world["rooms"]["nowhere"] = {}
    de_world["actions"].pop("cut_gem")
    de_world["actions"]["extra"] = {}
    with open(de_dir / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(de_world, fh)
    warnings = integrity.check_translations("de", data_dir)
    assert "Missing translation for message 'hello'" in warnings
    assert "Unused message translation 'extra' ignored" in warnings
    assert "Missing translation for command 'quit'" in warnings
    assert "Unused command translation 'jump' ignored" in warnings
    assert "Missing translation for item 'sword'" in warnings
    assert "Translation for unused item 'ghost' ignored" in warnings
    assert "Missing translation for room 'start'" in warnings
    assert "Translation for unused room 'nowhere' ignored" in warnings
    assert "Missing translation for action 'cut_gem'" in warnings
    assert "Translation for unused action 'extra' ignored" in warnings
