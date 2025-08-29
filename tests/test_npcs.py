import yaml
from engine.world import World
from engine import game, io


def make_world() -> World:
    data = {
        "npcs": {
            "old_man": {
                "state": "unknown",
                "states": {"unknown": {}, "met": {}, "helped": {}},
            }
        },
        "rooms": {"room1": {"description": "Room 1.", "exits": {}}},
        "start": "room1",
    }
    return World(data)


def test_meet_npc_changes_state():
    w = make_world()
    assert w.npc_state("old_man") == "unknown"
    assert w.meet_npc("old_man")
    assert w.npc_state("old_man") == "met"


def test_set_npc_state_changes_state():
    w = make_world()
    assert w.set_npc_state("old_man", "helped")
    assert w.npc_state("old_man") == "helped"


def test_npc_state_saved_and_loaded(tmp_path):
    w = make_world()
    w.meet_npc("old_man")
    save_path = tmp_path / "save.yaml"
    w.save(save_path)
    new = make_world()
    new.load_state(save_path)
    assert new.npc_state("old_man") == "met"
    with open(save_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["npc_states"] == {"old_man": "met"}


def test_npc_event_triggered_on_room_change(data_dir, capsys):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_go("Room 2")
    out = capsys.readouterr().out
    assert "The old man greets you." in out
    assert g.world.npc_state("old_man") == "met"
    g.cmd_go("Room 3")
    capsys.readouterr()
    g.cmd_go("Room 2")
    out = capsys.readouterr().out
    assert "The old man greets you." not in out


def test_npc_event_triggered_on_start(tmp_path, monkeypatch):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()

    generic = {
        "rooms": {"room1": {"exits": []}},
        "start": "room1",
        "npcs": {
            "old_man": {
                "state": "unknown",
                "states": {"unknown": {}, "met": {}},
                "meet": {"location": "room1"},
            }
        },
    }
    en = {
        "rooms": {"room1": {"names": ["Room"], "description": "Room"}},
        "npcs": {"old_man": {"meet": {"text": "Hello there."}}},
    }
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)

    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    monkeypatch.setattr(io, "get_input", lambda: (_ for _ in ()).throw(EOFError()))

    g = game.Game(str(tmp_path / "en" / "world.yaml"), "en")
    g.run()

    assert "Hello there." in outputs


def test_action_requires_npc_met():
    w = make_world()
    pre = {"npc_met": "old_man"}
    assert not w.check_preconditions(pre)
    w.meet_npc("old_man")
    assert w.check_preconditions(pre)


def test_action_requires_npc_help():
    w = make_world()
    pre_help = {"npc_help": "old_man"}
    pre_state = {"npc_state": {"npc": "old_man", "state": "helped"}}
    assert not w.check_preconditions(pre_help)
    assert not w.check_preconditions(pre_state)
    w.npc_states["old_man"] = "helped"
    w.npcs["old_man"].state = "helped"
    assert w.check_preconditions(pre_help)
    assert w.check_preconditions(pre_state)
