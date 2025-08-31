import pytest
from engine.world import World
from pydantic import ValidationError


def make_world(action: dict):
    data = {
        "start": "room",
        "rooms": {"room": {"names": ["Room"], "description": ""}},
        "actions": [action],
    }
    return World(data)


def test_invalid_action_preconditions():
    with pytest.raises(ValidationError):
        make_world({"preconditions": []})


def test_invalid_action_effect():
    with pytest.raises(ValidationError):
        make_world({"effect": []})
