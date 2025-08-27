# AGENTS.md

## Zweck
Dieses Dokument beschreibt, wie AI-Agents Testcode erstellen sollen.

## Richtlinien
- Es gilt die übergeordnete AGENTS.md
- pytest ist das Test-Framework
- Alle Tests sollen grundsätzlich nur auf Testdaten laufen. Die Daten werden in dem fixture "data_dir" in conftest.py aufgesetzt. Wenn nötig, sollen diese ergänzt oder manipuliert werden.
- Es muss sichergestellt werden, dass alle Unit-Tests laufen.
- 
