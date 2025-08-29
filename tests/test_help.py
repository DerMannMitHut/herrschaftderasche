from engine import game


def test_help_lists_commands(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_help("")
    names = []
    for key in g.command_processor.command_keys:
        val = g.language_manager.commands.get(key, [])
        entries = val if isinstance(val, list) else [val]
        first = entries[0]
        names.append(first.split()[0])
    expected = g.language_manager.messages["help"].format(commands=", ".join(names))
    assert io_backend.outputs[-1] == expected


def test_help_lists_synonyms(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_help("destroy")
    entries = g.language_manager.commands["destroy"]
    usages = [e.replace("$a", "<>").replace("$b", "<>") for e in entries]
    expected = (
        g.language_manager.messages["help_usage"].format(command="destroy")
        + "\n"
        + "\n".join(usages)
    )
    assert io_backend.outputs[-1] == expected


def test_help_optional_argument(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_help("help")
    expected = (
        g.language_manager.messages["help_usage"].format(command="help")
        + "\nhelp <>\nh <>"
    )
    assert io_backend.outputs[-1] == expected
