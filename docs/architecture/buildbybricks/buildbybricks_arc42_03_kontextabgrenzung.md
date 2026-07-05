# 3. Kontextabgrenzung

## 3.1 Ziel der Kontextabgrenzung

Dieses Kapitel beschreibt die fachlichen und technischen Grenzen von BuildByBricks.

BuildByBricks ist eine Open-Source-Anwendung zur Erstellung workflowbasierter Standardlösungen aus fertigen Bricks. Das System ermöglicht Nutzern, vorhandene fachliche Bausteine zu aktivieren, zu konfigurieren und zu einem nutzbaren Workflow zusammenzustellen.

Die Kontextabgrenzung stellt klar:

- welche Funktionen innerhalb von BuildByBricks liegen,
- welche Aufgaben außerhalb des Systems bleiben,
- welche Nutzergruppen mit dem System interagieren,
- welche externen Systeme angebunden werden können,
- welche Bestandteile nur zum Entwicklungsprozess nach BuildBySpec gehören.

Besonders wichtig ist die Trennung zwischen:

- BuildByBricks als nutzbarer Workflow-Software,
- BuildBySpec als Entwicklungs- und Qualitätsprozess zur Erstellung neuer Bricks.

BuildByBricks erzeugt zur Laufzeit keinen neuen Code. Neue Bricks entstehen außerhalb der Laufzeitfunktion durch Entwicklung nach BuildBySpec.

## 3.2 Fachlicher Systemkontext

BuildByBricks steht fachlich im Zentrum eines konfigurierbaren Workflow-Systems.

Ein Nutzer hat wiederkehrende Standardaufgaben und möchte diese in einer Software strukturiert abbilden. Dafür wählt oder konfiguriert er einen Workflow aus vorhandenen Bricks.

Der fachliche Kontext umfasst:

- Nutzer mit konkreten Standardaufgaben,
- Projekte oder Arbeitsbereiche,
- Workflow-Blueprints,
- aktivierte Bricks,
- Dashboard-Konfigurationen,
- fachliche Daten wie Rechnungen, Termine, Aufgaben, Verträge oder Dokumente,
- externe Dienste wie E-Mail, Kalender oder Dateiablagen,
- Entwickler und Maintainer, die neue Bricks nach BuildBySpec erstellen.

BuildByBricks ist dabei nicht der Ersteller beliebiger neuer Fachlogik. Es stellt vorhandene, geprüfte Bausteine bereit und erlaubt deren workfloworientierte Konfiguration.

## 3.3 Fachliche Systemgrenze

Innerhalb der fachlichen Systemgrenze von BuildByBricks liegen:

- Verwaltung von Projekten oder Arbeitsbereichen,
- Auswahl und Aktivierung vorhandener Bricks,
- Konfiguration von Workflows,
- Konfiguration von Dashboard-Kacheln,
- Darstellung des aktiven Workflows im Dashboard,
- Navigation entlang aktivierter Workflow-Bereiche,
- Nutzung der fachlichen Funktionen einzelner Bricks,
- Verwaltung brickbezogener Daten,
- Verwaltung von Aufgaben, Status, Fristen und Übersichten,
- Benutzer- und Berechtigungsverwaltung,
- Speicherung und Anzeige der konfigurierten Workflow-Struktur.

Außerhalb der fachlichen Systemgrenze liegen:

- automatische Codegenerierung,
- Erstellung beliebiger neuer Datenmodelle als allgemeines Plattformprinzip,
- freie Installation unstrukturierter Fremdmodule,
- Entwicklung neuer Bricks innerhalb der Laufzeitoberfläche,
- Ersatz einer Individualentwicklung durch beliebige UI-Konfiguration,
- fachliche Entscheidungen ohne dokumentierte Spezifikation,
- nicht kontrollierte Erweiterung von Businesslogik durch Endnutzer.

Kontrollierte dynamische Strukturen, zum Beispiel in Umfrage- oder Formular-Bricks, sind als Ausnahme möglich. Sie bleiben jedoch Bestandteil eines klar abgegrenzten Bricks und müssen durch Architektur, Validierung, Sicherheit und Tests beschrieben sein.

## 3.4 Nutzergruppen

### Endnutzer

Endnutzer verwenden BuildByBricks zur täglichen Arbeit mit einem konfigurierten Workflow.

