from engine import game


def test_language_switch(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_language("de")
    assert g.language_manager.messages["farewell"] == "Auf Wiedersehen!"
    assert g.language_manager.commands["look"][0] == "umschau"
    assert "ansehen $a" in g.language_manager.commands["examine"]
    assert g.language_manager.commands["talk"][0] == "rede mit $a"
    assert g.command_processor.reverse_cmds["hilfe"][0] == "help"
    assert g.command_processor.reverse_cmds["language"][0] == "language"
    assert g.command_processor.reverse_cmds["sprache"][0] == "language"
    assert io_backend.outputs[-1] == g.language_manager.messages["language_set"].format(language="de")
    assert g.world.items["sword"]["names"][0] == "Schwert"


def test_language_persistence(data_dir, io_backend):
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en", io_backend=io_backend)
    g.command_processor.cmd_language("de")
    g.command_processor.cmd_quit()
    g2 = game.Game(str(data_dir / "en" / "world.en.yaml"), "en", io_backend=io_backend)
    assert g2.language == "de"
    assert g2.language_manager.messages["farewell"] == "Auf Wiedersehen!"
    assert g2.command_processor.reverse_cmds["language"][0] == "language"
    assert g2.world.items["sword"]["names"][0] == "Schwert"


def test_language_command_base_word(data_dir, io_backend):
    g = game.Game(str(data_dir / "de" / "world.de.yaml"), "de", io_backend=io_backend)
    cmd, _ = g.command_processor.reverse_cmds["language"]
    getattr(g.command_processor, f"cmd_{cmd}")("en")
    assert g.language == "en"
    assert io_backend.outputs[-1] == g.language_manager.messages["language_set"].format(language="en")
