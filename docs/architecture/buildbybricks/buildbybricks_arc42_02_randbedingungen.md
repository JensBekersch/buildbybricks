# BuildByBricks – arc42 Kapitel 2: Randbedingungen

## 2. Randbedingungen

### 2.1 Technologische Randbedingungen

BuildByBricks wird als Django/Python-Anwendung umgesetzt.

Die grundlegende Architekturentscheidung ist in ADR-001 festgehalten:

> BuildByBricks wird als Django/Python-Projekt umgesetzt.  
> Das System wird nicht in PHP realisiert.

Die wichtigsten technologischen Randbedingungen sind:

- Python als Programmiersprache,
- Django als Webframework,
- PostgreSQL als bevorzugte relationale Datenbank,
- Docker-first für lokale Entwicklung und Deployment,
- Bootstrap 5 für die Benutzeroberfläche,
- Django Template Engine für serverseitiges Rendering,
- GitHub als zentrales Repository,
- Codex-gestützte Umsetzung auf Basis klarer Workorders,
- Docs-as-Code für Architektur, ADRs, Workorders und Testspezifikationen.

BuildByBricks soll nicht auf klassisches Shared Hosting optimiert werden. Die Anwendung wird so aufgebaut, dass sie reproduzierbar lokal und auf Servern per Docker betrieben werden kann.

### 2.2 Methodische Randbedingungen

BuildByBricks wird nach den Prinzipien von BuildBySpec entwickelt.

Das bedeutet:

- fachliche Anforderungen werden vor der Umsetzung beschrieben,
- Architekturentscheidungen werden dokumentiert,
- Bricks werden über Architektur-Sheets abgegrenzt,
- fachliche Abläufe werden modelliert,
- Testbarkeit wird vor der Umsetzung berücksichtigt,
- Änderungen erfolgen über nachvollziehbare Workorders,
- Dokumentation ist Bestandteil der Entwicklung und kein nachträglicher Zusatz.

BuildBySpec ist nicht Teil der Laufzeitfunktion von BuildByBricks. BuildByBricks erzeugt selbst keinen Code. BuildBySpec beschreibt den Herstellungsprozess, nach dem BuildByBricks und neue Bricks entwickelt werden.

### 2.2.1 Specification-driven Development als methodische Randbedingung

BuildByBricks wird spezifikationsgetrieben entwickelt.

Das bedeutet:

- Der primäre Entwicklungsgegenstand ist die präzise Spezifikation, nicht der spontane Quellcode.
- Fachliche Anforderungen, Architekturentscheidungen, Scope-Grenzen, Nicht-Ziele, Akzeptanzkriterien und Testvorgaben müssen vor der Umsetzung beschrieben werden.
- Code entsteht als Ergebnis eines kontrollierten Spezifikationsprozesses.
- KI-gestützte Entwicklungswerkzeuge werden als Architektur- und Ticketcompiler eingesetzt.
- KI darf keine impliziten Architekturentscheidungen treffen.
- KI darf keine fachlichen Lücken eigenständig schließen, wenn diese Lücken für Architektur, Datenmodell, Sicherheit oder Testbarkeit relevant sind.
- Jede Umsetzung muss durch Tests, Evidence und Dokumentation prüfbar bleiben.

Die methodische Grundform lautet:

> Spezifikation → Architektur → Workorder → Umsetzung → Tests → Evidence → Living Documentation

Diese Randbedingung ist besonders wichtig, weil KI-gestützte Umsetzung typische Risiken mitbringt:

- Overengineering,
- zu breite oder ungewollte Architekturänderungen,
- Umsetzung nur offensichtlicher Teilbereiche,
- falsche Annahmen bei implizitem Kontext,
- fehlende Reflexion komplexer Seiteneffekte,
- Erzeugung zusätzlicher Abstraktionen ohne fachliche Notwendigkeit.

Deshalb müssen Workorders so formuliert sein, dass die KI nicht raten muss. Kontext, Ziel, betroffene Komponenten, In-Scope, Out-of-Scope, Testpflichten und Definition of Done sind explizit anzugeben.


### 2.3 Architektur- und Dokumentationspflichten für Bricks

Jeder Brick muss vor seiner Umsetzung fachlich und architektonisch beschrieben werden.

Für jeden Brick sind mindestens folgende Artefakte erforderlich:

1. Architektur-Sheet nach arc42  
   Das Architektur-Sheet beschreibt Zweck, Kontext, fachliche Abgrenzung, Bausteine, Datenstrukturen, Qualitätsanforderungen, Risiken und relevante Architekturentscheidungen des Bricks.

2. BPMN-Modell(e)  
   Fachliche Abläufe, Prozessschritte, Entscheidungen, Rollen und Zustände müssen als BPMN-Modell beschrieben werden.

3. Flussdiagramme  
   Flussdiagramme beschreiben technische oder fachliche Entscheidungslogik, Validierungen, Statuswechsel, Fehlerpfade und Sonderfälle.

