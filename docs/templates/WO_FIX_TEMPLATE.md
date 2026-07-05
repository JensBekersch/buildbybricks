# WO_FIX_TEMPLATE.md

# Standard für FIX-Workorders

## Zweck

FIX-Workorders dienen nicht der Neuentwicklung, sondern der gezielten Korrektur, Anpassung oder Nachschärfung bestehender Funktionalität.

Eine FIX-Workorder muss so präzise formuliert sein, dass die ausführende KI nicht raten muss, wo der Fehler liegt, welche Komponente betroffen ist oder wie weit die Änderung gehen darf.

## Grundregel

Eine FIX-Workorder beschreibt immer:

1. **Was ist aktuell falsch?**
2. **Wo genau tritt es auf?**
3. **Welche Komponente ist betroffen?**
4. **Was soll stattdessen passieren?**
5. **Was darf ausdrücklich nicht geändert werden?**
6. **Wie wird nachgewiesen, dass der Fix korrekt ist?**

---

## Pflichtstruktur einer FIX-Workorder

### 1. Titel

Kurzer, eindeutiger Titel.

**Beispiel:**

```text
FIX-012: Segmentanalyse verwendet falschen Analysewert für Bucket-Auswertung
```

---

### 2. Betroffener Bereich

Explizit angeben, welcher technische Bereich betroffen ist.

**Mögliche Kategorien:**

- Backend
- Frontend
- Datenmodell
- Migration
- Service-Logik
- View / ViewModel
- Template
- Form
- API
- Tests
- Dokumentation
- BPMN / Workflow
- Export / PDF / CSV
- Validierung
- UI-Text / UX

**Beispiel:**

```text
Betroffener Bereich: Backend-Service, Form-Validierung, Ergebnis-Template
```

---

### 3. Betroffene Dateien / Komponenten

So konkret wie möglich angeben.

**Beispiel:**

```text
Betroffene Dateien / Komponenten:

- research/services/segment_analysis_service.py
- research/forms/segment_analysis_form.py
- research/templates/research/segment_analysis_result.html
- tests/research/test_segment_analysis_service.py
```

Falls die Datei noch nicht sicher bekannt ist:

```text
Die konkrete Datei ist vor Umsetzung zu identifizieren.
Erwarteter Bereich: research/services/*segment*
```

---

### 4. Ist-Verhalten

Beschreiben, was aktuell passiert.

**Beispiel:**

```text
Aktuell geht die Segmentanalyse implizit davon aus, dass der Surprise-Wert immer das zentrale Analysefeld ist.
Dadurch wird die Auswertung falsch, sobald ein anderer Analysewert wie KI-Sentiment oder Rating-Kategorie verwendet werden soll.
```

---

### 5. Soll-Verhalten

Beschreiben, was nach dem Fix passieren soll.

**Beispiel:**

```text
Die Segmentanalyse muss ein explizit ausgewähltes Analysefeld verwenden.
Dieses Feld kann numerisch oder kategorisch sein.
Die Bucket-Auswertung darf nicht mehr fest an Surprise-Werte gekoppelt sein.
```

---

### 6. Fachlicher Kontext

Kurz erklären, warum der Fix nötig ist.

**Beispiel:**

```text
Der Analyseprozess soll nicht nur Wirtschaftsdaten mit Ist-Prognose-Abweichung auswerten,
sondern auch andere klar definierte Analysewerte, etwa KI-gestützte Sentiment-Kategorien aus Geschäftsberichten.
```

---

### 7. Scope der Änderung

Genau abgrenzen, was geändert werden soll.

**In Scope:**

- [ ] Auswahl eines Analysefeldes ermöglichen
- [ ] Bucket-Logik auf ausgewähltes Feld anwenden
- [ ] Ergebnisdarstellung entsprechend beschriften
- [ ] Bestehende Tests anpassen oder ergänzen

**Out of Scope:**

