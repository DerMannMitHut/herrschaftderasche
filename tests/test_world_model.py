import pytest
from pydantic import ValidationError

from engine.world_model import Action, Item, Npc, Room


def test_room_dataclass():
    room = Room(
        names=["Hall"],
        description="Desc",
        items=["key"],
        exits={"north": {"names": ["North"]}},
        occupants=["npc"],
    )
    assert room.names[0] == "Hall"
    assert room.items == ["key"]
    assert "north" in room.exits
    assert room.occupants == ["npc"]


def test_item_dataclass():
    item = Item(names=["Key"], description="A key", state="new", states={"new": {}})
    assert item.names[0] == "Key"
    assert item.state == "new"
    assert "new" in item.states


def test_npc_dataclass():
    npc = Npc(
        names=["Bob"],
        state="idle",
        states={"idle": {}, "met": {}},
        meet={"location": "town"},
    )
    assert npc.names[0] == "Bob"
    assert npc.meet["location"] == "town"
    assert npc.state == "idle"


def test_action_dataclass():
    action = Action(
        trigger="use",
        item="key",
        target_item="door",
        preconditions={"is_location": "hall"},
        effect={"item_conditions": [{"item": "door", "state": "open"}]},
        messages={"success": "opened"},
    )
    assert action.trigger == "use"
    assert action.item == "key"
    assert action.messages["success"] == "opened"
