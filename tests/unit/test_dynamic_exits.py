from engine.world import World


def test_dynamic_exit_save_and_load(data_dir, tmp_path):
    w = World.from_files(data_dir / "generic/world.yaml", data_dir / "en/world.en.yaml")
    target_id = "room4"
    assert not w.can_move(target_id)
    w.add_exit("start", target_id)
    assert w.can_move(target_id)
    state = w.to_state()
    assert "exits" in state
    assert state["exits"].get("start", {}).get(target_id, {}) == {}
    save_path = tmp_path / "save.yaml"
    w.save(save_path)

    new = World.from_files(data_dir / "generic/world.yaml", data_dir / "en/world.en.yaml")
    assert not new.can_move(target_id)
    new.load_state(save_path)
    assert new.can_move(target_id)