4. Objektdiagramm(e)  
   Objektdiagramme beschreiben zentrale fachliche Objekte, ihre Beziehungen und Verantwortlichkeiten.

5. Testarchitektur-Konformität  
   Jeder Brick muss die übergreifende Testarchitektur von BuildByBricks einhalten. Die Testarchitektur definiert verbindliche Testarten, Testebenen, Testdaten, Qualitätsanforderungen und Nachweispflichten.

Ein Brick gilt erst dann als architekturfähig, wenn diese Artefakte ausreichend beschrieben sind.

### 2.4 Technische Struktur von Bricks

Ein Brick ist ein fachlicher Standardbaustein innerhalb von BuildByBricks.

Technisch kann ein Brick durch eine Django-App oder durch klar abgegrenzte Komponenten innerhalb einer Django-App umgesetzt werden. Die konkrete technische Struktur richtet sich nach fachlicher Größe, Wiederverwendbarkeit und Kopplung.

Ein Brick muss mindestens folgende Eigenschaften besitzen:

- klar definierte fachliche Verantwortung,
- klar abgegrenzten Datenbereich,
- definierte Schnittstellen zu anderen Bricks,
- definierte Navigations- und Dashboard-Beiträge,
- dokumentierte Konfigurationsmöglichkeiten,
- definierte Berechtigungsanforderungen,
- eigene Tests,
- dokumentierte Risiken und Randbedingungen.

Bricks dürfen nicht heimlich Fachlogik anderer Bricks übernehmen. Gemeinsame Funktionen müssen entweder im Core, in einer gemeinsamen Basiskomponente oder in einem bewusst definierten Shared-Konzept liegen.

### 2.5 Klassenbasierte Architekturbausteine

BuildByBricks verwendet klassenbasierte Architekturbausteine für zentrale Django-Komponenten.

Dies gilt insbesondere für:

- Views,
- Models,
- Forms,
- Admin-Konfigurationen,
- Services,
- Policies,
- Validators,
- Registries,
- Importer,
- Exporter,
- Dashboard-Widgets,
- Workflow-Komponenten,
- Brick-Metadaten,
- Konfigurationsobjekte.

Function-Based Views werden nicht verwendet.

Der Grundsatz lautet:

> Öffentliche Architekturbausteine sind klassenbasiert.  
> Kleine private Hilfsfunktionen sind erlaubt, wenn sie lokal begrenzt, rein technisch und pythonic sind.

Erlaubt sind beispielsweise kleine interne Hilfsfunktionen zur Normalisierung, Formatierung oder technischen Vereinfachung, sofern sie keine eigene fachliche Verantwortung tragen.

Nicht erlaubt sind:

- Function-Based Views,
- lose Businesslogik in Views,
- globale Utility-Sammlungen als Ersatz für klare Architektur,
- unstrukturierte Script-Logik,
- fachliche Logik ohne klaren Verantwortungsort.

### 2.6 Coding Standard

BuildByBricks folgt einem Python- und Django-konformen Coding Standard.

Verbindliche Grundlagen sind:

- PEP 8 für allgemeinen Python-Code-Stil,
- PEP 257 für Docstrings,
- Django Coding Style als Django-spezifische Ergänzung,
- pythonic code vor künstlicher Architektur,
- Clean Code nur, soweit er dem Pythonic Way nicht widerspricht.

Der Coding Standard soll Lesbarkeit, Wartbarkeit und KI-gestützte Weiterentwicklung unterstützen.

Die wichtigsten Prinzipien sind:

- sprechende Namen,
- kurze und verständliche Methoden,
- klare Verantwortlichkeiten,
- explizite Abhängigkeiten,
- einfache Django-Konventionen,
- nachvollziehbare Datenflüsse,
- geringe Kopplung zwischen Bricks,
- keine unnötige Abstraktion,
- keine Java-artige Service- oder Interface-Explosion.

### 2.7 Tooling für Codequalität

Die konkrete Toolchain wird zentral über `pyproject.toml` konfiguriert.

Vorgesehene Werkzeuge sind:

- Ruff für Linting und einfache Komplexitätsregeln,
- Ruff oder Black für Formatierung,
- mypy für statische Typprüfung,
- pytest für Tests,
- coverage.py oder pytest-cov für Testabdeckung,
- Radon oder ein vergleichbares Werkzeug für Komplexitätsmetriken.

Die finale Auswahl und Konfiguration wird in der Testarchitektur und in einem separaten ADR festgelegt.

Grundsatz:

> Codequalität darf nicht nur durch manuelle Reviews entstehen.  
> Sie muss durch automatisierte Prüfungen unterstützt werden.

### 2.8 Code-Komplexität als verbindliche Qualitätsrandbedingung

BuildByBricks prüft Code nicht nur auf Formatierung, Linting und Testabdeckung, sondern auch auf strukturelle Komplexität.

