import yaml
from engine import game, io


def make_game(tmp_path):
    (tmp_path / "generic").mkdir()
    (tmp_path / "en").mkdir()
    generic = {"rooms": {"start": {"exits": []}}, "start": "start"}
    en = {"rooms": {"start": {"names": ["Start"], "description": "Start room."}}}
    with open(tmp_path / "generic" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(generic, fh)
    with open(tmp_path / "en" / "world.yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(en, fh)
    return game.Game(str(tmp_path / "en" / "world.yaml"), "en")


def test_help_lists_commands(tmp_path, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = make_game(tmp_path)
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
