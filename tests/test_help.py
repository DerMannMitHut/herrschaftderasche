from engine import game, io


def test_help_lists_commands(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_help("")
    names = []
    for key in g.command_keys:
        val = g.commands.get(key)
        if isinstance(val, list):
            first = val[0]
            if isinstance(first, list):
                names.append(first[0])
            else:
                names.append(first)
        else:
            names.append(val)
    expected = g.messages["help"].format(commands=", ".join(names))
    assert outputs[-1] == expected
