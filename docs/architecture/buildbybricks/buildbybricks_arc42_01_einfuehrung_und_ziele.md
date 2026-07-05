# BuildByBricks – arc42 Kapitel 1: Einführung und Ziele

## 1. Einführung und Ziele

### 1.1 Zweck des Systems

BuildByBricks ist eine Open-Source-Software zur Erstellung workflowbasierter Standardanwendungen aus vorgefertigten fachlichen Bausteinen, den sogenannten Bricks.

Das System richtet sich an Nutzer, die wiederkehrende Aufgaben, Abläufe und Verwaltungsprozesse strukturiert in einer Software abbilden möchten, ohne dafür jedes Mal eine Individualentwicklung beginnen zu müssen. Statt beliebige Software dynamisch zu generieren, stellt BuildByBricks geprüfte, dokumentierte und getestete Standardbausteine bereit, aus denen sich konkrete Arbeitsabläufe zusammensetzen lassen.

Ein Nutzer kann beispielsweise einen Workflow für freiberufliche Tätigkeit, Unterrichtsverwaltung, Rechnungen, Verträge, Termine, Aufgaben oder steuerrelevante Übersichten konfigurieren. Die Anwendung wird dabei nicht neu programmiert, sondern aus vorhandenen, fachlich klar abgegrenzten Bricks zusammengestellt.

Der zentrale Gedanke lautet:

> Ein realer Arbeitsablauf wird als konfigurierbarer Workflow abgebildet.  
> Die dafür benötigten Funktionen werden aus fertigen, qualitätsgesicherten Bricks zusammengesetzt.

BuildByBricks ist damit kein Plugin-System, kein Low-Code-Generator und kein Codegenerator. Es ist ein workflowbasierter Sitebuilder für Standardprobleme.

### 1.2 Verhältnis zu BuildBySpec

BuildBySpec ist die Methode, nach der BuildByBricks und alle enthaltenen Bricks geplant, spezifiziert, gebaut, getestet und dokumentiert werden.

BuildByBricks selbst erzeugt keinen neuen Code. Neue Bricks entstehen nicht automatisch im System, sondern werden nach dem BuildBySpec-Prinzip entwickelt. Jeder Brick muss vor der Umsetzung fachlich, architektonisch und testseitig beschrieben sein.

BuildBySpec ist damit nicht die Laufzeitfunktion von BuildByBricks, sondern der verbindliche Herstellungs- und Qualitätsprozess hinter der Software.

### 1.2.1 Specification-driven Development als Herstellungsprinzip

BuildByBricks wird nach dem Prinzip der spezifikationsgetriebenen Softwareentwicklung erstellt.

Der primäre Entwicklungsgegenstand ist dabei nicht mehr der Quellcode selbst, sondern die präzise beschriebene fachliche, architektonische und qualitätssichernde Absicht. Code ist das Ergebnis eines kontrollierten Spezifikationsprozesses.

Die zentrale Herstellungslogik lautet:

> Spezifikation → Architektur → Workorder → Code → Tests → Evidence → Dokumentation

KI-gestützte Entwicklungswerkzeuge wie Codex werden in diesem Prozess nicht als autonome Softwarearchitekten verstanden, sondern als Architektur- und Ticketcompiler. Sie übersetzen geprüfte Spezifikationen, Architekturvorgaben und klar begrenzte Workorders in Quellcode und Tests.

Dadurch verschiebt sich der Schwerpunkt der Softwareentwicklung deutlich stärker in Richtung Engineering, Architekturführung und Qualitätssicherung. Fachliche Ziele, betroffene Komponenten, Scope-Grenzen, Nicht-Ziele, Akzeptanzkriterien und Testnachweise müssen explizit beschrieben werden.

BuildByBricks ist damit auch ein Referenzprojekt für die praktische Anwendung von BuildBySpec: Die Qualität entsteht nicht durch spontane Codegenerierung, sondern durch versionierte, prüfbare und nachvollziehbare Entwicklungsartefakte.


### 1.3 Grundidee der Bricks

Ein Brick ist ein fachlicher Standardbaustein, der ein wiederkehrendes Problem oder einen klar abgegrenzten Teil eines Workflows löst.

Beispiele für mögliche Bricks sind:

- Rechnungen
- Zahlungen
- Aufgaben
- Verträge
- Termine
- Dokumente
- Unterrichtsplanung
- Steuerübersicht
- Dashboard-Kacheln
- Kontakte
- Notizen

Ein Brick ist nicht als beliebig installierbares Plugin zu verstehen. Er ist ein geprüfter Bestandteil der Anwendung mit definierter fachlicher Verantwortung, definierten Schnittstellen, dokumentiertem Verhalten und vollständiger Testabdeckung nach der Testarchitektur.

Bricks können in Workflows kombiniert werden. Der Nutzer stellt sich daraus seine individuelle Lösung für einen konkreten Arbeitsablauf zusammen.

### 1.4 Workflow als Kern des Systems

Der Workflow ist der zentrale fachliche Anker von BuildByBricks.

Ein Workflow beschreibt, welche Aufgaben in welcher fachlichen Beziehung zueinander stehen und welche Bricks zur Bearbeitung dieser Aufgaben benötigt werden.

