# Herrschaft der Asche

Ein textbasiertes Adventure mit modularer Engine und einer YAML-beschriebenen Welt. Die Engine bleibt plot-frei; alle Inhalte liegen in `data/` und sind in mehreren Sprachen verfügbar (DE/EN).

## Schnellstart
- Voraussetzungen: Python 3.12, Poetry installiert
- Setup:
  - `poetry env use 3.12`
  - `poetry install`
- Starten:
  - Entry-Point: `poetry run herrschaft-der-asche --language de`
  - Alternativ (Modul): `poetry run python -m game.main --language de`
  - Shell-Skript: `./hda --language de` (siehe Datei `hda`)

## Projektstruktur
- `engine/`: Plot-agnostische Engine (Kernlogik, I/O, Parser, Integrität)
- `game/`: CLI-Einstieg (`game/main.py`) und Startlogik
- `data/`: Welt und Texte
  - `data/generic/world.yaml`: Regeln, Räume, Items, Aktionen (sprachneutral)
  - `data/de/*.yaml`, `data/en/*.yaml`: Namen, Beschreibungen, Meldungen
- `tests/`: Pytest-Suite (End-to-End und Unit-Tests)

## Entwicklung
- Lint: `poetry run ruff check .` | Format: `poetry run ruff format .`
- Typen: `poetry run pyright`
- Tests: `poetry run pytest -q` | mit Coverage: `poetry run pytest --cov --cov-branch -q`

## Steuerung (Beispiele)
- DE: `gehe Wald`, `umsehen`, `ansehen Truhe`, `nimm Schlüssel`, `rede mit Marek`, `benutze Schlüssel mit Truhe`, `hilfe`, `beenden`
- EN: `go Forest`, `look`, `examine Chest`, `take Key`, `talk Ashram`, `use Key with Chest`, `help`, `quit`

Hinweis: Der Spielstand wird automatisch gespeichert und beim nächsten Start fortgesetzt. LLM-Integration (z. B. über Ollama) ist über einen Adapter vorgesehen und kann testseitig gemockt werden.
