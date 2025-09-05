# Herrschaft der Asche

Ein textbasiertes Adventure mit modularer Engine und YAML-beschriebener Welt. Die Engine bleibt plot-frei; alle Inhalte liegen in `data/` und sind in mehreren Sprachen verfügbar (DE/EN).

## Schnellstart
- Voraussetzungen: Python 3.12, Poetry installiert
- Setup:
  - `poetry env use 3.12`
  - `poetry install`
- Starten:
  - Entry-Point: `poetry run herrschaft-der-asche --language de`
  - Mit LLM (Ollama): `poetry run herrschaft-der-asche --language de --llm`
  - LLM-Parameter:
    - `--llm-model <name>`: überschreibt `OLLAMA_MODEL` (z. B. `mistral`, `llama3`)
    - `--llm-base-url <url>`: überschreibt `OLLAMA_BASE_URL` (z. B. `http://localhost:11434`)
    - `--llm-timeout <sek>`: Timeout in Sekunden (überschreibt Default 30)
  - Alternativ (Modul): `poetry run python -m game.main --language de`
  - Shell-Skript: `./hda --language de` (siehe Datei `hda`)
  - Shell-Skript (mit LLM): `./hda --language de --llm` (optionale Flags wie oben)
  - Debug-Traces: Flag `--debug` aktivieren (Ausgaben inkl. `datei.py:zeile -- ...`)

## Projektstruktur
- `engine/`: Plot-agnostische Engine (Kernlogik, I/O, Parser, Integrität)
  - `engine/llm.py`: LLM-Backends (`NoOpLLM`, `OllamaLLM`)
  - `engine/interfaces.py`: Protokolle (`IOBackend`, `LLMBackend`)
- `game/`: CLI-Einstieg (`game/main.py`) und Startlogik
- `data/`: Welt und Texte
  - `data/generic/world.yaml`: Regeln, Räume, Items, Aktionen (sprachneutral)
  - `data/<lang>/world.<lang>.yaml`: sprachspezifische Namen/Beschreibungen (Welt)
  - `data/<lang>/messages.<lang>.yaml`: Meldungen/Benutzertexte
  - `data/<lang>/commands.<lang>.yaml`: Befehls-Synonyme
  - `data/<lang>/llm.<lang>.yaml`: LLM-Sprachhinweise (Artikel/Präpositionen etc.)
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

Hinweis: Der Spielstand wird automatisch gespeichert und beim nächsten Start fortgesetzt. Die LLM-Integration (z. B. über Ollama) ist optional über einen Adapter aktivierbar (CLI-Flag `--llm`) und kann testseitig gemockt werden.

## LLM-Nutzung (optional)
- Ziel: Freitext-Eingaben auf Spielbefehle mappen (z. B. „nimm den roten Schlüssel vom Tisch“ → „take key“).
- Standard: Ohne Konfiguration läuft ein No-Op-Backend; Eingaben werden unverändert ausgewertet.

### Ollama aktivieren
- Voraussetzungen: Lokaler Ollama-Server (https://ollama.ai), Modell per `ollama pull <modell>` geladen.
- Konfiguration über Umgebungsvariablen:
  - `OLLAMA_BASE_URL` (Default: `http://localhost:11434`)
  - `OLLAMA_MODEL` (Default: `mistral`)

Schnell starten via CLI-Flag:

```
poetry run herrschaft-der-asche --language de --llm
```

Mit Parametern (überschreiben Env-Vars):

```
poetry run herrschaft-der-asche --language en --llm \
  --llm-model mistral --llm-base-url http://localhost:11434 --llm-timeout 20
```

Alternativ kann das LLM-Backend programmgesteuert übergeben werden. Beispiel:

```
poetry run python - << 'PY'
from engine.game import run
from engine.llm import OllamaLLM
from pathlib import Path

lang = "de"
data_path = Path("data")/lang/f"world.{lang}.yaml"
run(str(data_path), language=lang, llm_backend=OllamaLLM(), debug=False)
PY
```

Oder kurz für EN:

```
poetry run python -c "from engine.game import run; from engine.llm import OllamaLLM; run('data/en/world.en.yaml', language='en', llm_backend=OllamaLLM())"
```

Hinweise:
- Die Prompt-Vorlagen liegen in `data/<lang>/llm.<lang>.yaml`. Zur Laufzeit füllt das Backend diese mit Welt, Sprache und Log.
- Netzwerkfehler oder ungültige Antworten führen zu einem sicheren Fallback: Der Originalbefehl wird genutzt.

### Eigenes LLM-Backend
- Implementiere das Protokoll `engine.interfaces.LLMBackend` mit:
  - `interpret(command: str) -> str`
  - `set_context(world, language, log) -> None`
- Binde es beim Start wie oben gezeigt über `llm_backend=<DeinBackend>()` ein.

### LLM-Sprachkonfiguration
- Pro Sprache konfigurierbar unter `data/<lang>/llm.<lang>.yaml`. Die Datei enthält Abschnitte für `prompt`, `context` und `guidance` sowie Listen für Artikel und Präpositionen.
- Beispiel (`data/en/llm.en.yaml`):

```yaml
prompt: |-
  You map player input to game commands. A command consists of a <verb> and optional 1 or 2 objects. <confidence> is a value between 0 and 2: 0=unsure, 1=quite sure, 2=totally sure.
  Language: {lang}.
  Allowed verbs: {allowed_verbs}
  Known nouns: {known_nouns}
  Guidance:
  ```
  {guidance}
  ```
  Context:
  ```
  {context}
  ```
  Respond with JSON {{"confidence": <confidence>, "verb": "<verb>", "object": "<noun1>", "additional": "<noun2>"}} and nothing else.
context: |-
  Description of the current location:
  {room} {visible}
  Player inventory: {inventory}
  Item states: {item_states}
  NPC states: {npc_states}
guidance: |-
  Ignore articles/determiners when matching nouns ({articles}).
  Ignore contractions when matching nouns ({contractions}).
  Map these prepositions to the second object (additional): {prepositions}.
  Choose object strings from 'Known nouns'.
  Treat quoted phrases as one object.
ignore_articles:
  - the
  - a
  - an
ignore_contractions: []
second_object_preps:
  - with
```

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