Ziel ist es, dauerhaft wartbaren, verständlichen und testbaren Code zu erzeugen. Dies ist besonders wichtig, weil BuildByBricks mit klaren Workorders und KI-gestützter Umsetzung entwickelt wird. Automatisch erzeugter oder assistiert geschriebener Code darf nicht durch überlange Methoden, verschachtelte Kontrollflüsse oder unklare Verantwortlichkeiten unwartbar werden.

Die Prüfung der Code-Komplexität ist daher verbindlicher Bestandteil der Qualitätssicherung.

Geprüft werden insbesondere:

- zyklomatische Komplexität von Methoden und Funktionen,
- zu stark verschachtelte Kontrollstrukturen,
- überlange Methoden,
- überlange Klassen,
- zu große Dateien,
- zu viele Verantwortlichkeiten in einer Klasse,
- zu viele Parameter in Methoden,
- duplizierte Logik,
- unnötige Vererbungstiefe,
- unklare Kopplung zwischen Bricks,
- versteckte Businesslogik in Views, Forms oder Templates.

Grundsatz:

> Komplexität muss entweder reduziert oder bewusst begründet werden.  
> Unbegründete Komplexität ist ein Architektur- und Qualitätsmangel.

Die konkreten Grenzwerte werden in der Testarchitektur und Tool-Konfiguration festgelegt. Als Startpunkt gelten folgende Orientierungswerte:

- Methoden sollen kurz und fachlich klar abgegrenzt sein.
- Eine Methode darf nur eine klar erkennbare Verantwortung haben.
- Stark verschachtelte `if`-/`else`-/`try`-Strukturen sind zu vermeiden.
- Wiederholte Fachlogik muss in Services, Policies oder Validatoren ausgelagert werden.
- Views dürfen keine komplexe Businesslogik enthalten.
- Forms dürfen Validierungslogik enthalten, aber keine fachlichen Prozessentscheidungen.
- Models dürfen fachliche Invarianten schützen, aber nicht zu God Objects werden.
- Services dürfen Fachlogik bündeln, müssen aber klein, testbar und klar benannt bleiben.

Für Django gilt insbesondere:

- Class-Based Views bleiben schlank.
- `get_context_data()` darf nicht zum Sammelplatz für Businesslogik werden.
- `form_valid()` und `form_invalid()` dürfen keine komplexen Prozessabläufe enthalten.
- Query-Logik wird bei wachsender Komplexität in Manager, QuerySets oder Services ausgelagert.
- Dashboard-Widgets kapseln ihre Datenbeschaffung und Darstellung klar.
- Workflow-Logik wird nicht in Templates implementiert.

Komplexitätsprüfungen müssen automatisierbar sein und sollen Bestandteil der lokalen Prüfungen sowie der CI-Pipeline werden.

Mögliche Prüfwerkzeuge sind:

- Ruff für McCabe-/Komplexitätsregeln,
- Radon oder vergleichbare Werkzeuge für zyklomatische Komplexität und Maintainability Index,
- pytest/coverage zur Absicherung komplexer Pfade,
- zusätzliche Architekturtests für Brick-Grenzen und unerlaubte Abhängigkeiten.

Ein Pull Request oder eine Codex-Umsetzung darf nicht allein deshalb akzeptiert werden, weil Tests grün sind. Wenn die Lösung unnötig komplex ist, muss sie vereinfacht oder begründet werden.

Jede Workorder soll daher implizit folgende Qualitätsfrage beantworten:

> Ist die Lösung fachlich korrekt, getestet und strukturell einfach genug, um langfristig gewartet zu werden?

### 2.9 Kommentierungs- und Dokumentationsstandard im Code

Jede Python-Datei erhält einen kurzen Modul-Docstring.

Der Modul-Docstring beschreibt:

- Zweck der Datei,
- Rolle im BuildByBricks-Kontext,
- fachliche oder technische Abgrenzung.

Jede öffentliche Klasse erhält einen Docstring.

Der Klassen-Docstring beschreibt:

- Verantwortung der Klasse,
- wichtige Invarianten,
- Abgrenzung zu anderen Klassen,
- relevante Nutzungshinweise.

Öffentliche Methoden erhalten dann einen Docstring, wenn:

- sie fachliche Logik enthalten,
- sie Teil eines Service-, Policy-, Registry- oder Brick-Kontrakts sind,
- ihr Verhalten nicht unmittelbar offensichtlich ist,
- sie von anderen Bricks oder Komponenten genutzt werden.

Inline-Kommentare werden sparsam verwendet.

Inline-Kommentare erklären nicht, was der Code offensichtlich tut, sondern warum eine bestimmte Entscheidung getroffen wurde.

Geeignete Gründe für Inline-Kommentare sind:

- fachliche Sonderregeln,
- Sicherheitsaspekte,
- nicht offensichtliche Validierungen,
- technische Workarounds,
- bewusst getroffene Architekturkompromisse.

### 2.10 Testarchitektur als verbindliche Randbedingung

Die Testarchitektur von BuildByBricks ist verbindlich.

Auch wenn sie separat beschrieben wird, gilt bereits auf übergeordneter Architekturebene:

