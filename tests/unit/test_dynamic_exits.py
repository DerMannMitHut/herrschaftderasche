from engine.world import World


def test_dynamic_exit_save_and_load(data_dir, tmp_path):
    # Load base world from files (fixtures provide generic + en)
    w = World.from_files(data_dir / "generic/world.yaml", data_dir / "en/world.en.yaml")

    # New exit target that does not exist in the base configuration
    target_id = "room4"

    # Initially, moving to the new target should not be possible
    assert not w.can_move(target_id)

    # Add exit dynamically and verify movement is permitted by id
    w.add_exit("start", target_id)
    assert w.can_move(target_id)

    # State should contain the added exit relative to base
    state = w.to_state()
    assert "exits" in state
    assert state["exits"].get("start", {}).get(target_id, {}) == {}

    # Save and load into a fresh world; exit should be restored
    save_path = tmp_path / "save.yaml"
    w.save(save_path)

    new = World.from_files(data_dir / "generic/world.yaml", data_dir / "en/world.en.yaml")
    assert not new.can_move(target_id)
    new.load_state(save_path)
    assert new.can_move(target_id)
