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


def test_help_lists_synonyms(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    g.cmd_help("destroy")
    entries = g.commands["destroy"]
    arg_str = " ".join("<>" for _ in range(g.command_info["destroy"].get("arguments", 0)))
    usages = []
    for entry in entries:
        if isinstance(entry, list):
            name, suffix = entry
            usages.append(f"{name} {arg_str} {suffix}".strip())
        else:
            usages.append(f"{entry} {arg_str}".strip())
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
        + "\nhelp <command>\nh <command>"
    )
    assert outputs[-1] == expected