Sie nutzen beispielsweise:

- Dashboard,
- Aufgaben,
- Rechnungen,
- Termine,
- Verträge,
- Dokumente,
- Übersichten,
- Statusinformationen,
- Fristen,
- einfache Konfigurationsmöglichkeiten.

Endnutzer entwickeln keine neuen Bricks und erzeugen keinen Code.

### Projekt- oder Workflow-Verantwortliche

Projekt- oder Workflow-Verantwortliche konfigurieren, welche Bricks in einem Projekt aktiv sind und wie der Workflow dargestellt wird.

Sie können beispielsweise:

- einen Workflow-Blueprint auswählen,
- Bricks aktivieren oder deaktivieren,
- Dashboard-Kacheln konfigurieren,
- Navigation und sichtbare Bereiche anpassen,
- Statuswerte oder einfache Workflow-Parameter pflegen,
- Rollen und Berechtigungen verwalten.

Diese Nutzergruppe arbeitet mit vorhandenen Bausteinen. Sie verändert nicht den Quellcode und erstellt keine neue Fachlogik außerhalb der vorgesehenen Konfiguration.

### Administratoren

Administratoren betreiben und verwalten die technische Installation.

Sie kümmern sich um:

- Benutzerverwaltung,
- Rechtevergabe,
- Systemkonfiguration,
- Deployment,
- Updates,
- Backups,
- Sicherheitseinstellungen,
- technische Überwachung,
- Fehleranalyse.

Administratoren haben keinen fachlichen Freibrief zur Änderung von Bricks. Auch administrative Konfiguration bleibt innerhalb der vom System vorgesehenen Grenzen.

### Brick-Entwickler

Brick-Entwickler erstellen neue fachliche Bricks nach dem BuildBySpec-Prinzip.

Sie arbeiten außerhalb der normalen Laufzeitkonfiguration von BuildByBricks und verwenden dafür:

- Architektur-Sheets nach arc42,
- BPMN-Modelle,
- Flussdiagramme,
- Objektdiagramme,
- Workorders,
- Testspezifikationen,
- Coding Standards,
- Testarchitektur,
- DevSecOps-Prüfungen,
- ADRs.

Brick-Entwickler erweitern BuildByBricks durch neue, geprüfte Softwarebestandteile. Diese Erweiterung erfolgt im Entwicklungsprozess, nicht durch Endnutzerkonfiguration.

### Maintainer

Maintainer verantworten die langfristige Qualität des Open-Source-Projekts.

Sie prüfen insbesondere:

- Architekturkonformität,
- Einhaltung der Brick-Vorgaben,
- Testabdeckung,
- Code-Komplexität,
- Security Checks,
- Dokumentation,
- ADRs,
- Kompatibilität neuer Bricks,
- Einhaltung der BuildBySpec-Prinzipien.

Maintainer entscheiden, ob ein neuer Brick oder eine Änderung Bestandteil von BuildByBricks werden darf.

## 3.5 Externe fachliche Systeme

Je nach aktiviertem Brick kann BuildByBricks mit externen Systemen interagieren.

Mögliche externe fachliche Systeme sind:

- E-Mail-Systeme,
- Kalenderdienste,
- Dateiablagen,
- Dokumentenexporte,
- Buchhaltungs- oder Steuerwerkzeuge,
- Zahlungs- oder Bankdatenquellen,
- externe Kontaktverwaltungen,
- KI- oder RAG-Dienste in späteren Bricks.

Diese Systeme sind nicht zwingender Bestandteil des Kerns. Sie werden nur über klar definierte Brick-Funktionen oder Integrationskomponenten angebunden.

BuildByBricks muss daher zwischen Core-Funktionen und optionalen Integrationen unterscheiden.

## 3.6 Technischer Systemkontext

Technisch besteht BuildByBricks aus einer Django/Python-Anwendung mit PostgreSQL als bevorzugter Datenbank.

Zum technischen Kontext gehören:

- Webbrowser der Nutzer,
- Django-Anwendung,
- PostgreSQL-Datenbank,
- statische Dateien,
- Medien- und Uploadspeicher,
- optionaler Mailserver,
- optionaler Kalenderdienst,
- optionaler Dokumentenexport,
- optionaler Hintergrundjob-Prozessor,
- Docker-basierte Laufzeitumgebung,
- Reverse Proxy für produktiven Betrieb,
- GitHub und CI-Pipeline im Entwicklungsprozess.

