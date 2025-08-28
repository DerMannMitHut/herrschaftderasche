from engine import game, io


def test_help_lists_commands(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_help("")
    names = []
    for key in g.command_keys:
        val = g.commands.get(key, [])
        entries = val if isinstance(val, list) else [val]
        first = entries[0]
        names.append(first.split()[0])
    expected = g.messages["help"].format(commands=", ".join(names))
    assert outputs[-1] == expected


def test_help_lists_synonyms(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_help("destroy")
    entries = g.commands["destroy"]
    usages = [e.replace("$a", "<>").replace("$b", "<>") for e in entries]
    expected = (
        g.messages["help_usage"].format(command="destroy")
        + "\n"
        + "\n".join(usages)
    )
    assert outputs[-1] == expected


def test_help_optional_argument(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_help("help")
    expected = (
        g.messages["help_usage"].format(command="help")
        + "\nhelp <>\nh <>"
    )
    assert outputs[-1] == expected
