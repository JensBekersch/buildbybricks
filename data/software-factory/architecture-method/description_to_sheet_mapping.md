# Mapping von Beschreibung zu Architecture Sheet

Dieses Dokument beschreibt, wie eine freie Beschreibung eines Django-Softwareartefakts
in die Felder des Architecture Sheets uebertragen wird.

## Grundregel

Die Beschreibung ist kein fertiger Architekturentwurf. Der Generator soll
fachliche Hinweise extrahieren, plausible Architekturannahmen markieren und
offene Punkte sichtbar machen.

## Mapping-Regeln

- Substantive und Prozessbegriffe wie Kunden, Angebote, Rechnungen, Termine,
  Freigaben oder Dokumente werden Kandidaten fuer `building_blocks`, `data_view`
  und `runtime_scenarios`.
- Ziele wie "schneller bearbeiten", "nachvollziehbar freigeben" oder
  "Fehler vermeiden" werden Kandidaten fuer `business_goal` und
  `quality_goals`.
- Begriffe wie Rollen, Rechte, Login, Mandanten, Freigabe oder Audit werden in
  `security_view`, `architecture_drivers`, `risks` und `open_questions`
  gespiegelt.
- Begriffe wie API, Schnittstelle, Import, Export, Webhook oder Integration
  werden in `context.interfaces` und `context.external_systems` gespiegelt.
- Begriffe wie PDF, Excel, CSV, Dokument, Archiv oder Vorlage werden in
  `building_blocks`, `runtime_scenarios`, `risks` und `open_questions`
  gespiegelt.
- Unklare Anforderungen werden nicht erfunden. Sie werden als `assumptions` oder
  `open_questions` markiert.

## Artifact Name

Der `artifact_name` soll kurz, fachlich und stabil sein. Gute Namen:

- Angebotsverwaltung
- Kundenportal
- Freigabecenter
- Vertragsverwaltung
- Reporting Dashboard

Schlechte Namen:

- Django App
- Neues System
- Kunden Angebote Freigaben PDF API

## Readiness

Ein Sheet darf `ready-for-review` sein, wenn es strukturell vollstaendig ist und
Folgeagenten daraus arbeiten koennen. Es darf nicht `approved` sein, solange kein
Mensch das Sheet geprueft und offene Fragen akzeptiert oder beantwortet hat.
