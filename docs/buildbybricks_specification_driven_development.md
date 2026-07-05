# BuildByBricks – Specification-driven Development und KI-gestützter Entwicklungsprozess

## 1. Zweck dieses Dokuments

Dieses Dokument beschreibt die grundlegende Erkenntnis hinter dem BuildBySpec-Ansatz für BuildByBricks:

> Spezifikationsgetriebene Softwareentwicklung bedeutet, dass Code nicht mehr der primäre Entwicklungsgegenstand ist.  
> Der primäre Entwicklungsgegenstand ist die präzise beschriebene fachliche, architektonische und qualitätssichernde Absicht.

BuildByBricks wird nicht durch spontane KI-Codegenerierung gebaut. BuildByBricks wird durch einen kontrollierten Spezifikationsprozess hergestellt.

KI-gestützte Entwicklungswerkzeuge wie Codex werden dabei als Architektur- und Ticketcompiler verstanden. Sie übersetzen strukturierte Spezifikationen, Architekturvorgaben, Workorders und Testanforderungen in Code und technische Artefakte.

## 2. Historische Einordnung

Ein Ziel von Programmiersprachen war immer, Software für Menschen verständlicher beschreibbar zu machen.

Maschinencode war für Maschinen direkt ausführbar, für Menschen aber schwer verständlich. Höhere Programmiersprachen haben diese Lücke reduziert. Sie wurden lesbarer, strukturierter und näher an menschlichen Denkmodellen, blieben aber dennoch formale technische Sprachen.

Mit KI-gestützter Entwicklung verschiebt sich diese Grenze erneut.

Nicht mehr nur Programmiersprachen werden ausführbar, sondern strukturierte menschliche Sprache wird zu einem steuernden Entwicklungsartefakt.

Das bedeutet:

- Anforderungen können präzise formuliert werden.
- Architekturentscheidungen können explizit dokumentiert werden.
- Workorders können konkrete Umsetzungsschritte beschreiben.
- Akzeptanzkriterien können prüfbar gemacht werden.
- Tests und Evidence können verbindlicher Bestandteil der Umsetzung werden.

Die KI übernimmt dabei nicht die fachliche Wahrheit. Sie übernimmt die Übersetzung gut beschriebener Absicht in Code.

## 3. Zentrale Definition

Specification-driven Development bedeutet im BuildByBricks-Kontext:

> Software entsteht aus versionierten, prüfbaren und nachvollziehbaren Spezifikationen.  
> Code ist das Ergebnis dieses Spezifikationsprozesses.

Die zentrale Prozesskette lautet:

```text
Spezifikation
→ Architektur
→ Workorder
→ Umsetzung
→ Tests
→ Evidence
→ Living Documentation
```

Oder in Kurzform:

```text
Spezifikation → Architektur → Workorder → Code → Tests → Evidence
```

## 4. KI als Architektur- und Ticketcompiler

KI wird im BuildBySpec-Prozess nicht als autonomer Softwarearchitekt betrachtet.

Die richtige Rolle lautet:

> KI ist ein Architektur- und Ticketcompiler.

Das bedeutet:

- Die KI erhält strukturierte Eingaben.
- Die KI setzt abgegrenzte Workorders um.
- Die KI erzeugt oder verändert Code innerhalb definierter Grenzen.
- Die KI führt Aufgaben aus, die durch Spezifikation, Architektur und Tests kontrolliert werden.
- Die KI darf keine impliziten Architekturentscheidungen treffen.
- Die KI darf keine fachlichen Lücken eigenständig schließen, wenn diese Lücken relevant für Architektur, Datenmodell, Sicherheit oder Testbarkeit sind.

Die Verantwortung bleibt beim Engineering-Prozess.

## 5. Verschiebung der Entwicklungsarbeit

Durch KI verschwindet Engineering nicht. Es verschiebt sich.

Früher lag ein großer Teil der Arbeit direkt im Schreiben, Debuggen und Refactoring von Code. Der Entwickler musste Anforderungen interpretieren, Lücken schließen, Architekturentscheidungen treffen, Seiteneffekte erkennen und Qualität absichern.

