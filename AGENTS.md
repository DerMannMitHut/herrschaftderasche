# Repository Guidelines

## Projektstruktur & Module
- `engine/`: Plot-agnostische Engine (Kernlogik, keine Story-Abhängigkeiten)
- `data/`: Welt-/Plotdaten. Sprachspezifisch unter `data/<lang>/world.yaml`; Defaults unter `data/generic/*`
- `game/`: CLI-Einstieg (`game/main.py`), startet die Engine mit einer `world.yaml`
- `tests/`: Pytest-Suite, spiegelt Modulstruktur wider

## Build, Test & lokale Entwicklung
- Python-Version: 3.11+ (empfohlen 3.12). Empfohlenes Setup mit Poetry:
  - `poetry env use 3.12`
  - `poetry install`
  - Interaktive Shell: `poetry shell` (alternativ Befehle mit `poetry run ...`)
- Lint: `poetry run ruff check .` und Format: `poetry run ruff format .`
- Typen: `poetry run pyright`
- Tests schnell: `poetry run pytest -q`
- Tests mit Coverage: `poetry run pytest --cov --cov-branch -q`
- Abhängigkeiten: `poetry add <pkg>`; Dev-Tools: `poetry add --group dev ruff pyright pytest pytest-cov`
 - Ausführen:
   - Entry-Point: `poetry run herrschaft-der-asche --language de`
   - Modulstart: `poetry run python -m game.main --language de`
   - Notfall (Dateiaufruf): `poetry run PYTHONPATH=. python game/main.py --language de`

## Coding Style & Benennung
- Stil: PEP8, geprüft via ruff; Typen via pyright
- Lesbarkeit vor Kommentaren; vermeide überflüssige Code-Kommentare
- Bezeichner (Variablen, Funktionen, Klassen, Konstanten) in Englisch
- Muster: `snake_case` (Funktionen/Variablen/Module), `PascalCase` (Klassen), `UPPER_SNAKE_CASE` (Konstanten)
- Strukturiere Rückgaben mit `@dataclass` statt anonymer `dict`

## Test-Richtlinien
- Framework: pytest; Dateinamen: `tests/test_*.py`
- Schreibe gezielte Unit-Tests für neue/änderte Logik; mocke I/O und LLM-Aufrufe
- Bevorzugt hohe Abdeckung; nutze `--cov --cov-branch` für Regressionsschutz
- Beispiel: Engine-APIs gegen Fixtures testen; Plot-Validierung gegen `data/generic/world.yaml`

## Commits & Pull Requests
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`); Imperativ, kurz, präzise
- PRs: klare Beschreibung, Motivation, Änderungsliste, ggf. Screenshots/Logs
- Checkliste vor Merge: Lint ok, Typprüfung ok, Tests (inkl. Coverage) grün, relevante Doku angepasst

## Agent-/LLM- und Architektur-Hinweise
- Die Engine bleibt strikt plot-frei; Story/Regeln liegen in `data/*/world.yaml`
- LLM (ollama) nur über eine interne Schnittstelle verwenden (Adapter/Port), damit Tests deterministisch bleiben
- Keine Netzwerkanfragen in Unit-Tests; Adapter mocken und Eingaben/Ausgaben als Dataclasses modellieren

## Sicherheit & Konfiguration
- Keine Secrets ins Repo; Konfiguration über Umgebungsvariablen (z. B. `OLLAMA_BASE_URL`, `OLLAMA_MODEL`)
- Optional `.env.local` nutzen; sichere Defaults vorsehen
