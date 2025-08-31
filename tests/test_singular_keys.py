import copy
from typing import Any

import pytest

from engine import world


BASE_DATA = {
    "items": {
        "key": {"states": {"unused": {}}},
        "door": {},
    },
    "rooms": {
        "room": {"exits": []},
        "room2": {"exits": []},
    },
    "npcs": {"bob": {"state": "met", "states": {"met": {}}}},
    "start": "room",
}


@pytest.mark.parametrize(
    "section,bad_key,payload",
    [
        ("preconditions", "item_condition", {"item": "key", "state": "unused"}),
        ("preconditions", "npc_condition", {"npc": "bob", "state": "met"}),
        ("effect", "add_exit", {"room": "room", "target": "room2"}),
    ],
)
def test_singular_keys_raise(section, bad_key, payload):
    data = copy.deepcopy(BASE_DATA)
    action: dict[str, Any] = {
        "trigger": "use",
        "item": "key",
        "target_item": "door",
    }
    action[section] = {bad_key: payload}
    data["actions"] = [action]
    with pytest.raises(ValueError, match=bad_key):
        world.World(data)
