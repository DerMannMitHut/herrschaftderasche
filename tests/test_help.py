from engine import game, io


GENERIC = {"rooms": {"start": {"exits": []}}, "start": "start"}
EN = {"rooms": {"start": {"names": ["Start"], "description": "Start room."}}}


def test_help_lists_commands(make_data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    data_dir = make_data_dir(generic=GENERIC, en=EN)
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_help("")
    names = []
    for key in g.command_keys:
        val = g.commands.get(key)
        if isinstance(val, list):
            names.append(val[0])
        else:
            names.append(val)
    expected = g.messages["help"].format(commands=", ".join(names))
    assert outputs[-1] == expected
