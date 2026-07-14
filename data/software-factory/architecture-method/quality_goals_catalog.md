# Katalog typischer Qualitaetsziele

Dieses Dokument liefert wiederverwendbare Qualitaetsziele fuer Django-
Architecture-Sheets. Jedes Qualitaetsziel muss als pruefbares Szenario
formuliert werden.

## Typische Qualitaetsziele

### Nachvollziehbarkeit

Szenario: Eine fachliche Entscheidung, etwa eine Freigabe oder Ablehnung, kann
spaeter mit Nutzer, Zeitpunkt, Objektzustand und Begruendung rekonstruiert
werden.

### Aenderbarkeit

Szenario: Eine fachliche Regel kann in einem klar abgegrenzten Django-Modul
angepasst werden, ohne unrelated Apps zu veraendern.

### Testbarkeit

Szenario: Fachlogik, Berechtigungen und kritische Workflows koennen automatisiert
in Unit-, Service- und Integrationstests geprueft werden.

### Bedienbarkeit

Szenario: Fachanwender koennen die Kernaufgabe ohne Entwicklerunterstuetzung
durchfuehren und erkennen Validierungsfehler direkt.

### Datenintegritaet

Szenario: Ungueltige Statusuebergaenge, fehlende Pflichtdaten und widerspruechliche
Beziehungen werden durch Models, Services oder Datenbankconstraints verhindert.

### Betriebssicherheit

Szenario: Die Anwendung kann lokal, in Test und in Produktion mit klarer
Konfiguration gestartet, ueberwacht und wiederhergestellt werden.

## Priorisierung

`high` bedeutet: Das Ziel beeinflusst Architekturentscheidungen und Workorders
im ersten Release.

`medium` bedeutet: Das Ziel muss sichtbar bleiben, kann aber in spaeteren
Workorders vertieft werden.

`low` bedeutet: Das Ziel ist bekannt, aber nicht entscheidend fuer den ersten
Architekturschnitt.