Für spätere KI- oder RAG-Funktionen können zusätzliche technische Systeme hinzukommen, zum Beispiel:

- LLM-Dienst,
- lokales Modell,
- Embedding-Service,
- Vektorspeicher,
- pgvector,
- Dokumentenparser,
- RAG-spezifische Hintergrundjobs.

Diese Systeme sind Erweiterungen spezifischer Bricks und nicht zwingender Bestandteil des initialen Kerns.

## 3.7 Technische Systemgrenze

Innerhalb der technischen Systemgrenze liegen:

- Django-Anwendung,
- Django-Apps für Core und Bricks,
- Datenmodelle,
- Views,
- Forms,
- Templates,
- Services,
- Policies,
- Validators,
- Dashboard-Komponenten,
- Workflow-Konfiguration,
- Benutzer- und Rechteverwaltung,
- Datenbankmigrationen,
- Tests,
- statische Dateien,
- Konfigurationsmechanismen,
- dokumentierte Schnittstellen zu externen Diensten.

Außerhalb der technischen Systemgrenze liegen:

- Betriebssystem des Servers,
- Docker Host,
- Reverse Proxy,
- externe Mailserver,
- externe Kalenderdienste,
- externe Zahlungsanbieter,
- externe Dateiablagen,
- GitHub als Entwicklungsplattform,
- Codex als Entwicklungswerkzeug,
- externe KI- oder LLM-Dienste,
- Browser des Nutzers,
- produktive Infrastruktur des Betreibers.

BuildByBricks muss diese externen Systeme über klar definierte Schnittstellen verwenden und darf keine impliziten Annahmen über deren interne Implementierung treffen.

## 3.8 Entwicklungs- und Laufzeitkontext

BuildByBricks hat zwei unterschiedliche Kontexte, die klar getrennt werden müssen.

### Laufzeitkontext

Im Laufzeitkontext nutzen Endnutzer und Administratoren die Anwendung.

Der Laufzeitkontext umfasst:

- Anmeldung,
- Projekt- oder Workflow-Auswahl,
- Aktivierung vorhandener Bricks,
- Dashboard-Nutzung,
- Bearbeitung fachlicher Daten,
- Konfiguration vorhandener Workflow-Optionen,
- Nutzung von Exporten oder Integrationen,
- Rollen- und Rechteprüfung.

Im Laufzeitkontext entsteht kein neuer Quellcode.

### Entwicklungskontext

Im Entwicklungskontext entstehen neue Bricks oder Änderungen an bestehenden Bricks.

Der Entwicklungskontext umfasst:

- Architekturplanung,
- arc42-Sheets,
- BPMN-Modelle,
- Flussdiagramme,
- Objektdiagramme,
- Workorders,
- Codex-gestützte Umsetzung,
- Tests,
- DevSecOps-Prüfungen,
- Pull Requests,
- Reviews,
- ADRs,
- Dokumentation.

Der Entwicklungskontext ist methodisch durch BuildBySpec geprägt.

Diese Trennung ist verbindlich. BuildBySpec beschreibt, wie BuildByBricks gebaut wird. BuildByBricks selbst ist nicht der Codegenerator für neue Bricks.

### 3.8.1 Specification-driven Development im Entwicklungskontext

Im Entwicklungskontext wird KI-gestützte Umsetzung als Architektur- und Ticketcompiler verstanden.

Die steuernden Eingaben sind:

- fachliche Spezifikationen,
- Architektur-Sheets,
- ADRs,
- BPMN-Modelle,
- Flussdiagramme,
- Objektdiagramme,
- Workorders,
- FIX-Workorders,
- Testvorgaben,
- Akzeptanzkriterien,
- Evidence-Anforderungen.

Der erzeugte Quellcode ist ein nachgelagertes Artefakt dieses Prozesses.

Diese Einordnung ist wichtig für die Kontextabgrenzung: Codex und andere KI-Werkzeuge gehören zum Entwicklungskontext, nicht zum Laufzeitkontext von BuildByBricks. Sie dürfen die Architektur nicht autonom erweitern und keine fachlichen Entscheidungen ohne dokumentierte Spezifikation treffen.

## 3.9 Kontext: Dashboard

