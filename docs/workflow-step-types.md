# Workflow Step Types

Die Workflow Factory unterscheidet Step-Typen bewusst von konkreten Agenten. Dadurch kann ein Workflow spaeter aus deterministischen Funktionen, LLM-Agenten, Validierungen und Kontrollschritten zusammengesetzt werden.

## TASK

Ein `TASK` ist ein deterministisch implementierter Schritt ohne eigenen LLM-Aufruf. Beispiele:

- JSON/YAML laden
- Schema laden
- Methodenwissen aus Dateien sammeln
- Git Repository auslesen
- Dateien erzeugen
- Artefakte in Postgres speichern

Tasks sollen ueber eine Registry aufgeloest werden. Der Workflow beschreibt dann nur noch `task.name` und `task.parameters`, nicht die konkrete Python-Implementierung.

## AGENT

Ein `AGENT` nutzt eine Agent-Konfiguration aus YAML. Der Agent erhaelt:

- definierte Inputs aus vorherigen Artefakten
- System- und User-Prompt
- optionales Methodenswissen
- ein Output-Schema
- Validatoren
- Modell- und Timeout-Konfiguration

Ein Agent soll nicht implizit beliebige Seiteneffekte ausfuehren. Wenn ein Agent ein Git Repository lesen soll, bekommt er das Ergebnis eines vorherigen `TASK` als Input oder spaeter ein explizit erlaubtes Tool.

## VALIDATION

Ein `VALIDATION` Step prueft Artefakte gegen harte Regeln. Beispiele:

- JSON Schema Validation
- verbotene Begriffe
- Evidence-Pflicht
- Zahlen- und Scope-Erhaltung
- Cross-Field-Konsistenz

Validierungen koennen den Workflow stoppen oder Korrekturschritte ausloesen.

## CONTROL

Ein `CONTROL` Step steuert den Ablauf. Beispiele:

- Branching
- Retry/Korrekturlauf
- Schleifen mit maximaler Iterationszahl
- Auswahl des naechsten Agenten anhand eines Review-Ergebnisses

CONTROL Steps erzeugen normalerweise keine fachlichen Artefakte, sondern Ablaufentscheidungen.

## HUMAN_REVIEW

`HUMAN_REVIEW` ist fuer spaetere Ausbaustufen vorgesehen. Der Workflow pausiert, bis eine Person ein Artefakt freigibt, ablehnt oder kommentiert.

## Immutability-Regel

Veroeffentlichte Workflow-Versionen sind unveraenderlich. Aenderungen passieren in Drafts oder in neuen Versionen. Dadurch bleiben alte Runs reproduzierbar und Debug-Ergebnisse nachvollziehbar.