- Jeder Brick benötigt eigene Tests.
- Fachliche Kernlogik muss automatisiert testbar sein.
- Tests müssen nachvollziehbare Testdaten verwenden.
- Kritische Workflows benötigen E2E- oder Integrationstests.
- Dashboard- und Workflow-Konfigurationen müssen testbar sein.
- Fehlerfälle und Sonderfälle müssen berücksichtigt werden.
- Tests müssen reproduzierbar und automatisierbar sein.

Ein Brick darf nicht als fertig gelten, wenn seine Testbarkeit nicht nachgewiesen ist.

Die finale Testarchitektur legt später fest:

- Testebenen,
- Testarten,
- Namenskonventionen,
- Testdatenstrategie,
- Coverage-Ziele,
- Pflichtnachweise,
- CI-Prüfungen,
- Umgang mit E2E-Tests,
- Umgang mit Regressionstests.

### 2.11 Workflow-Konfiguration als Produktkern

BuildByBricks ermöglicht Nutzern, eigene Workflows aus fertigen Bricks zusammenzustellen.

Diese Konfiguration ist der Kern des Produkts.

Konfigurierbar sind insbesondere:

- aktivierte Bricks,
- sichtbare Workflow-Schritte,
- Dashboard-Kacheln,
- Reihenfolge und Gruppierung von Dashboard-Elementen,
- Navigationsstruktur,
- einfache Statuswerte,
- Projektbezeichnungen,
- sichtbare Aufgabenbereiche,
- relevante Fristen und Übersichten,
- einfache Darstellungsoptionen.

Die Konfiguration verändert die Nutzung und Darstellung vorhandener Funktionen. Sie erzeugt keinen neuen Code.

### 2.12 Begrenzung der Konfigurierbarkeit

BuildByBricks ist kein allgemeines Low-Code- oder No-Code-System.

Nicht vorgesehen sind:

- beliebige Codegenerierung durch Endnutzer,
- freie Erstellung neuer Fachlogik zur Laufzeit,
- freie Installation unstrukturierter Fremdmodule,
- generische Modellierung beliebiger Anwendungen,
- Ersetzung der Softwareentwicklung durch reine UI-Konfiguration.

Die Grenze ist bewusst gesetzt:

> Nutzer konfigurieren vorhandene Bricks und Workflows.  
> Neue Bricks werden durch Entwicklung nach BuildBySpec erstellt.

### 2.13 Dynamische Strukturen als kontrollierte Ausnahme

BuildByBricks erstellt grundsätzlich keine beliebigen Datenmodelle zur Laufzeit.

Spezifische Bricks dürfen jedoch kontrollierte dynamische Strukturen verwenden, wenn dies fachlich notwendig ist.

Beispiele sind:

- Umfragen,
- Fragebögen,
- konfigurierbare Formulare,
- strukturierte Erfassungsmasken,
- wiederverwendbare Feldgruppen innerhalb eines klar abgegrenzten Bricks.

Solche dynamischen Strukturen sind nur innerhalb des jeweiligen Bricks erlaubt und müssen vollständig beschrieben werden durch:

- Architektur-Sheet,
- Datenmodell,
- Validierungsregeln,
- Berechtigungskonzept,
- Sicherheitsbetrachtung,
- Testfälle,
- Migrations- oder Versionierungskonzept,
- Grenzen der Konfigurierbarkeit.

Diese Ausnahme macht BuildByBricks nicht zu einem allgemeinen Datenmodell-Builder.

### 2.14 Dashboard als verbindliche Workflow-Oberfläche

Das Dashboard ist die zentrale Repräsentation des aktiven Workflows.

Jeder Brick kann Dashboard-Beiträge bereitstellen, zum Beispiel:

- Kennzahlen,
- offene Aufgaben,
- Fristen,
- Warnungen,
- Statusanzeigen,
- Listen,
- Schnellaktionen,
- Fortschrittsanzeigen.

Dashboard-Beiträge müssen klar definieren:

- welche Daten sie anzeigen,
- aus welchem Brick sie stammen,
- für welche Workflows sie geeignet sind,
- welche Berechtigungen erforderlich sind,
- ob sie konfigurierbar sind,
- wie sie getestet werden.

Das Dashboard darf nicht zu einer unstrukturierten Sammlung beliebiger Widgets werden. Es muss immer den aktiven Workflow unterstützen.

### 2.15 Benutzeroberfläche

Die Benutzeroberfläche wird serverseitig mit Django Templates und Bootstrap 5 umgesetzt.

Die UI soll:

- einfach verständlich sein,
- workfloworientiert sein,
- auch ohne komplexes Frontend-Framework funktionieren,
- gut testbar bleiben,
- konsistente Komponenten verwenden,
- für spätere Erweiterungen offen bleiben.

JavaScript wird gezielt und sparsam eingesetzt.

Eine spätere Ergänzung durch HTMX ist möglich, wenn dadurch Interaktionen verbessert werden, ohne die Architektur unnötig zu verkomplizieren.

### 2.16 Open-Source-Randbedingung