- [ ] Keine neue Strategie-Engine bauen
- [ ] Keine neue Importstrecke entwickeln
- [ ] Keine Änderung am gesamten Datenmodell, sofern nicht zwingend nötig
- [ ] Keine optische Neugestaltung der Seite
- [ ] Keine Änderung an bestehenden Eventtypen außerhalb der betroffenen Analyse

---

### 8. Technische Vorgaben

Konkrete technische Leitplanken.

**Beispiel:**

```text
- Bestehende Architektur beibehalten
- Keine DTOs einführen
- Service-Logik nicht in Templates verschieben
- Django Forms für Validierung verwenden
- Bestehende Tests dürfen nicht entfernt werden
- Neue Tests müssen deterministisch sein
```

---

### 9. Akzeptanzkriterien

Als prüfbare Kriterien formulieren.

**Beispiel:**

```text
- Wenn ein numerisches Analysefeld gewählt wird, werden Buckets korrekt auf Basis dieses Feldes gebildet.
- Wenn ein kategorisches Analysefeld gewählt wird, werden die definierten Kategorien korrekt gruppiert.
- Die Ergebnisansicht zeigt eindeutig, welches Analysefeld verwendet wurde.
- Bestehende Surprise-Analysen funktionieren weiterhin.
- Ungültige oder fehlende Analysefelder werden validiert und führen zu einer verständlichen Fehlermeldung.
- Alle bestehenden Tests bleiben grün.
```

---

### 10. Testvorgaben

Explizit angeben, welche Tests erwartet werden.

**Beispiel:**

```text
- Unit-Test für numerische Bucket-Auswertung
- Unit-Test für kategorische Bucket-Auswertung
- Regressionstest für bestehende Surprise-Auswertung
- Form-Test für fehlendes Analysefeld
- Template-Test oder View-Test für korrekte Anzeige des gewählten Analysefeldes
```

---

### 11. Nachweis / Evidence

Beschreiben, was Codex oder die ausführende KI am Ende liefern soll.

**Beispiel:**

```text
- Liste der geänderten Dateien
- Kurze Erklärung der Änderung
- Testergebnis
- Hinweis auf mögliche Folgearbeiten
- Keine ungefragten Zusatzfeatures
```

---

### 12. Explizite Nicht-Ziele

Dieser Abschnitt ist bei FIX-Workorders besonders wichtig.

**Beispiel:**

```text
Diese Workorder soll ausschließlich die Auswahl und Verwendung des Analysefeldes in der bestehenden Segmentanalyse korrigieren.
Es sollen keine neuen Analysearten, keine neue UI-Struktur und keine neue Strategieentscheidung implementiert werden.
```

---

## Merksatz

Eine FIX-Workorder ist keine Feature-Idee, sondern eine präzise Reparaturanweisung.

Die KI soll nicht interpretieren, sondern ausführen.

---

# Leere Vorlage zum Ausfüllen

## Titel

```text
FIX-XXX:
```

---

## Betroffener Bereich

```text
Betroffener Bereich:
```

---

## Betroffene Dateien / Komponenten

```text
Betroffene Dateien / Komponenten:

-
-
-
```

---

## Ist-Verhalten

```text
Aktuell:
```

---

## Soll-Verhalten

```text
Nach dem Fix:
```

---

## Fachlicher Kontext

```text
Warum ist dieser Fix nötig?
```

---

## Scope der Änderung

### In Scope

- [ ]
- [ ]
- [ ]

### Out of Scope

- [ ]
- [ ]
- [ ]

---

## Technische Vorgaben

```text
-
-
-
```

---

## Akzeptanzkriterien

- [ ]
- [ ]
- [ ]

---

## Testvorgaben

- [ ]
- [ ]
- [ ]

---

## Nachweis / Evidence

Die ausführende KI / Codex soll nach Umsetzung liefern:

- [ ] Liste der geänderten Dateien
- [ ] Kurze Erklärung der Änderung
- [ ] Testergebnis
- [ ] Hinweis auf mögliche Folgearbeiten
- [ ] Bestätigung, dass keine ungefragten Zusatzfeatures umgesetzt wurden

---

## Explizite Nicht-Ziele

```text
Diese Workorder soll nicht:
-
-
-
```
