from engine import game, io
from engine.world_model import Action, Item, LocationTag


def test_examine_triggers_action(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)

    g.world.items["stone"] = Item(names=["Stone"], description="A stone.")
    g.world.items["coin"] = Item(names=["Coin"], description="A coin.")
    g.world.rooms["start"].setdefault("items", []).append("stone")
    g.world.actions.append(
        Action(
            trigger="examine",
            item="stone",
            effect={"item_condition": {"item": "coin", "location": LocationTag.CURRENT_ROOM}},
            messages={"success": "You find a coin."},
        )
    )

    g.command_processor.describe_item("Stone")

    assert io_backend.outputs[-2:] == ["A stone.", "You find a coin."]
    assert "coin" in g.world.rooms[g.world.current].get("items", [])