Mit KI-Unterstützung wird ein Teil der mechanischen Umsetzung beschleunigt. Dadurch werden andere Bereiche wichtiger:

- Spezifikationsqualität,
- Architekturführung,
- präzise Workorders,
- Scope-Kontrolle,
- Nicht-Ziele,
- Akzeptanzkriterien,
- Testarchitektur,
- Regressionstests,
- Evidence,
- Reviews,
- Living Documentation.

Der neue Engpass ist nicht mehr nur die Fähigkeit, Code zu schreiben. Der neue Engpass ist die Fähigkeit, Software präzise, testbar und architektonisch kontrolliert zu beschreiben.

## 6. Warum präzise Workorders notwendig sind

KI kann gut umsetzen, wenn der Zielzustand klar beschrieben ist.

KI ist jedoch unzuverlässig, wenn sie komplexe Aufgaben mit implizitem Kontext selbständig interpretieren soll.

Typische Risiken sind:

- Overengineering,
- unnötige neue Abstraktionen,
- zu große Architekturänderungen,
- Umsetzung nur offensichtlicher Teilbereiche,
- fehlende Berücksichtigung von Seiteneffekten,
- falsche Annahmen über bestehende Logik,
- Änderung nicht betroffener Komponenten,
- fehlende oder unpassende Tests,
- unvollständige Umsetzung komplexer Zusammenhänge.

Deshalb müssen Workorders die relevanten Zusammenhänge explizit machen.

Eine gute Workorder beschreibt nicht nur, was gebaut werden soll, sondern auch:

- warum es gebaut werden soll,
- wo es eingebaut werden soll,
- welche Komponenten betroffen sind,
- welche Architekturregeln gelten,
- welche Tests erwartet werden,
- was ausdrücklich nicht geändert werden darf.

## 7. Besondere Bedeutung von FIX-Workorders

FIX-Workorders sind kritischer als Feature-Workorders.

Bei neuen Features kann eine KI oft aus Zielbild, Akzeptanzkriterien und Architekturvorgaben eine brauchbare Umsetzung ableiten. Bei Änderungen an bestehender Logik ist das Risiko deutlich höher.

Eine FIX-Workorder muss deshalb besonders präzise sein.

Sie muss mindestens enthalten:

- Titel,
- betroffener Bereich,
- betroffene Dateien oder Komponenten,
- aktuelles Ist-Verhalten,
- erwartetes Soll-Verhalten,
- fachlicher Kontext,
- In-Scope,
- Out-of-Scope,
- technische Vorgaben,
- Akzeptanzkriterien,
- Testvorgaben,
- Evidence-Anforderungen,
- explizite Nicht-Ziele.

Der Grundsatz lautet:

> Eine FIX-Workorder ist keine Feature-Idee, sondern eine präzise Reparaturanweisung.

Die KI soll bei FIX-Workorders nicht interpretieren, sondern ausführen.

## 8. Bedeutung für BuildByBricks

BuildByBricks selbst ist kein Codegenerator, kein Plugin-System und kein allgemeines Low-Code-System.

BuildByBricks ist die nutzbare Workflow-Software aus fertigen, geprüften Bricks.

BuildBySpec ist der Herstellungsprozess, mit dem BuildByBricks und neue Bricks entwickelt werden.

Diese Trennung ist wesentlich:

```text
BuildByBricks = Laufzeitprodukt
BuildBySpec   = Herstellungs- und Qualitätsprozess
Codex/KI      = Umsetzungswerkzeug im Entwicklungskontext
```

Endnutzer konfigurieren Workflows und aktivieren vorhandene Bricks. Sie erzeugen keinen neuen Code.

Neue Bricks entstehen außerhalb des Laufzeitkontexts durch:

- Capability-Spezifikationen,
- Architektur-Sheets,
- BPMN-Modelle,
- Flussdiagramme,
- Objektdiagramme,
- Workorders,
- FIX-Workorders,
- Tests,
- Evidence,
- Reviews,
- Dokumentation.

