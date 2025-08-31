# AGENTS.md

## Zweck
Dieses Dokument beschreibt, wie AI-Agents Testcode erstellen sollen.

## Richtlinien
- Es gilt die übergeordnete AGENTS.md
- pytest ist das Test-Framework
- Alle Tests sollen grundsätzlich nur auf Testdaten laufen. Die Daten werden in dem Fixture "data_dir" in conftest.py aufgesetzt. Wenn nötig, sollen diese ergänzt oder manipuliert werden.
- Es muss sichergestellt werden, dass alle Unit-Tests laufen.

## Verzeichnisstruktur der Tests
- tests/unit: Unit-Tests ohne echte Spieldaten
  - Testen ausschließlich Engine-Logik mit Testdaten/Fixtures (z. B. `data_dir`).
  - Dürfen keine Dateien aus `data/<lang>/*` oder `data/generic/*` lesen oder kopieren.
- tests/story: Story-Tests mit echten Spieldaten
  - Greifen auf die realen YAMLs unter `data/*/world.yaml` zu (z. B. Kopieren in ein tmp-Verzeichnis).
  - Validieren Story-Verhalten, Enden, Interaktionen auf Basis der gelieferten Welt.
- Gemischte Tests sind nicht erlaubt
  - Eine Testdatei darf entweder ausschließlich Testdaten/Fixtures verwenden (Unit) oder ausschließlich mit echten Spieldaten arbeiten (Story).
  - Wenn beides benötigt wird, sind getrennte Tests zu schreiben (ein Unit-Test und ein Story-Test) – keine Mischung innerhalb einer Testdatei.

## Platzierung neuer Tests
- Bevorzuge `tests/unit` für reine Engine-Logik. Nutze das Fixture `data_dir` statt echter Dateien.
- Lege nur dann unter `tests/story` an, wenn der Test explizit die echten Spieldateien benötigt.
- Gemischte Tests (gleichzeitig Testdaten und echte Spieldaten) sind unzulässig; splitte die Fälle in separate Tests.
- Vermeide Netzwerkanfragen; LLM/Adapter sind zu mocken und als Dataclasses zu modellieren.

## Testabdeckung (Coverage)
- Coverage wird ausschließlich über die Unit-Tests gemessen.
- Story-Tests werden nicht für die Abdeckungsmetriken herangezogen.
- Empfohlener Befehl für Coverage: `pytest --cov --cov-branch -q tests/unit`.