BuildByBricks ist als Open-Source-Projekt geplant.

Daraus ergeben sich besondere Anforderungen:

- verständliche Projektstruktur,
- nachvollziehbare Architekturentscheidungen,
- klare Setup-Anleitung,
- gute Entwicklerdokumentation,
- reproduzierbare lokale Installation,
- saubere Lizenzierung,
- keine versteckten proprietären Kernbestandteile,
- gute Lesbarkeit für externe Mitwirkende.

Die konkrete Open-Source-Lizenz wird in einer separaten Architekturentscheidung festgelegt.

### 2.17 Betrieb und Deployment

BuildByBricks wird Docker-first entwickelt.

Für lokale Entwicklung und einfache Server-Deployments sollen bereitgestellt werden:

- `Dockerfile`,
- `docker-compose.yml`,
- `.env.example`,
- Makefile,
- Setup-Dokumentation,
- Datenbank-Migrationen,
- statische Dateien,
- Basis-Konfiguration für produktiven Betrieb.

PostgreSQL ist die bevorzugte produktive Datenbank.

SQLite kann optional für sehr einfache lokale Entwicklung unterstützt werden, sofern dadurch keine produktionsrelevanten Annahmen verfälscht werden. Die verbindliche Datenbank für realistische Entwicklung, Tests und Betrieb bleibt PostgreSQL.

### 2.18 DevSecOps als verbindliche Randbedingung

BuildByBricks berücksichtigt DevSecOps von Beginn an als verbindliche Architektur- und Qualitätsrandbedingung.

Sicherheit, Qualität, Build-Prozess, Tests, Deployment und Betrieb werden nicht getrennt voneinander betrachtet. Jede Änderung an BuildByBricks muss nachvollziehbar, testbar, prüfbar und reproduzierbar sein.

Der Grundsatz lautet:

> Jede Änderung muss fachlich korrekt, architektonisch sauber, getestet, sicherheitsgeprüft und reproduzierbar auslieferbar sein.

DevSecOps ist damit kein späterer Betriebszusatz, sondern Bestandteil des Entwicklungsprozesses nach BuildBySpec.

#### 2.18.1 Entwicklungsprozess

Änderungen an BuildByBricks erfolgen über nachvollziehbare Workorders.

Eine Workorder muss so beschrieben sein, dass Umsetzung, Test, Review und Dokumentation prüfbar bleiben. Änderungen ohne nachvollziehbaren fachlichen oder architektonischen Bezug sollen vermieden werden.

Für jede relevante Änderung gilt:

- fachlicher Zweck ist beschrieben,
- betroffene Bricks oder Core-Komponenten sind benannt,
- Architekturauswirkungen sind berücksichtigt,
- Tests sind definiert oder angepasst,
- Sicherheitsaspekte sind geprüft,
- Dokumentation wird bei Bedarf aktualisiert,
- Migrationen sind nachvollziehbar,
- Breaking Changes werden ausdrücklich benannt.

#### 2.18.2 Versionsverwaltung

GitHub ist das zentrale System für Quellcode, Pull Requests, Issues, Workorders und technische Nachvollziehbarkeit.

Für die Entwicklung gelten folgende Regeln:

- Änderungen erfolgen über Branches.
- Direkte Änderungen am Hauptbranch sind zu vermeiden.
- Pull Requests müssen prüfbar und fachlich abgegrenzt sein.
- Commits sollen nachvollziehbar benannt werden.
- Architekturentscheidungen werden als ADRs dokumentiert.
- Größere Änderungen müssen auf Workorders zurückführbar sein.

#### 2.18.3 CI-Prüfungen

BuildByBricks benötigt eine automatisierte CI-Pipeline.

Die CI-Pipeline muss mindestens folgende Prüfungen unterstützen:

- Installation der Abhängigkeiten,
- statische Codeanalyse,
- Formatierungsprüfung,
- Typprüfung,
- Komplexitätsprüfung,
- Unit Tests,
- Integrationstests,
- Migrationsprüfung,
- Testabdeckung,
- Security Checks,
- Prüfung auf bekannte verwundbare Abhängigkeiten.

Eine Änderung darf nicht allein aufgrund manueller Einschätzung akzeptiert werden. Automatisierte Prüfungen sind verbindlicher Bestandteil der Qualitätssicherung.

#### 2.18.4 Security Checks

Sicherheitsprüfungen sind verbindlicher Bestandteil der BuildByBricks-Qualitätssicherung.

Security Checks sind keine optionale Ergänzung und keine Kann-Bestimmung. Jede relevante Änderung muss automatisiert auf Sicherheitsrisiken geprüft werden. Die Prüfungen müssen lokal ausführbar und Bestandteil der CI-Pipeline sein.

Mindestens folgende Sicherheitsprüfungen sind verpflichtend:

