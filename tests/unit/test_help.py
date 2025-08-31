from engine import game


def test_help_lists_commands(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_help("")
    out = io_backend.outputs[-1]
    # Expect column headings and some representative commands
    assert "System" in out
    assert "Basics" in out
    assert "Interactions" in out
    # Representative commands present somewhere in the table
    for token in ("quit", "go", "talk"):
        assert token in out


def test_help_lists_synonyms(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
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
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_help("help")
    expected = (
        g.language_manager.messages["help_usage"].format(command="help")
        + "\nhelp <>\nh <>"
    )
    assert io_backend.outputs[-1] == expected
