# Herrschaft der Asche

Ein einfaches Textadventure-Projekt. Dieses Repository enthält eine kleine Engine und eine Beispielwelt, die aus YAML-Daten geladen wird.

## Installation und Ausführung

Dieses Projekt verwaltet Abhängigkeiten mit [Poetry](https://python-poetry.org/).
Nach dem Klonen des Repositories werden die Abhängigkeiten mit

```bash
poetry install
```

installiert. Das Spiel wird anschließend über

```bash
poetry run python game/main.py
```

gestartet.

Je nach Spracheingabe können Befehle wie `gehe Wald` (Deutsch) oder `go forest` (Englisch) eingegeben werden. Mit `beenden` (Deutsch) bzw. `quit` oder `exit` (Englisch) wird das Spiel beendet.

In der Hütte liegt beispielsweise ein Schlüssel. Gegenstände können mit `nimm`/`take` aufgenommen, mit `lege`/`drop` wieder abgelegt und mit `inventar`/`inventory` angezeigt werden.
Mit `umsehen`/`look` lässt sich die Beschreibung des aktuellen Raums erneut ausgeben. Mit `umsehen Schlüssel`/`look key` erhält man die Beschreibung eines Gegenstands. Mit `hilfe`/`help` werden alle verfügbaren Befehle angezeigt. Mit `sprache <id>`/`language <id>` kann die Sprache gewechselt werden.

Die Welt- und Übersetzungsdaten liegen in den Unterverzeichnissen `data/de/` bzw. `data/en/`.
