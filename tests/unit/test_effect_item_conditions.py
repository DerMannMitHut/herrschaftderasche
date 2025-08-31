from engine import game
from engine.world_model import LocationTag


def test_apply_effect_multiple_item_conditions(data_dir):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en")
    assert "sword" in g.world.rooms["room3"]["items"]
    g.world.apply_effect(
        {
            "item_conditions": [
                {"item": "gem", "state": "green"},
                {"item": "sword", "location": LocationTag.INVENTORY},
            ]
        }
    )
    assert g.world.item_states["gem"] == "green"
    assert "sword" in g.world.inventory
    assert "sword" not in g.world.rooms["room3"]["items"]