## 9. Bedeutung für arc42

Die Erkenntnis gehört in mehrere arc42-Kapitel:

### Kapitel 1: Einführung und Ziele

Hier wird beschrieben, dass BuildByBricks nicht nur ein Produkt ist, sondern auch ein Beispiel für spezifikationsgetriebene Softwareproduktion.

### Kapitel 2: Randbedingungen

Hier wird festgelegt, dass KI-gestützte Entwicklung nur innerhalb klarer methodischer, architektonischer und qualitätssichernder Grenzen erfolgen darf.

### Kapitel 3: Kontextabgrenzung

Hier wird klargestellt, dass KI und Codex zum Entwicklungskontext gehören, nicht zum Laufzeitkontext von BuildByBricks.

### Kapitel 8: Querschnittliche Konzepte

Hier sollte später ein eigenes Konzept für Specification-driven Development, Workorder-driven Implementation, FIX-Workorders, Evidence und Living Documentation aufgenommen werden.

### Kapitel 9: Architekturentscheidungen

Hier sollte ein ADR festhalten, dass BuildByBricks nach dem BuildBySpec-Prinzip entwickelt wird und KI als Architektur- und Ticketcompiler genutzt wird.

## 10. Qualitätsprinzipien

Für BuildByBricks gelten aus dieser Erkenntnis folgende Qualitätsprinzipien:

### 10.1 Spezifikation vor Umsetzung

Keine relevante Umsetzung ohne beschriebene fachliche Absicht, Architekturbezug und Akzeptanzkriterien.

### 10.2 Architektur vor Code

KI darf nicht eigenständig Architekturentscheidungen treffen. Architekturentscheidungen gehören in Architektur-Sheets, ADRs oder Workorders.

### 10.3 Kleine, prüfbare Arbeitspakete

Workorders müssen klein genug sein, um umgesetzt, getestet und reviewed werden zu können.

### 10.4 Tests als Pflichtbestandteil

Jede Umsetzung muss durch passende Tests abgesichert werden. Grüne Tests allein reichen jedoch nicht aus, wenn die Lösung unnötig komplex oder architektonisch falsch ist.

### 10.5 Evidence als Abschluss

Eine Umsetzung ist erst abgeschlossen, wenn nachvollziehbar dokumentiert ist:

- was geändert wurde,
- welche Dateien betroffen sind,
- welche Tests ausgeführt wurden,
- welche Ergebnisse erzielt wurden,
- welche Folgearbeiten offen bleiben.

### 10.6 Keine implizite Kontextannahme

Die KI soll Kontext nicht erraten müssen. Relevanter Kontext ist Teil der Workorder.

### 10.7 Nicht-Ziele sind Pflicht

Gerade bei KI-gestützter Umsetzung sind Nicht-Ziele wichtig, um Overengineering und ungewollte Architekturänderungen zu vermeiden.

## 11. Praktischer Merksatz

> Die Intelligenz wandert nicht vollständig in die KI.  
> Sie wandert in den Entwicklungsprozess.

Oder anders formuliert:

> Code ist nicht mehr der Ursprung der Software, sondern das Ergebnis eines kontrollierten Spezifikationsprozesses.

## 12. Schlussfolgerung

Specification-driven Development ist keine Abkürzung um Engineering herum.

Es ist eine stärkere Disziplinierung von Engineering auf einer höheren Abstraktionsebene.

Für BuildByBricks bedeutet das:

- Bricks werden nicht spontan gebaut.
- Änderungen werden nicht frei interpretiert.
- KI wird nicht als autonomer Architekt eingesetzt.
- Architektur, Tests, Scope und Evidence sind verbindlich.
- FIX-Workorders erhalten einen eigenen Standard.
- Qualität entsteht aus dem Prozess, nicht aus blindem Vertrauen in generierten Code.

BuildByBricks wird damit zu einem praktischen Beispiel für kontrollierte KI-gestützte Softwareproduktion.
