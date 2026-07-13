# Agentic RAG Study Template

Dieses Repository entsteht als schlanke Vorlage fuer ein agentic-RAG-System, das spaeter auf unterschiedliche Anwendungen uebertragen werden kann. Die erste Phase ist bewusst eine Studie: Wir bauen das Grundkonstrukt on-the-fly, pruefen jede Entscheidung lokal und halten die Architektur so klein, dass sie verstanden, ersetzt und erweitert werden kann.

## Ziel

Das Projekt soll eine wiederverwendbare Basis liefern fuer Anwendungen, die Dokumente oder Wissensquellen durchsuchen, relevante Informationen abrufen und mit einem Agenten kontrolliert weiterverarbeiten.

Die Vorlage soll:

- lokal startbar und testbar sein
- per Docker Container reproduzierbar laufen
- klare Austauschpunkte fuer Modelle, Vector Stores und Datenquellen haben
- einfache Evaluations- und Debugging-Moeglichkeiten bieten
- Schritt fuer Schritt zu einer produktnaeheren Architektur ausgebaut werden koennen

## Grundkonstrukt

Ein minimales agentic-RAG-System braucht folgende Bestandteile:

1. **Application Shell**

   Eine kleine API oder CLI als Einstiegspunkt. Sie nimmt eine Nutzerfrage entgegen, startet den Agentenlauf und gibt Antwort, Quellen und Debug-Informationen zurueck.

2. **Ingestion Pipeline**

   Ein Prozess, der Dokumente einliest, bereinigt, in Chunks zerlegt und fuer die Suche vorbereitet. Am Anfang reichen lokale Dateien in einem `data/`-Ordner.

3. **Embedding Layer**

   Eine austauschbare Komponente, die Textabschnitte in Vektoren umwandelt. Die Schnittstelle sollte unabhaengig vom konkreten Provider sein.

4. **Vector Store**

   Eine lokale Suchschicht fuer semantische Suche. Fuer die Studie kann eine einfache lokale Loesung genuegen; spaeter koennen Qdrant, pgvector, Weaviate oder andere Stores angeschlossen werden.

5. **Retriever**

   Eine Komponente, die aus der Nutzerfrage Suchanfragen ableitet, relevante Chunks findet und diese fuer den Agenten strukturiert bereitstellt.

6. **Agent Orchestrator**

   Der Kern des Systems. Der Agent entscheidet, ob er suchen, nachfragen, Quellen vergleichen, eine Antwort formulieren oder einen Zwischenschritt wiederholen soll.

7. **Tools**

   Klar begrenzte Werkzeuge, die der Agent verwenden darf. Fuer den Start:

   - `search_knowledge_base`
   - `read_source`
   - `summarize_context`
   - `answer_with_citations`

8. **Prompt and Policy Layer**

   Systemprompts, Antwortregeln und Sicherheitsgrenzen. Besonders wichtig: Der Agent muss kenntlich machen, wann Informationen fehlen oder Quellen nicht ausreichen.

9. **Evaluation Harness**

   Ein kleiner Satz von Testfragen mit erwarteten Eigenschaften. Nicht zwingend perfekte Musterantworten, aber pruefbare Kriterien wie Quellenabdeckung, Halluzinationsvermeidung und Antwortformat.

10. **Observability**

    Einfache Logs fuer Agentenschritte, verwendete Tools, gefundene Quellen, Tokenverbrauch und Fehler. Ohne Sichtbarkeit wird agentic RAG schnell undurchsichtig.

11. **Docker Runtime**

    Ein `Dockerfile` und optional `docker-compose.yml`, damit die Studie reproduzierbar gestartet werden kann. Lokale Entwicklung und Containerlauf sollten denselben Codepfad verwenden.

## Vorgeschlagene Reihenfolge

1. **Projekt-Skeleton anlegen**

   Ordnerstruktur, minimale Runtime, Konfiguration und ein erster Startbefehl.

2. **Lokale Docker-Ausfuehrung herstellen**

   `Dockerfile`, `.dockerignore` und ein einfacher Container-Start, der zunaechst nur eine Health-Ausgabe oder CLI-Hilfe liefert.

3. **Application Shell bauen**

   Entscheidung zwischen CLI, HTTP API oder beidem. Fuer die Studie ist eine CLI oft der schnellste Einstieg; eine kleine API kann danach folgen.

4. **Ingestion fuer lokale Dateien umsetzen**

   Textdateien einlesen, chunking definieren, Metadaten speichern und reproduzierbar erneut ausfuehren.

5. **Embedding und lokalen Vector Store anbinden**

   Erst die Schnittstellen stabilisieren, dann einen konkreten lokalen Store einsetzen.

6. **Retriever implementieren**

   Top-k-Suche, einfache Filter, Quellenmetadaten und ein nachvollziehbares Retrieval-Ergebnis.

7. **Agentischen Ablauf einfuehren**

   Der Agent bekommt Tools und entscheidet selbst, wann Retrieval noetig ist. Zunaechst mit wenigen, gut sichtbaren Schritten.

8. **Antworten mit Quellen erzeugen**

   Ausgabeformat festlegen: Antwort, Quellen, Unsicherheiten und optional Debug Trace.

9. **Evaluation hinzufuegen**

   Kleine Testkollektion mit wiederholbarem Lauf, damit Aenderungen am System vergleichbar bleiben.

10. **Template abstrahieren**

    Anwendungsspezifische Teile auslagern: Datenquellen, Prompts, Tool-Definitionen, Evaluationsfragen und Runtime-Konfiguration.

## Erste technische Annahmen

Diese Punkte sind bewusst vorlaeufig und sollen im Verlauf der Studie validiert werden:

- Python eignet sich gut fuer die erste Version, weil RAG-, Embedding- und Evaluationsbibliotheken dort schnell verfuegbar sind.
- Eine CLI ist der einfachste erste Einstiegspunkt; eine HTTP API kann danach ergaenzt werden.
- Lokale Dateien sind die erste Datenquelle.
- Der Vector Store sollte austauschbar bleiben.
- Docker ist von Anfang an Teil des Workflows, nicht erst ein spaeter Deployment-Schritt.

## Erwartete erste Ordnerstruktur

```text
.
├── README.md
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── src/
│   └── agentic_rag_template/
│       ├── app.py
│       ├── config.py
│       ├── ingestion/
│       ├── retrieval/
│       ├── agent/
│       ├── tools/
│       └── evaluation/
├── data/
│   └── sample/
└── tests/
```

## Naechster Schritt

Als naechstes sollte das Projekt-Skeleton entstehen: minimale Python-App, Dockerfile, lokaler Startbefehl und ein erster Smoke Test. Danach koennen wir die Ingestion fuer lokale Dateien bauen.
