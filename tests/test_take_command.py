from engine import game, io


def test_take_uses_canonical_name(data_dir, monkeypatch):
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    g = game.Game(str(data_dir / "en" / "world.yaml"), "en")
    assert g.world.move("Room 3")
    g.cmd_take("sword")
    assert outputs[-1] == g.messages["taken"].format(item="Sword")
