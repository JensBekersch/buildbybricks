# Architecture Sheet nach arc42 fuer Django-Softwareartefakte

Dieses Methodenwissen beschreibt den ersten produktiven Workflow der Software Factory:
Aus einer freien Beschreibung eines Softwareartefakts wird ein strukturiertes
Architecture Sheet erzeugt. Das Sheet ist kein vollstaendiges arc42-Dokument,
sondern ein kompakter, pruefbarer Zwischenstand fuer nachgelagerte Agenten.

## Ziel des Architecture Sheets

Das Architecture Sheet soll ein gemeinsames Verstaendnis ueber Ziel, Kontext,
Qualitaetsziele, technische Leitplanken und offene Fragen schaffen. Es muss so
strukturiert sein, dass spaeter Workorders, Django-Module, Tests und GitHub-
Aenderungen daraus abgeleitet werden koennen.

## arc42-orientierte Abschnitte

Ein Architecture Sheet enthaelt mindestens:

- artifact_name: Name des geplanten Softwareartefakts.
- artifact_type: Fuer den Start vor allem `django-application`, `django-service`
  oder `django-app-module`.
- business_goal: Fachliches Ziel und Nutzen.
- stakeholders: Nutzer, Betreiber, Fachbereiche, Entwickler und weitere
  Anspruchsgruppen.
- quality_goals: Die wichtigsten Qualitaetsziele mit konkretem Szenario und
  Prioritaet.
- constraints: Technische, organisatorische, regulatorische und betriebliche
  Randbedingungen.
- context: Nutzer, externe Systeme und Schnittstellen.
- solution_strategy: Architekturidee in wenigen Saetzen.
- building_blocks: Grobe Bausteine und ihre Django-Zuordnung.
- runtime_scenarios: Zentrale Ablauf- oder Nutzungsszenarien.
- deployment_view: Erste Sicht auf Betrieb, Container, Umgebungen und
  Infrastruktur.
- data_view: Wichtige Datenobjekte, Datenfluesse und Persistenz.
- security_view: Authentifizierung, Autorisierung, Datenzugriff und Audit.
- test_strategy: Welche Tests spaeter erzeugt werden muessen.
- risks: Risiken mit moeglicher Mitigation.
- open_questions: Punkte, die vor Umsetzung geklaert werden muessen.
- assumptions: Annahmen, die aus der Beschreibung abgeleitet wurden.

## Django-spezifische Heuristiken

Wenn die Beschreibung eine Django-Applikation nahelegt, sollen Bausteine in
Django-Begriffen formuliert werden:

- Django Project fuer globale Settings, URL-Routing und Deployment-Konfiguration.
- Django Apps fuer fachliche Module wie Kunden, Angebote, Rechnungen, Rollen
  oder Freigaben.
- Models fuer Kernobjekte und Beziehungen.
- Views oder API Views fuer Interaktionen.
- Forms, Serializers oder Templates je nach UI/API-Stil.
- Admin-Konfiguration fuer interne Pflegeoberflaechen.
- Celery, Django-Q oder Management Commands fuer Hintergrundaufgaben.
- pytest oder Django TestCase fuer Unit-, Integration- und API-Tests.

## Antwortregeln fuer den Generator

Der Generator soll nicht frei plaudern, sondern ein strukturiertes Sheet liefern.
Wenn Informationen fehlen, sollen keine Details erfunden werden. Stattdessen:

- Eine plausible Annahme in `assumptions` aufnehmen.
- Eine klaerbare Frage in `open_questions` aufnehmen.
- Risiken sichtbar machen, wenn Anforderungen unklar oder kritisch sind.
- Django-spezifische Vorschlaege nur nennen, wenn sie aus der Beschreibung
  plausibel ableitbar sind.

## Minimaler Output-Contract

Das Architecture Sheet soll als JSON-kompatible Struktur erzeugt werden. Jeder
Abschnitt muss vorhanden sein. Leere oder unklare Bereiche werden mit sinnvollen
offenen Fragen und Annahmen markiert, nicht still ausgelassen.

## Beispiel fuer ein kompaktes Sheet

Beschreibung: Eine Django-App verwaltet Kunden, Angebote und Freigabeprozesse.

Erwartete Kernelemente:

- artifact_name: Angebotsverwaltung
- artifact_type: django-application
- business_goal: Angebote strukturiert erstellen, pruefen und freigeben.
- stakeholders: Vertrieb, Management, Backoffice, Administratoren.
- quality_goals: Nachvollziehbarkeit, Bedienbarkeit, Datenintegritaet.
- building_blocks: customers app, offers app, approvals app, accounts app.
- runtime_scenarios: Angebot erstellen, Angebot freigeben, PDF exportieren.
- risks: Unklare Rollenmatrix, rechtliche Anforderungen an Angebotsdokumente.
- open_questions: PDF-Layout, Freigabestufen, externe CRM-Integration.
