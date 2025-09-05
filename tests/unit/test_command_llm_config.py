from engine import commands, language, persistence, world


def test_command_processor_uses_llm_config(data_dir, io_backend, tmp_path):
    generic = data_dir / "generic" / "world.yaml"
    en = data_dir / "en" / "world.en.yaml"
    w = world.World.from_files(generic, en)
    lm = language.LanguageManager(data_dir, "en", io_backend)
    lm.llm_config = {"ignore_articles": ["zzz"], "ignore_contractions": ["yyy"]}
    saver = persistence.SaveManager(tmp_path)
    cp = commands.CommandProcessor(
        w,
        lm,
        saver,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda _w: None,
        io_backend,
    )
    assert cp._ignore_articles == {"zzz"}
    assert cp._ignore_contractions == {"yyy"}
