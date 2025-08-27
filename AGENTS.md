# AGENTS.md

## Zweck
Dieses Dokument beschreibt die Idee des Projektes und wie AI-Agents mit dem Code umgehen sollen.


## Projektidee
Ich möchte ein Textadventure schreiben. Dazu möchte ich eine Engine machen, mit der das ganze Spiel funktioniert. Anschließend möchte ich diese Engine benutzen, um ein kleines Adventure zu erstellen.

Besonderheit soll sein, dass zur Laufzeit über ollama ein LLM verfügbar ist, welches das Spiel unterstützen soll. Mögliche Anwendungsgebiete für das LLM sind:
- Interpretation der Eingabebefehle des Nutzers (weg von starren Befehlen, hin zu natürlicher Sprache)
- Natürliche Gespräche mit NSC in der Spielwelt
- Ausgabe von Beschreibungstexten der dynamischen Spielwelt

Dieses Projekt umfasst also:
- Engine erstellen
- Plot erstellen
- Plot mit der Engine umsetzen

Ich möchte diese drei Dinge parallel hochziehen: Die Engine ermöglicht das Spiel, der Plot fordert Erweiterungen der Engine, so dass er dann mit der Engine umgesetzt werden kann.

Die Story soll aus der Sicht einer Person (dem Spieler) passieren.


## Richtlinien
- Programmiersprache: Python 3.12
- Styleguide: PEP8 + ruff + pyright
- Wenn Tests durchgeführt werden, sollte immer auch ein Report der Codeabdeckung gemacht werden  
- Antworten in Deutsch, Variablen-Namen, Konstanten, etc. in Englisch
- Vermeide Code-Kommentare zugunsten eines gut lesbaren Codes 
- Die Engine selber soll frei von plotabhängigem Code sein; der gesamte Plot muss über die generic/world.yaml beshrieben werden. 
- Anstatt anonymer dicts für strukturierte Rückgabe von Daten, verwende @dataclass classes
  Beispiel: statt `return {'a': 1, 'b': 'bbb'}` mache `return Ab(a=1, b='bbb')` mit entsprechender @dataclass `class Ab`