Ein Nutzer beginnt nicht mit einer technischen App-Struktur, sondern mit einem praktischen Arbeitsablauf:

> Ich habe bestimmte Standardaufgaben und möchte dafür eine passende Softwareoberfläche zusammenstellen.

BuildByBricks unterstützt diese Idee, indem es Bricks nicht isoliert betrachtet, sondern im Kontext eines Workflows nutzbar macht.

Ein Workflow kann beispielsweise festlegen:

- welche Bricks aktiv sind,
- welche Aufgabenbereiche sichtbar sind,
- welche Statuswerte verwendet werden,
- welche Dashboard-Kacheln angezeigt werden,
- welche Fristen und offenen Punkte relevant sind,
- welche Navigationseinträge eingeblendet werden,
- welche Daten im Arbeitsalltag im Vordergrund stehen.

### 1.5 Dashboard als Workflow-Repräsentation

Das Dashboard ist die zentrale Einstiegsebene eines BuildByBricks-Projekts.

Es ist nicht nur eine allgemeine Startseite, sondern die visuelle Repräsentation des aktuell konfigurierten Workflows. Es zeigt dem Nutzer, was in seinem konkreten Arbeitsablauf gerade relevant ist.

Das Dashboard soll daher pro Workflow konfigurierbar sein. Es kann je nach aktivierten Bricks unterschiedliche Informationen anzeigen, zum Beispiel:

- offene Rechnungen,
- offene Zahlungen,
- Termine dieser Woche,
- anstehende Aufgaben,
- fällige Verträge,
- Einnahmen des Monats,
- steuerrelevante Übersichten,
- aktuelle Projektstände,
- offene Dokumentationspunkte.

Damit wird das Dashboard zum operativen Kontrollzentrum des jeweiligen Workflows.

### 1.6 Voraussetzungen für die Entwicklung eines Bricks

Jeder Brick muss vor seiner Umsetzung nach dem BuildBySpec-Prinzip beschrieben werden.

Für jeden Brick sind mindestens folgende Artefakte erforderlich:

1. Architektur-Sheet nach arc42  
   Das Architektur-Sheet beschreibt Zweck, fachliche Abgrenzung, Schnittstellen, Datenstrukturen, Qualitätsanforderungen, Risiken und Architekturentscheidungen des Bricks.

2. BPMN-Modell(e) des fachlichen Ablaufs  
   Die fachlichen Prozesse des Bricks müssen als BPMN-Modell beschrieben werden. Dadurch wird sichtbar, welche Akteure, Zustände, Entscheidungen und Prozessschritte relevant sind.

3. Flussdiagramme  
   Ergänzend zu BPMN können technische oder fachliche Entscheidungsflüsse als Flussdiagramme beschrieben werden. Diese dienen insbesondere zur Klärung von Validierungen, Statuswechseln, Sonderfällen und Fehlerpfaden.

4. Objektdiagramm(e)  
   Die zentralen fachlichen Objekte, ihre Beziehungen und ihre Verantwortlichkeiten müssen beschrieben werden. Daraus ergeben sich später Datenmodelle, Services, Formulare, Views und Tests.

5. Testarchitektur-Konformität  
   Jeder Brick muss die übergreifende Testarchitektur von BuildByBricks einhalten. Die Testarchitektur ist verbindlich und definiert, welche Testarten, Testebenen, Testdaten, Qualitätsgrenzen und Nachweispflichten für Bricks gelten.

Ein Brick darf erst dann als Bestandteil von BuildByBricks gelten, wenn seine fachliche Spezifikation, Architektur und Testbarkeit nachvollziehbar dokumentiert sind.

### 1.7 Architekturziele

Die übergeordnete Architektur von BuildByBricks verfolgt folgende Ziele.

#### 1. Workflow-Zentrierung

BuildByBricks soll reale Arbeitsabläufe abbilden. Die technische Struktur folgt dem fachlichen Workflow, nicht umgekehrt.

#### 2. Wiederverwendbare fachliche Bausteine

Bricks sollen klar abgegrenzte Standardprobleme lösen und in verschiedenen Workflows wiederverwendbar sein.

#### 3. Konfigurierbarkeit ohne Codegenerierung

Nutzer sollen ihre eigene Lösung aus vorhandenen Bricks zusammenstellen können. Diese Konfiguration verändert den Workflow, das Dashboard, die Navigation und sichtbare Funktionsbereiche, erzeugt aber keinen neuen Code.

#### 4. Hohe Verständlichkeit

Die Architektur muss für Menschen, Entwickler und KI-gestützte Entwicklungswerkzeuge verständlich sein. Fachliche Abläufe, Datenobjekte, Abhängigkeiten und Tests müssen explizit dokumentiert werden.

#### 5. Konsequente Qualitätssicherung

Jeder Brick muss nach einem einheitlichen Qualitätsprozess entstehen. Architektur, BPMN, Diagramme, Tests und Dokumentation sind keine optionalen Ergänzungen, sondern Voraussetzung für die Aufnahme eines Bricks.

#### 6. Erweiterbarkeit durch neue Bricks

