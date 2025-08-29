import builtins

from engine import io, parser


def test_parse_normalizes():
    assert parser.parse("  LOOK  ") == "look"


def test_get_input(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda prompt="": "value")
    assert io.get_input("?") == "value"


def test_output(capsys):
    io.output("text")
    assert capsys.readouterr().out.strip() == "text"