- Prüfung auf bekannte Schwachstellen in Python-Abhängigkeiten,
- Prüfung auf unsichere oder veraltete Paketversionen,
- statische Python-Security-Analyse,
- Prüfung auf versehentlich eingecheckte Secrets,
- Django Deployment Checks,
- Prüfung sicherheitsrelevanter Django-Konfiguration,
- Prüfung auf kritische Abhängigkeitsupdates,
- Prüfung sicherheitsrelevanter Codepfade bei Uploads, Formularen, Authentifizierung und Berechtigungen.

Für BuildByBricks werden folgende Prüfwerkzeuge verbindlich eingesetzt:

- `pip-audit` für Dependency Vulnerability Scanning,
- `bandit` für statische Python-Security-Analyse,
- `detect-secrets` für Secret Scanning,
- Django Deployment Checks für produktionsrelevante Sicherheitseinstellungen,
- GitHub Dependabot für Abhängigkeitswarnungen und Update-Hinweise,
- GitHub CodeQL für statische Code- und Security-Analyse.

Diese Werkzeuge sind Mindeststandard. Sie dürfen durch weitere Werkzeuge ergänzt, aber nicht ersatzlos weggelassen werden.

Eine Ausnahme von einem verpflichtenden Security Check ist nur zulässig, wenn sie ausdrücklich dokumentiert, fachlich begründet und durch eine Architekturentscheidung oder Security-Entscheidung freigegeben wurde.

Geprüft werden insbesondere:

- bekannte Schwachstellen in Abhängigkeiten,
- unsichere Paketversionen,
- fehlerhafte Django-Sicherheitseinstellungen,
- versehentlich eingecheckte Secrets,
- unsichere Datei-Uploads,
- CSRF-relevante Änderungen,
- Rechte- und Rollenzugriffe,
- Zugriff auf projektspezifische Daten,
- potenziell gefährliche Template- oder Form-Verarbeitung,
- Authentifizierungs- und Autorisierungslogik,
- sicherheitsrelevante Konfigurationsänderungen.

Eine Änderung darf nicht akzeptiert werden, wenn verpflichtende Security Checks fehlschlagen oder nicht ausgeführt wurden.

Security Checks sind Teil der Definition of Done.

#### 2.18.5 Secrets und Konfiguration

Secrets dürfen nicht im Repository gespeichert werden.

Dazu gehören insbesondere:

- Datenbankpasswörter,
- Django Secret Key,
- API Keys,
- Mail-Zugangsdaten,
- OAuth- oder Token-Werte,
- Zugangsdaten zu externen Diensten,
- produktive Konfigurationsdateien.

BuildByBricks verwendet dafür:

- `.env.example` als dokumentierte Vorlage,
- lokale `.env`-Dateien für Entwicklung,
- Umgebungsvariablen im Betrieb,
- Secret-Verwaltung der jeweiligen Deployment-Umgebung.

Die Datei `.env` darf nicht versioniert werden.

#### 2.18.6 Build und Artefakte

Builds müssen reproduzierbar sein.

Die Anwendung soll über dokumentierte Befehle lokal gestartet, getestet und gebaut werden können.

Dafür sind vorgesehen:

- Makefile als zentraler Einstiegspunkt,
- Dockerfile,
- docker-compose.yml,
- pyproject.toml,
- requirements- oder lockbasierte Dependency-Verwaltung,
- dokumentierte Migrationsschritte,
- dokumentierte Static-Files-Erzeugung,
- klare Trennung zwischen Development-, Test- und Production-Konfiguration.

Ein Entwickler oder eine CI-Pipeline soll dieselben Prüfungen ausführen können.

#### 2.18.7 Deployment

BuildByBricks wird Docker-first entwickelt und ausgeliefert.

Für Deployment und Betrieb gelten folgende Grundsätze:

- produktive Konfiguration getrennt von Entwicklungskonfiguration,
- Debug-Modus in Produktion deaktiviert,
- sichere Allowed-Hosts-Konfiguration,
- HTTPS im produktiven Betrieb,
- sichere Cookie-Einstellungen,
- CSRF-Schutz aktiviert,
- statische Dateien kontrolliert ausgeliefert,
- Datenbankmigrationen nachvollziehbar angewendet,
- Rollback-Strategie für fehlerhafte Deployments,
- Backups für produktive Daten.

Produktive Deployments müssen so dokumentiert sein, dass sie reproduzierbar und überprüfbar bleiben.

#### 2.18.8 Datenbankmigrationen

Datenbankmigrationen sind Teil des Entwicklungs- und Deploymentprozesses.

Für Migrationen gilt:

- Migrationen müssen im Repository versioniert werden.
- Migrationen dürfen nicht manuell an der Datenbank vorbei erfolgen.
- Datenmigrationen müssen besonders dokumentiert und getestet werden.
- Breaking Changes an Datenmodellen müssen in Workorders benannt werden.
- Migrationskonflikte müssen bewusst aufgelöst werden.
- Produktive Migrationen müssen rollback-fähig oder zumindest risikobewertet sein.

#### 2.18.9 Logging und Monitoring

BuildByBricks benötigt von Beginn an eine saubere Logging-Strategie.

Logging muss unterstützen:

