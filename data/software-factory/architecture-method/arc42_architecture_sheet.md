# Architecture Sheet nach arc42 fuer Django-Softwareartefakte

Dieses Methodenwissen beschreibt den ersten produktiven Workflow der Software Factory:
Aus einer freien Beschreibung eines Softwareartefakts wird ein strukturiertes
Architecture Sheet erzeugt. Das Sheet ist kein vollstaendiges arc42-Dokument,
sondern ein kompakter, pruefbarer Zwischenstand fuer nachgelagerte Agenten.

Ergaenzende Methodenquellen in dieser Collection:

- `description_to_sheet_mapping.md`: Mapping von Nutzerbeschreibung zu Sheet-Feldern.
- `django_building_blocks.md`: typische Django-Bausteine, App-Schnitte und Test-Mapping.
- `quality_goals_catalog.md`: wiederverwendbare Qualitaetsziele mit Szenarien.
- `risks_and_review.md`: typische Risiken, offene Fragen und Review-Regeln.

## Ziel des Architecture Sheets

Das Architecture Sheet soll ein gemeinsames Verstaendnis ueber Ziel, Kontext,
Qualitaetsziele, technische Leitplanken und offene Fragen schaffen. Es muss so
strukturiert sein, dass spaeter Workorders, Django-Module, Tests und GitHub-
Aenderungen daraus abgeleitet werden koennen.

## arc42-orientierte Abschnitte

Ein Architecture Sheet enthaelt mindestens:

- schema_version: Version des Sheet-Contracts, aktuell `1.0.0`.
- artifact_name: Name des geplanten Softwareartefakts.
- artifact_type: Fuer den Start vor allem `django-application`, `django-service`
  oder `django-app-module`.
- input_summary: Verdichtete Nutzerbeschreibung als Arbeitsgrundlage.
- business_goal: Fachliches Ziel und Nutzen.
- stakeholders: Nutzer, Betreiber, Fachbereiche, Entwickler und weitere
  Anspruchsgruppen.
- architecture_drivers: Zentrale Treiber fuer Architekturentscheidungen.
- quality_goals: Die wichtigsten Qualitaetsziele mit konkretem Szenario und
  Prioritaet.
- constraints: Technische, organisatorische, regulatorische und betriebliche
  Randbedingungen.
- context: Nutzer, externe Systeme und Schnittstellen.
- solution_strategy: Architekturidee in wenigen Saetzen.
- architecture_decisions: Explizite Entscheidungen mit Begruendung und Status.
- building_blocks: Grobe Bausteine und ihre Django-Zuordnung.
- runtime_scenarios: Zentrale Ablauf- oder Nutzungsszenarien.
- deployment_view: Erste Sicht auf Betrieb, Container, Umgebungen und
  Infrastruktur.
- data_view: Wichtige Datenobjekte, Datenfluesse und Persistenz.
- security_view: Authentifizierung, Autorisierung, Datenzugriff und Audit.
- test_strategy: Welche Tests spaeter erzeugt werden muessen.
- acceptance_criteria: Pruefbare Kriterien fuer die Brauchbarkeit des Sheets.
- risks: Risiken mit moeglicher Mitigation.
- open_questions: Punkte, die vor Umsetzung geklaert werden muessen.
- assumptions: Annahmen, die aus der Beschreibung abgeleitet wurden.
- readiness: Status und kurze Einschaetzung fuer Review/Freigabe.

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

Ein produktiv brauchbares Sheet muss:

- alle Pflichtfelder des Schemas `1.0.0` enthalten,
- mindestens eine Architekturentscheidung enthalten,
- mindestens ein Qualitaetsziel mit Szenario enthalten,
- mindestens ein Risiko mit Mitigation enthalten,
- offene Fragen sichtbar machen,
- Django Building Blocks mit konkreter Django-Zuordnung benennen,
- den Status `ready-for-review` erst setzen, wenn Folgeagenten daraus arbeiten
  koennen.

Ein schlechtes Sheet:

- enthaelt nur Fliesstext ohne strukturierte Felder,
- vermischt fachliche Ziele, Loesungen und Annahmen,
- nennt keine Risiken oder offenen Fragen,
- liefert keine Django-Zuordnung,
- erfindet Details, statt Annahmen und Fragen zu markieren.

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
