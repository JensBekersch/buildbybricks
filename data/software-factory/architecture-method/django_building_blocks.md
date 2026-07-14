# Django Building Blocks fuer Architecture Sheets

Dieses Dokument beschreibt typische Bausteine fuer Django-Applikationen, die im
Architecture Sheet verwendet werden koennen.

## Standard-Bausteine

- Django Project Shell: Settings, URL-Routing, ASGI/WSGI, Konfiguration und
  Deployment-Einstieg.
- Accounts and Permissions: Benutzer, Rollen, Gruppen, Berechtigungen und
  objektbezogene Zugriffskontrolle.
- Core Domain Apps: fachliche Django Apps entlang stabiler Verantwortlichkeiten.
- Admin Surface: Django Admin fuer interne Pflege, Support und Diagnose.
- API Layer: Django REST Framework oder vergleichbare API-Schicht, wenn externe
  Systeme oder spaetere Automatisierung angebunden werden.
- Background Jobs: Celery, Django-Q, Huey oder Management Commands fuer
  asynchrone Aufgaben, Importe, Exporte und regelmaessige Verarbeitung.
- Document Export: PDF, CSV, Excel oder andere erzeugte Dokumente.
- Audit Trail: Nachvollziehbarkeit wichtiger fachlicher Entscheidungen.

## Schnittregeln fuer Django Apps

Eine Django App sollte eine klare fachliche Verantwortung haben. Gute Schnitte:

- `customers` fuer Kundenstammdaten
- `offers` fuer Angebote und Angebotspositionen
- `approvals` fuer Freigabeprozesse
- `documents` fuer Exporte und Vorlagen
- `accounts` fuer Rollen und Nutzerverwaltung

Schlechte Schnitte:

- `misc`
- `core` fuer alle fachlichen Dinge
- `utils` als Ablage fuer Geschaeftslogik
- Views mit versteckter Fachlogik ohne Services oder Tests

## Test-Mapping

- Models brauchen Tests fuer Validierung, Beziehungen und wichtige Constraints.
- Services brauchen Tests fuer Fachregeln und Statusuebergaenge.
- Views/API Views brauchen Tests fuer Authentifizierung, Autorisierung und
  Response-Verhalten.
- Workflows brauchen Integrationstests.
- Exporte brauchen Snapshot- oder Strukturtests fuer erzeugte Dateien.
