import yaml
from engine.world import World
from engine import game


def make_world() -> World:
    data = {
        "npcs": {
            "old_man": {
                "state": "unknown",
                "states": {"unknown": {}, "met": {}},
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
