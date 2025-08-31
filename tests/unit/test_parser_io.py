import builtins

from engine import parser
from engine.io import ConsoleIO


def test_parse_normalizes():
    assert parser.parse("  LOOK  ") == "look"


def test_get_input(monkeypatch):
    console = ConsoleIO()
    monkeypatch.setattr(builtins, "input", lambda prompt="": "value")
    assert console.get_input("?") == "value"


def test_output(capsys):
    console = ConsoleIO()
    console.output("text")
    assert capsys.readouterr().out.strip() == "text"