- Fehleranalyse,
- Sicherheitsereignisse,
- fehlgeschlagene Logins,
- kritische Workflow-Aktionen,
- unerwartete Exceptions,
- Import-/Exportfehler,
- Hintergrundjobs,
- Deployment- und Migrationsprobleme.

Logs dürfen keine Secrets, Passwörter oder unnötig personenbezogene Daten enthalten.

Monitoring kann zunächst einfach gehalten werden, muss aber später für produktive Installationen ausbaubar sein.

#### 2.18.10 Abhängigkeiten und Updates

Abhängigkeiten müssen aktiv gepflegt werden.

Für externe Pakete gilt:

- nur notwendige Abhängigkeiten verwenden,
- keine unklaren oder schlecht gepflegten Pakete ohne Begründung,
- regelmäßige Prüfung auf Sicherheitsupdates,
- dokumentierte Entscheidung bei kritischen Kernabhängigkeiten,
- keine Abhängigkeiten, die zentrale Architekturprinzipien unterlaufen.

Neue externe Abhängigkeiten sollen bewusst entschieden und bei relevanter Bedeutung als ADR dokumentiert werden.

#### 2.18.11 Open-Source-Sicherheit

Da BuildByBricks Open Source ist, müssen Sicherheitsaspekte besonders sorgfältig behandelt werden.

Das Projekt benötigt perspektivisch:

- klare Security Policy,
- definierte Meldewege für Schwachstellen,
- verantwortlichen Umgang mit Security Issues,
- dokumentierte Mindestanforderungen für produktiven Betrieb,
- keine Beispielkonfigurationen mit unsicheren Defaults,
- klare Hinweise zu Secrets und Deployment.

#### 2.18.12 Codex- und KI-gestützte Entwicklung

Da BuildByBricks mit Codex-gestützten Workorders entwickelt wird, gelten zusätzliche Qualitätsanforderungen.

KI-gestützte Änderungen müssen:

- klein genug für Review bleiben,
- durch Tests abgesichert sein,
- Coding Standard und Architekturregeln einhalten,
- Komplexitätsgrenzen beachten,
- keine versteckten Abhängigkeiten einführen,
- keine Sicherheitsmechanismen umgehen,
- keine Secrets erzeugen oder einchecken,
- Dokumentation bei Architektur- oder Verhaltensänderungen aktualisieren.

Codex darf keine Architekturentscheidungen implizit treffen. Architekturentscheidungen müssen explizit in Workorders, Architektur-Sheets oder ADRs dokumentiert werden.

Codex und vergleichbare KI-Werkzeuge werden nicht als Ersatz für Engineering-Reflexion verstanden. Sie können komplexe Zusammenhänge nicht zuverlässig selbständig bewerten, neigen zu Overengineering und setzen komplexe Aufgaben teilweise nur in Ausschnitten um. Diese Schwächen müssen durch präzise Spezifikation, kleine Workorders, verbindliche Tests, Review-Fragen, Komplexitätsprüfungen und Evidence-Nachweise kompensiert werden.

#### 2.18.13 Mindestdefinition von Done

Eine Änderung gilt nur dann als fertig, wenn sie die DevSecOps-Mindestanforderungen erfüllt.

Dazu gehören:

- fachliche Anforderung umgesetzt,
- Architekturregeln eingehalten,
- Tests ergänzt oder angepasst,
- Testlauf erfolgreich,
- Linting erfolgreich,
- Formatierung erfolgreich,
- Typprüfung berücksichtigt,
- Komplexitätsprüfung bestanden,
- verpflichtende Security Checks erfolgreich ausgeführt,
- `pip-audit` ohne kritische ungeklärte Findings,
- `bandit` ohne ungeklärte sicherheitsrelevante Findings,
- `detect-secrets` ohne ungeklärte Secret-Funde,
- Django Deployment Checks für produktionsnahe Konfiguration geprüft,
- GitHub Dependabot aktiviert,
- GitHub CodeQL aktiviert,
- sicherheitsrelevante Ausnahmen dokumentiert und freigegeben,
- Migrationen geprüft,
- Dokumentation aktualisiert,
- keine Secrets im Repository,
- keine bekannten kritischen Schwachstellen eingeführt.

DevSecOps ist damit Teil der Definition of Done.

#### 2.18.14 FIX-Workorders als verbindliche Änderungsform

Korrekturen, Nacharbeiten und Änderungen an bestehenden Funktionen erfolgen über eigene FIX-Workorders.

FIX-Workorders sind strenger zu formulieren als neue Feature-Workorders, weil bei Änderungen bestehender Logik mehr impliziter Kontext und mehr Regressionsrisiko besteht.

Eine FIX-Workorder muss mindestens beschreiben:

