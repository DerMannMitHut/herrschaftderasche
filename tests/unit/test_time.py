from engine.game import Game
from engine.world_model import Action


def test_time_advances_default(data_dir, io_backend, llm_backend):
    io_backend.inputs = [
        "look",
        "go Room 2",
        "quit",
    ]
    g = Game(str(data_dir / "generic/world.yaml"), language="en", io_backend=io_backend, llm_backend=llm_backend)
    assert g.world.time == 0
    g.run()
    # 3 successful commands
    assert g.world.time == 3


def test_move_duration_override(data_dir, io_backend, llm_backend):
    io_backend.inputs = [
        "go Room 2",
        "quit",
    ]
    g = Game(str(data_dir / "generic/world.yaml"), language="en", io_backend=io_backend, llm_backend=llm_backend)
    # set custom duration for exit start -> room2
    g.world.rooms["start"].exits["room2"]["duration"] = 5
    g.run()
    # go (5 TU) + quit (1 TU)
    assert g.world.time == 6


def test_action_duration_override(data_dir, io_backend, llm_backend):
    io_backend.inputs = [
        "go Room 2",
        "use Sword Gem",
        "quit",
    ]
    g = Game(str(data_dir / "generic/world.yaml"), language="en", io_backend=io_backend, llm_backend=llm_backend)
    # set duration for the only defined action in fixture (use sword on gem)
    for i, act in enumerate(g.world.actions):
        if act.trigger == "use" and act.item == "sword" and act.target_item == "gem":
            # replace with a new Action including duration to ensure pydantic model update
            g.world.actions[i] = Action(
                trigger=act.trigger,
                item=act.item,
                target_item=act.target_item,
                target_npc=act.target_npc,
                preconditions=act.preconditions,
                effect=act.effect,
                duration=9,
                messages=act.messages,
            )
            break
    g.run()
    # go (1) + use (9) + quit (1)
    assert g.world.time == 11
