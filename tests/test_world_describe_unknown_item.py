from engine.world import World


def test_describe_current_handles_unknown_item(data_dir):
    world = World.from_files(
        data_dir / "generic/world.yaml", data_dir / "en/world.yaml"
    )
    world.rooms[world.current].items.append("ghost")
    assert "ghost" in world.describe_current()
