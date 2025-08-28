from engine import game


def test_apply_effect_multiple_item_conditions(data_dir):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert "sword" in g.world.rooms["room3"]["items"]
    g.world.apply_effect(
        {
            "item_condition": [
                {"item": "gem", "state": "green"},
                {"item": "sword", "location": "INVENTORY"},
            ]
        }
    )
    assert g.world.item_states["gem"] == "green"
    assert "sword" in g.world.inventory
    assert "sword" not in g.world.rooms["room3"]["items"]