- betroffener Bereich, zum Beispiel Backend, Frontend, Datenmodell, Migration, Service, View, Template, Form, API, Tests oder Dokumentation,
- betroffene Dateien, Module, Klassen, Templates oder erwarteter Suchbereich,
- aktuelles Ist-Verhalten,
- erwartetes Soll-Verhalten,
- fachlicher Grund der Änderung,
- In-Scope der Änderung,
- explizite Nicht-Ziele und Out-of-Scope-Grenzen,
- technische Vorgaben,
- Akzeptanzkriterien,
- Testvorgaben,
- erwarteter Evidence-Nachweis.

Der Grundsatz lautet:

> Eine FIX-Workorder ist keine Feature-Idee, sondern eine präzise Reparaturanweisung.

Die KI soll bei FIX-Workorders nicht interpretieren, sondern ausführen. Architektur- oder Scope-Erweiterungen ohne ausdrückliche Freigabe sind nicht zulässig.

### 2.19 Sicherheit und Berechtigungen

Sicherheit ist eine übergreifende Randbedingung.

BuildByBricks muss von Anfang an berücksichtigen:

- Benutzerkonten,
- Rollen,
- Berechtigungen,
- Zugriff auf Projekte,
- Zugriff auf Bricks,
- Zugriff auf Dashboard-Elemente,
- Schutz vor unberechtigter Datenanzeige,
- sichere Formularverarbeitung,
- sichere Uploads,
- CSRF-Schutz,
- sichere Standardkonfigurationen.

Berechtigungen dürfen nicht nur in Templates versteckt werden. Fachliche Zugriffsbeschränkungen müssen serverseitig durchgesetzt und getestet werden.

### 2.20 Internationalisierung

BuildByBricks soll grundsätzlich so gebaut werden, dass Internationalisierung möglich bleibt.

Die erste Umsetzung kann deutschsprachig starten. Dennoch sollen Texte, Labels und fachliche Begriffe so strukturiert werden, dass eine spätere englische Version realistisch bleibt.

Dies betrifft insbesondere:

- UI-Texte,
- Dashboard-Kacheln,
- Statuswerte,
- Fehlermeldungen,
- Hilfetexte,
- Dokumentation.

### 2.21 Architekturentscheidungen

Wichtige Architekturentscheidungen werden als ADRs dokumentiert.

Bereits gesetzt:

- ADR-001: Django/Python statt PHP

Vorgesehene weitere ADRs:

- ADR-002: BuildByBricks ist ein Workflow-Sitebuilder, kein Codegenerator
- ADR-003: Bricks sind fachliche Standardbausteine, keine Plugins
- ADR-004: Dashboard als Workflow-Repräsentation
- ADR-005: Klassenbasierte Django-Bausteine
- ADR-006: Docker-first
- ADR-007: PostgreSQL als bevorzugte Datenbank
- ADR-008: Coding Standard und Toolchain
- ADR-009: Testarchitektur als verbindliche Qualitätsgrundlage
- ADR-010: Umgang mit dynamischen Strukturen in Spezial-Bricks
- ADR-011: DevSecOps als verbindliche Entwicklungs- und Betriebsrandbedingung
- ADR-012: CI-Pipeline mit Linting, Tests, Security Checks und Komplexitätsprüfung
- ADR-013: Umgang mit Secrets und produktiver Konfiguration
- ADR-014: Specification-driven Development als Delivery Model
- ADR-015: FIX-Workorders als verbindlicher Änderungsstandard

### 2.22 Zusammenfassung

Die wichtigsten Randbedingungen für BuildByBricks sind:

- Django/Python ist gesetzt.
- BuildByBricks ist kein Codegenerator.
- BuildByBricks ist kein Plugin-System.
- BuildByBricks ist ein workflowbasierter Sitebuilder aus fertigen Bricks.
- Neue Bricks werden nach BuildBySpec entwickelt.
- Jeder Brick benötigt Architektur-Sheet, BPMN, Flussdiagramme, Objektdiagramme und Testarchitektur-Konformität.
- Zentrale Architekturbausteine werden klassenbasiert umgesetzt.
- Function-Based Views werden nicht verwendet.
- Das Dashboard repräsentiert den aktiven Workflow.
- Nutzer konfigurieren vorhandene Bricks und Workflows.
- Dynamische Strukturen sind nur als kontrollierte Ausnahme innerhalb spezifischer Bricks erlaubt.
- Code-Komplexität wird automatisiert geprüft und ist eine verbindliche Qualitätsrandbedingung.
- DevSecOps ist verbindlicher Bestandteil von Entwicklung, Qualitätssicherung, Deployment und Betrieb.
- Security Checks sind verpflichtend und keine Kann-Bestimmung.
- Qualität, Tests, Sicherheit und Dokumentation sind verbindliche Bestandteile der Architektur.
- BuildByBricks wird spezifikationsgetrieben nach BuildBySpec entwickelt.
- KI-gestützte Werkzeuge werden als Architektur- und Ticketcompiler genutzt, nicht als autonome Softwarearchitekten.
- Workorders müssen Kontext, Scope, Nicht-Ziele, Akzeptanzkriterien und Testvorgaben explizit machen.
- FIX-Workorders sind als eigener, präziser Änderungsstandard verbindlich.