Das Dashboard steht fachlich zwischen Nutzer, Workflow und Bricks.

Es erhält Informationen aus aktivierten Bricks und stellt diese workflowbezogen dar.

Das Dashboard kann anzeigen:

- offene Aufgaben,
- offene Rechnungen,
- fällige Zahlungen,
- Termine,
- Fristen,
- Warnungen,
- Fortschritte,
- Kennzahlen,
- Schnellaktionen,
- Statusinformationen.

Dashboard-Elemente dürfen nicht beliebig und losgelöst vom Workflow angezeigt werden. Sie müssen aus dem aktiven Workflow ableitbar sein und eine klare fachliche Funktion erfüllen.

Jeder Dashboard-Beitrag muss daher einem Brick, einem Workflow-Kontext und einer Berechtigungssituation zugeordnet werden können.

## 3.10 Kontext: Workflow

Der Workflow beschreibt die fachliche Ordnung der aktivierten Bricks.

Ein Workflow beantwortet insbesondere:

- Welche Aufgaben gehören zusammen?
- Welche Bricks werden benötigt?
- Welche Reihenfolge oder Abhängigkeit besteht zwischen Aufgaben?
- Welche Statuswerte sind relevant?
- Welche Fristen sind wichtig?
- Welche Informationen müssen im Dashboard sichtbar sein?
- Welche Rollen dürfen welche Schritte sehen oder bearbeiten?

Der Workflow ist damit nicht nur eine UI-Konfiguration, sondern die fachliche Struktur eines BuildByBricks-Projekts.

## 3.11 Kontext: Brick

Ein Brick ist ein fachlicher Standardbaustein mit klarer Verantwortung.

Ein Brick kann bereitstellen:

- Datenmodelle,
- Views,
- Forms,
- Services,
- Validierungen,
- Policies,
- Templates,
- Navigationseinträge,
- Dashboard-Beiträge,
- Workflow-Schritte,
- Tests,
- Dokumentation.

Ein Brick muss seine fachliche Grenze kennen. Er darf andere Bricks nicht unkontrolliert voraussetzen oder deren Fachlogik übernehmen.

Abhängigkeiten zwischen Bricks müssen explizit beschrieben werden.

## 3.12 Kontext: BuildBySpec

BuildBySpec ist die Methode zur Entwicklung von BuildByBricks und seiner Bricks.

BuildBySpec liegt nicht als Endnutzerfunktion im Zentrum des Laufzeitsystems, sondern als Entwicklungsprozess außerhalb der normalen Nutzung.

BuildBySpec liefert:

- Spezifikationsstruktur,
- Architekturdisziplin,
- Workorder-Prozess,
- FIX-Workorder-Prozess,
- Testdisziplin,
- Dokumentationspflicht,
- Qualitätsnachweise,
- Nachvollziehbarkeit,
- KI-unterstützte Entwicklungsfähigkeit.

BuildBySpec beruht auf der Erkenntnis, dass KI-gestützte Entwicklung nur dann zuverlässig funktioniert, wenn Spezifikation, Architektur, Scope und Tests explizit beschrieben sind. KI kann Umsetzung beschleunigen, ersetzt aber nicht die fachliche und architektonische Verantwortung.

Die KI wird deshalb als Compiler für Architektur- und Ticketartefakte verstanden. Sie übersetzt strukturierte menschliche Spezifikationen in Code, Tests und Anpassungen. Sie ist jedoch nicht der fachliche Entscheider, nicht der autonome Architekt und nicht der Ersatz für Qualitätssicherung.

Neue Bricks dürfen nur dann in BuildByBricks aufgenommen werden, wenn sie nach BuildBySpec ausreichend beschrieben, umgesetzt, getestet und dokumentiert wurden.

## 3.13 Externe Entwicklungssysteme

Im Entwicklungskontext nutzt BuildByBricks externe Werkzeuge.

Dazu gehören:

- GitHub für Repository, Issues, Pull Requests und Releases,
- Codex für KI-gestützte Umsetzung auf Basis von Workorders,
- CI-Pipeline für automatisierte Prüfungen,
- Security-Scanner,
- Linter,
- Testframeworks,
- Dokumentationswerkzeuge,
- Container- und Deploymentwerkzeuge.

Diese Systeme gehören nicht zur Laufzeitfunktion von BuildByBricks, sind aber für die Qualität des Projekts wesentlich.