BuildByBricks soll langfristig durch weitere fachliche Bricks wachsen können. Neue Bricks müssen jedoch immer nach BuildBySpec-Prinzipien geplant, gebaut und getestet werden.

#### 7. Dashboard als Steuerungszentrale

Das Dashboard soll den jeweiligen Workflow abbilden und dem Nutzer sofort zeigen, welche Aufgaben, Fristen, Risiken oder offenen Punkte aktuell relevant sind.

#### 8. Saubere technische Struktur

Die technische Umsetzung soll modular, nachvollziehbar und wartbar bleiben. Bricks dürfen nicht durch versteckte Abhängigkeiten oder unklare Zuständigkeiten miteinander vermischt werden.

#### 9. Spezifikationsgetriebene Softwareproduktion

BuildByBricks soll nach einem kontrollierten Spezifikationsprozess entwickelt werden. Fachlichkeit, Architektur, Workorders, Tests und Evidence bilden die maßgeblichen Steuerungsartefakte. KI-gestützte Umsetzung darf nur auf Basis dieser Artefakte erfolgen und darf Architekturentscheidungen nicht implizit treffen.

#### 10. Präzise Änderungs- und FIX-Prozesse

Änderungen an bestehenden Bereichen müssen besonders genau beschrieben werden. FIX-Workorders benötigen eine klare Angabe des betroffenen Bereichs, der betroffenen Dateien oder Komponenten, des Ist-Verhaltens, des Soll-Verhaltens, der Nicht-Ziele und der erwarteten Testnachweise.

### 1.8 Nicht-Ziele

BuildByBricks verfolgt ausdrücklich nicht folgende Ziele:

- keine automatische Codegenerierung durch Endnutzer,
- kein frei installierbares Plugin-System,
- kein generisches Low-Code- oder No-Code-System,
- keine generische dynamische Erstellung beliebiger Datenmodelle zur Laufzeit,
- keine frei konfigurierbare Datenmodellierung als allgemeines Plattformprinzip,
- keine beliebige Erweiterung der Fachlogik durch Endnutzerkonfiguration,
- keine beliebige Erweiterung durch unstrukturierte Fremdmodule,
- keine Vermischung von Workflow-Konfiguration und Softwareentwicklung.

Neue Funktionalität entsteht durch Entwicklung nach BuildBySpec, nicht durch spontane Konfiguration im laufenden System.

#### Kontrollierte Ausnahme für dynamische Strukturen

Spezifische Bricks dürfen kontrollierte dynamische Strukturen verwenden, wenn dies fachlich notwendig ist, zum Beispiel für Umfragen, Fragebögen, konfigurierbare Formulare oder strukturierte Erfassungsmasken.

Diese dynamischen Strukturen sind jedoch Bestandteil eines klar abgegrenzten Bricks und müssen durch dessen Architektur-Sheet, Datenmodell, Validierungsregeln, Testfälle und Sicherheitskonzept beschrieben sein. Sie ersetzen nicht das grundsätzliche Datenmodell von BuildByBricks und machen BuildByBricks nicht zu einem allgemeinen Low-Code-Datenmodell-Builder.

### 1.9 Zielgruppen

BuildByBricks richtet sich an Nutzer, die wiederkehrende Standardaufgaben in einer strukturierten Softwarelösung abbilden möchten.

Mögliche Zielgruppen sind:

- Freelancer,
- kleine Unternehmen,
- Selbstständige,
- Dozenten,
- Berater,
- kleine Organisationen,
- interne Teams mit standardisierten Abläufen,
- Entwickler, die BuildByBricks als Open-Source-Basis erweitern möchten.

Für Endnutzer steht die Konfiguration von Workflows im Vordergrund.  
Für Entwickler steht die methodische Erstellung neuer Bricks nach BuildBySpec im Vordergrund.

### 1.10 Zusammenfassung

BuildByBricks ist eine workflowbasierte Open-Source-Anwendung aus fertigen, qualitätsgesicherten Bricks.

Die Software ermöglicht es Nutzern, eigene Arbeitsabläufe aus vorhandenen Bausteinen zusammenzustellen und über ein konfigurierbares Dashboard zu steuern.

Die Entwicklung neuer Bricks erfolgt nicht innerhalb der Anwendung, sondern nach dem BuildBySpec-Prinzip. Jeder Brick benötigt dafür eine fachliche Spezifikation, ein Architektur-Sheet, BPMN-Modelle, Flussdiagramme, Objektdiagramme und die Einhaltung der übergreifenden Testarchitektur.

Damit verbindet BuildByBricks zwei Ebenen:

- eine nutzbare Workflow-Software für Standardprobleme,
- einen klaren Entwicklungs- und Qualitätsprozess für neue fachliche Bausteine.

Der Quellcode von BuildByBricks ist dabei nicht der Ursprung der Software, sondern das Ergebnis eines kontrollierten BuildBySpec-Prozesses. KI-gestützte Entwicklungswerkzeuge dienen als Architektur- und Ticketcompiler, während Verantwortung für Fachlichkeit, Architektur, Scope, Tests und Qualität beim Engineering-Prozess bleibt.
