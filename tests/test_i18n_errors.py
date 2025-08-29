import pytest

from engine import i18n, io


def _prepare_i18n(monkeypatch, data_dir):
    engine_dir = data_dir / "engine"
    engine_dir.mkdir()
    monkeypatch.setattr(i18n, "__file__", str(engine_dir / "i18n.py"))


def test_load_messages_missing_file(data_dir, monkeypatch):
    _prepare_i18n(monkeypatch, data_dir)
    (data_dir / "data" / "en").mkdir(parents=True)
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    with pytest.raises(SystemExit):
        i18n.load_messages("en")
    assert any("Missing file" in o for o in outputs)


def test_load_messages_corrupted(data_dir, monkeypatch):
    _prepare_i18n(monkeypatch, data_dir)
    path = data_dir / "data" / "en"
    path.mkdir(parents=True)
    with open(path / "messages.yaml", "w", encoding="utf-8") as fh:
        fh.write("- : - invalid yaml")
    outputs: list[str] = []
    monkeypatch.setattr(io, "output", lambda text: outputs.append(text))
    with pytest.raises(SystemExit):
        i18n.load_messages("en")
    assert any("Invalid YAML" in o for o in outputs)