Codex-gestützte Umsetzung darf nur auf Basis klarer Workorders erfolgen. Bei Änderungen an bestehenden Funktionen sind FIX-Workorders zu verwenden, die betroffene Bereiche, Dateien oder Komponenten, Ist-Verhalten, Soll-Verhalten, Nicht-Ziele und Testnachweise explizit benennen.

## 3.14 Schnittstellenübersicht

Die wichtigsten Schnittstellen von BuildByBricks sind:

### Benutzeroberfläche

Nutzer greifen über einen Webbrowser auf die Anwendung zu.

Die Benutzeroberfläche wird serverseitig mit Django Templates und Bootstrap 5 gerendert.

### Datenbank

BuildByBricks speichert fachliche Daten, Konfigurationen, Benutzer, Berechtigungen, Workflows und Brick-Daten in einer relationalen Datenbank.

PostgreSQL ist die bevorzugte produktive Datenbank.

### Datei- und Medienablage

Bricks können Dateien, Dokumente oder Exporte verwalten.

Dateien müssen kontrolliert gespeichert, validiert und berechtigungsabhängig zugänglich gemacht werden.

### E-Mail

E-Mail kann für Benachrichtigungen, Einladungen, Erinnerungen oder Dokumentenversand verwendet werden.

E-Mail ist eine optionale externe Integration.

### Kalender

Kalenderfunktionen können über Bricks angebunden werden, wenn Workflows Termine, Fristen oder Planung enthalten.

### Export

BuildByBricks oder einzelne Bricks können Daten exportieren, zum Beispiel als PDF, CSV oder andere strukturierte Formate.

### KI/RAG

Spätere Bricks können KI- oder RAG-Funktionen integrieren.

Solche Funktionen sind optional, brickbezogen und müssen eigene Architektur-, Sicherheits- und Testanforderungen erfüllen.

## 3.15 Abgrenzung zu ähnlichen Systemtypen

BuildByBricks ist kein klassisches Content-Management-System.

Es verwaltet nicht primär Inhalte und Seiten, sondern fachliche Workflows und Standardaufgaben.

BuildByBricks ist kein Plugin-System.

Bricks sind keine beliebig installierbaren Fremdmodule, sondern geprüfte fachliche Bausteine innerhalb einer kontrollierten Architektur.

BuildByBricks ist kein Low-Code-System.

Nutzer können Workflows konfigurieren, aber keine beliebige neue Fachlogik, Datenmodelle oder Anwendungen zur Laufzeit erzeugen.

BuildByBricks ist kein Codegenerator.

Neue Bricks werden entwickelt, getestet und dokumentiert. Sie entstehen nicht automatisch durch Endnutzerinteraktion.

BuildByBricks ist kein reines Dashboard-System.

Das Dashboard ist wichtig, aber es repräsentiert den Workflow. Es ersetzt nicht die fachlichen Funktionen der Bricks.

## 3.16 Zusammenfassung

BuildByBricks liegt im Zentrum eines workflowbasierten Anwendungskontexts.

Innerhalb des Systems befinden sich:

- Projekte,
- Workflows,
- aktivierte Bricks,
- Dashboard-Konfiguration,
- fachliche Daten,
- Benutzer,
- Berechtigungen,
- Navigation,
- Workflow-Darstellung.

Außerhalb des Systems befinden sich:

- Entwicklung neuer Bricks,
- Codex-gestützte Umsetzung,
- GitHub,
- CI/CD,
- externe Mail-, Kalender-, Datei-, Zahlungs- oder KI-Dienste,
- produktive Infrastruktur.

Die wichtigste Kontextentscheidung lautet:

> BuildByBricks ist die nutzbare Workflow-Software.  
> BuildBySpec ist der Entwicklungsprozess zur Erstellung und Qualitätssicherung dieser Software und ihrer Bricks.

Diese Trennung verhindert, dass BuildByBricks versehentlich zu einem Codegenerator, Plugin-System oder allgemeinen Low-Code-Builder wird.

Zusätzlich gilt:

> KI-gestützte Werkzeuge gehören in den Entwicklungskontext.  
> Sie kompilieren Spezifikationen, Architekturvorgaben und Workorders in Code, ersetzen aber nicht Engineering, Architekturverantwortung und Qualitätssicherung.
