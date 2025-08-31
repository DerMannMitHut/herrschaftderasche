# Herrschaft der Asche

Ein textbasiertes Adventure mit modularer Engine und YAML-beschriebener Welt. Die Engine bleibt plot-frei; alle Inhalte liegen in `data/` und sind in mehreren Sprachen verfügbar (DE/EN).

## Schnellstart
- Voraussetzungen: Python 3.12, Poetry installiert
- Setup:
  - `poetry env use 3.12`
  - `poetry install`
- Starten:
  - Entry-Point: `poetry run herrschaft-der-asche --language de`
  - Alternativ (Modul): `poetry run python -m game.main --language de`
  - Shell-Skript: `./hda --language de` (siehe Datei `hda`)
  - Debug-Traces: Flag `--debug` aktivieren (Ausgaben inkl. `datei.py:zeile -- ...`)

## Projektstruktur
- `engine/`: Plot-agnostische Engine (Kernlogik, I/O, Parser, Integrität)
- `game/`: CLI-Einstieg (`game/main.py`) und Startlogik
- `data/`: Welt und Texte
  - `data/generic/world.yaml`: Regeln, Räume, Items, Aktionen (sprachneutral)
  - `data/<lang>/world.<lang>.yaml`: sprachspezifische Namen/Beschreibungen (Welt)
  - `data/<lang>/messages.<lang>.yaml`: Meldungen/Benutzertexte
  - `data/<lang>/commands.<lang>.yaml`: Befehls-Synonyme
- `tests/`: Pytest-Suite
  - `tests/unit`: Unit-Tests (ohne echte Spieldaten; nutzen Fixtures)
  - `tests/story`: Story-Tests (mit echten Spieldaten)

## Entwicklung
- Makefile-Shortcuts:
  - `make deps` (installiert aus Lockfile)
  - `make unit` (Unit-Tests mit Coverage; nur `tests/unit`)
  - `make story` (Story-Tests)
  - `make lint` / `make lint-fix` (ruff)
  - `make typecheck` (pyright)
  - `make all` (deps → lint-fix → typecheck → unit → story)
- Ohne Makefile:
  - Lint: `poetry run ruff check .`
  - Typen: `poetry run pyright`
  - Tests gesamt: `poetry run pytest -q`
  - Coverage (nur Unit): `pytest --cov --cov-branch -q tests/unit`

## Steuerung (Beispiele)
- DE: `gehe Wald`, `umsehen`, `ansehen Truhe`, `nimm Schlüssel`, `rede mit Marek`, `benutze Schlüssel mit Truhe`, `hilfe`, `beenden`
- EN: `go Forest`, `look`, `examine Chest`, `take Key`, `talk Ashram`, `use Key with Chest`, `help`, `quit`

Hinweis: Der Spielstand wird automatisch gespeichert und beim nächsten Start fortgesetzt. LLM-Integration (z. B. über Ollama) ist über einen Adapter vorgesehen und kann testseitig gemockt werden.

### Hilfe-Ausgabe
- Die Hilfe ohne Argument zeigt drei Spalten (lokalisiert): System, Grundlegend, Interaktion.
- Jeweils mit erster Übersetzungs-Phrase und Argumenthinweisen, z. B. `go <>`, `use <> <>`, `show log [n]`.

Beispiel (DE):

```
System   Grundlegend          Interaktion
beenden  gehe <>              rede mit <>
hilfe    umschau              benutze <> <>
sprache <> untersuche <>      zeige <> <>
zeige protokoll [n] inventar  zerstöre <>
         nimm <>              trage <>
         lege <> ab
```

Beispiel (EN):

```
System  Basics  Interactions
quit    go <>   talk to <>
help    look    use <> <>
lang <> examine <> show <> <>
show log [n] inventory destroy <>
         take <>        wear <>
         drop <>
```

### show_log und Synonyme
- Aufrufbar per IDs und Synonymen, z. B. `show log [n]`, `history [n]`, `log [n]` (EN), bzw. `zeige protokoll [n]`, `verlauf [n]`, `protokoll [n]` (DE).

### Debug-Traces
- Mit `--debug`: präzise Traces mit Datei/Zeile, z. B. `world.py:600 -- item gem state green`.
- Enthalten u. a. Kommandodispatch, Spielinitialisierung und dynamische Änderungen (z. B. `add_exit hut->ruins`).

## Tests & Coverage
- Unit- und Story-Tests sind getrennt (`tests/unit`, `tests/story`).
- Coverage wird ausschließlich mit Unit-Tests gemessen.
