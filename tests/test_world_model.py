from engine.world_model import Action, Item, Npc, Room


def test_item_dataclass():
    item = Item(names=["Key"], description="A key", state="unused")
    assert item.names == ["Key"]
    assert item.description == "A key"
    assert item.state == "unused"
    assert item.states == {}


def test_room_dataclass():
    room = Room(names=["Hall"], description="Desc", items=["key"], exits={"north": {"names": ["north"]}})
    assert room.names[0] == "Hall"
    assert room.description == "Desc"
    assert room.items == ["key"]
    assert "north" in room.exits


def test_npc_dataclass():
    npc = Npc(names=["Bob"], state="met", states={"met": {}}, meet={"location": "hall"})
    assert npc.names == ["Bob"]
    assert npc.state == "met"
    assert "met" in npc.states
    assert npc.meet["location"] == "hall"


def test_action_dataclass():
    action = Action(trigger="use", item="key", target_item="door", messages={"success": "ok"})
    assert action.trigger == "use"
    assert action.item == "key"
    assert action.target_item == "door"
    assert action.messages["success"] == "ok"
