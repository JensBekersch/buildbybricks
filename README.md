# Agentic RAG Study Template

Dieses Repository entsteht als schlanke Vorlage fuer ein agentic-RAG-System, das spaeter auf unterschiedliche Anwendungen uebertragen werden kann. Die erste Phase ist bewusst eine Studie: Wir bauen das Grundkonstrukt on-the-fly, pruefen jede Entscheidung lokal und halten die Architektur so klein, dass sie verstanden, ersetzt und erweitert werden kann.

## Ziel

Das Projekt soll eine wiederverwendbare Basis liefern fuer Anwendungen, die Dokumente oder Wissensquellen durchsuchen, relevante Informationen abrufen und mit einem Agenten kontrolliert weiterverarbeiten.

Die produktive Zielrichtung ist eine mehragentenfaehige Softwarefabrik fuer
Django-Applikationen. Sie soll aus fachlichen Beschreibungen zunaechst
Architektur-Sheets erzeugen, diese spaeter in Workorders herunterbrechen, die
Workorders ausfuehren, Tests erzeugen und Aenderungen nach GitHub committen
koennen.

Die Vorlage soll:

- lokal startbar und testbar sein
- per Docker Container reproduzierbar laufen
- eine kleine API mit HTML-Chat-Frontend bereitstellen
- klare Austauschpunkte fuer Modelle, Vector Stores und Datenquellen haben
- einfache Evaluations- und Debugging-Moeglichkeiten bieten
- Schritt fuer Schritt zu einer produktnaeheren Architektur ausgebaut werden koennen

## Software Factory Direction

Die erste konkrete Produktinstanz ist `software-factory`. Sie fokussiert sich
zunaechst auf Django-Applikationen und bildet den Anfang einer Softwarefabrik:

1. Beschreibung eines Softwareartefakts aufnehmen.
2. Daraus ein strukturiertes Architecture Sheet nach arc42-orientierten
   Abschnitten erzeugen.
3. Offene Fragen, Annahmen, Risiken und Qualitaetsziele explizit machen.
4. Das Sheet spaeter als Input fuer Workorders, Implementierung, Tests und
   GitHub-Aenderungen verwenden.

Der erste Contract liegt unter:

- `apps/software-factory/architecture_sheet.schema.json`
- `apps/software-factory/app_profile.json`
- `data/software-factory/architecture-method/arc42_architecture_sheet.md`

Das Architecture Sheet ist bewusst ein maschinenlesbares Zwischenformat. Es ist
kein vollstaendiges arc42-Dokument, sondern der spaetere Uebergabepunkt zwischen
Architektur-Agent, Workorder-Agenten und Implementierungs-Agenten.

## Grundkonstrukt

Ein minimales agentic-RAG-System braucht folgende Bestandteile:

1. **Application Shell**

   Eine kleine HTTP API als Einstiegspunkt. Sie nimmt Chat-Nachrichten entgegen, startet den Agentenlauf und gibt Antwort, Quellen und Debug-Informationen strukturiert zurueck.

2. **HTML Chat Frontend**

   Ein bewusst einfaches, statisches Frontend fuer lokale Tests. Es zeigt den Chatverlauf, sendet Fragen an die API und macht Quellen, Unsicherheiten und optionale Agentenschritte sichtbar.

3. **Ingestion Pipeline**

   Ein Prozess, der Dokumente einliest, bereinigt, in Chunks zerlegt und fuer die Suche vorbereitet. Am Anfang reichen lokale Dateien in einem `data/`-Ordner.

4. **Embedding Layer**

   Eine austauschbare Komponente, die Textabschnitte in Vektoren umwandelt. Die Schnittstelle sollte unabhaengig vom konkreten Provider sein.

5. **Vector Store**

   Eine lokale Suchschicht fuer semantische Suche. Fuer die Studie kann eine einfache lokale Loesung genuegen; spaeter koennen Qdrant, pgvector, Weaviate oder andere Stores angeschlossen werden.

6. **Retriever**

   Eine Komponente, die aus der Nutzerfrage Suchanfragen ableitet, relevante Chunks findet und diese fuer den Agenten strukturiert bereitstellt.

7. **Agent Orchestrator**

   Der Kern des Systems. Der Agent entscheidet, ob er suchen, nachfragen, Quellen vergleichen, eine Antwort formulieren oder einen Zwischenschritt wiederholen soll.

8. **Tools**

   Klar begrenzte Werkzeuge, die der Agent verwenden darf. Fuer den Start:

   - `search_knowledge_base`
   - `read_source`
   - `summarize_context`
   - `answer_with_citations`

9. **Prompt and Policy Layer**

   Systemprompts, Antwortregeln und Sicherheitsgrenzen. Besonders wichtig: Der Agent muss kenntlich machen, wann Informationen fehlen oder Quellen nicht ausreichen.

10. **Evaluation Harness**

   Ein kleiner Satz von Testfragen mit erwarteten Eigenschaften. Nicht zwingend perfekte Musterantworten, aber pruefbare Kriterien wie Quellenabdeckung, Halluzinationsvermeidung und Antwortformat.

11. **Observability**

    Einfache Logs fuer Agentenschritte, verwendete Tools, gefundene Quellen, Tokenverbrauch und Fehler. Ohne Sichtbarkeit wird agentic RAG schnell undurchsichtig.

12. **Docker Runtime**

    Ein `Dockerfile` und optional `docker-compose.yml`, damit die API und das HTML-Frontend reproduzierbar gestartet werden koennen. Lokale Entwicklung und Containerlauf sollten denselben Codepfad verwenden.

## Vorgeschlagene Reihenfolge

1. **Projekt-Skeleton anlegen**

   Ordnerstruktur, minimale Runtime, Konfiguration, API-Modul und Frontend-Ordner.

2. **Minimale API bauen**

   Ein erster HTTP Server mit `GET /health` und `POST /chat`. Der Chat-Endpunkt darf zu Beginn noch eine statische Antwort liefern.

3. **HTML Chat Frontend bauen**

   Eine einfache Seite mit Chatverlauf, Eingabefeld, Senden-Button und Anzeige fuer Quellen oder Debug Trace. Das Frontend spricht direkt mit `POST /chat`.

4. **Lokale Docker-Ausfuehrung herstellen**

   `Dockerfile`, `.dockerignore` und ein Container-Start, der API und Frontend gemeinsam verfuegbar macht.

5. **Ingestion fuer lokale Dateien umsetzen**

   Textdateien einlesen, chunking definieren, Metadaten speichern und reproduzierbar erneut ausfuehren.

6. **Embedding und lokalen Vector Store anbinden**

   Erst die Schnittstellen stabilisieren, dann einen konkreten lokalen Store einsetzen. Die Default-Implementierung ist ein deterministischer Hash-Embedder, damit Tests und Docker ohne externe Dienste laufen. Spaeter koennen Provider wie Ollama oder OpenAI ueber dieselbe Schnittstelle angebunden werden.

7. **Retriever implementieren**

   Top-k-Suche, einfache Collection-Filter, Quellenmetadaten, Trace-Informationen und ein nachvollziehbares Ergebnisformat. Der Retriever ist die Fassade, die der Agent spaeter als Such-Tool verwenden soll.

8. **Agentischen Ablauf einfuehren**

   Der Agent bekommt Tools und entscheidet selbst, wann Retrieval noetig ist. Zunaechst mit wenigen, gut sichtbaren Schritten. Der erste deterministische Agent nutzt `search_knowledge_base`, `read_source` und `answer_with_citations`.

9. **Antworten mit Quellen erzeugen**

   Ausgabeformat fuer API und Frontend festlegen: Antwort, Quellen, Unsicherheiten und optional Debug Trace. Quellen enthalten Titel, Pfad, Ausschnitt und Score; die Antwort nennt Unsicherheiten explizit.

10. **Evaluation hinzufuegen**

   Kleine Testkollektion mit wiederholbarem Lauf, damit Aenderungen am System vergleichbar bleiben. Die Evaluation prueft beobachtbare Kriterien wie Quellenabdeckung, Antwortformat, Unsicherheit und Tool-Nutzung.

11. **Template abstrahieren**

    Anwendungsspezifische Teile auslagern: Datenquellen, Prompts, Tool-Definitionen, Evaluationsfragen und Runtime-Konfiguration.

## Erste technische Annahmen

Diese Punkte sind bewusst vorlaeufig und sollen im Verlauf der Studie validiert werden:

- Python eignet sich gut fuer die erste Version, weil RAG-, Embedding- und Evaluationsbibliotheken dort schnell verfuegbar sind.
- Eine kleine HTTP API ist der zentrale Einstiegspunkt; das HTML-Frontend ist der erste Client.
- Das Frontend bleibt zunaechst statisch und ohne Build-Schritt, damit Docker und lokale Tests einfach bleiben.
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
│       ├── api/
│       ├── ingestion/
│       ├── retrieval/
│       ├── agent/
│       ├── tools/
│       └── evaluation/
├── template/
│   ├── app_profile.json
│   └── evaluation_cases.json
├── apps/
│   └── <app-id>/
│       ├── app_profile.json
│       └── evaluation_cases.json
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/
│   └── sample/
│       └── agentic_rag_basics.md
└── tests/
```

## Datenstruktur

`data/` ist der lokale Wissensbereich. Jede direkte Unterstruktur ist eine Collection, die spaeter getrennt ingestiert, gefiltert oder fuer unterschiedliche Anwendungen verwendet werden kann.

```text
data/
├── sample/
├── product-docs/
├── policies/
└── customer-a/
```

Die Ingestion liest aktuell `.md` und `.txt` Dateien rekursiv aus diesen Collection-Ordnern. Jeder Chunk erhaelt Metadaten fuer Collection, relativen Dateipfad, Dateiname, Dateityp, Chunk-Index und Zeichenposition.

## App-Instanzen

Die bisherige Template-App bleibt als `default`-Instanz verfuegbar. Zusaetzlich koennen wiederverwendbare Anwendungen unter `apps/<app-id>/` angelegt werden. Eine App-Instanz besitzt ihr eigenes Profil und optional eigene Evaluationsfaelle:

```text
apps/
└── policy-assistant/
    ├── app_profile.json
    └── evaluation_cases.json
```

Das Wissen einer App liegt unter `data/<app-id>/<collection>/`:

```text
data/
└── policy-assistant/
    └── policies/
        └── handbook.md
```

Damit koennen verschiedene Anwendungen dieselbe Runtime, dieselben Provider und dasselbe Frontend nutzen, aber getrennte Prompts, Collections und Tests haben.

Wissen kann pro App und Collection ueber die API inspiziert und ergaenzt werden:

- `GET /apps/{app_id}/collections/{collection}/documents`
- `POST /apps/{app_id}/collections/{collection}/documents`
- `GET /apps/{app_id}/ingestion/preview?collection={collection}`
- `GET /apps/{app_id}/retrieval/search?q={query}&collection={collection}`

Der Upload-Endpunkt erwartet aktuell JSON:

```json
{
  "filename": "handbook.md",
  "content": "Das neue Wissen fuer diese Collection."
}
```

Unterstuetzt werden zunaechst `.md` und `.txt`. Die Dateien werden unter `data/<app-id>/<collection>/` gespeichert und stehen danach direkt fuer Retrieval und Chat zur Verfuegung.

## Naechster Schritt

Als naechstes kann eine konkrete Anwendung auf dieses Template gelegt werden: eigene Collection unter `data/`, angepasstes `template/app_profile.json`, eigene `template/evaluation_cases.json` und danach optional ein echter Embedding-Provider wie Ollama.

## Template-Konfiguration

Anwendungsspezifische Einstellungen liegen unter `template/`:

- `template/app_profile.json`: Name, Beschreibung, Default-Collection, Default-Top-k, Antwort-Policy und aktivierte Tools
- `template/evaluation_cases.json`: wiederholbare Evaluationsfragen und erwartete Quellen/Tool-Nutzung

Damit kann dieselbe technische Basis fuer verschiedene Anwendungen genutzt werden, ohne Agent-, Retrieval- oder API-Code umzuschreiben.

## Evaluation

Die Evaluation nutzt feste Testfragen gegen den aktuellen deterministischen Agenten. Sie prueft keine perfekte Musterantwort, sondern beobachtbare Eigenschaften:

- Antwort ist nicht leer
- erwartete Quellen werden gefunden
- erforderliche Begriffe im Antwortformat sind vorhanden
- Unsicherheit wird ausgewiesen
- erwartete Tools wurden genutzt

Der lokale Endpunkt `GET /evaluation/run` fuehrt die Default-Evaluation gegen `data/sample/` aus und liefert eine Zusammenfassung mit einzelnen Checks.

## Agent Tools

Der aktuelle Agent nutzt bewusst wenige, explizite Tools:

- `search_knowledge_base`: durchsucht lokale Collections ueber den Retriever
- `read_source`: liest ein konkretes Quelldokument aus `data/`
- `answer_with_citations`: formuliert eine einfache Antwort mit Quellenliste

Der Chat-Endpunkt `POST /chat` ruft diesen deterministischen Agenten auf und gibt `answer`, `sources`, `uncertainty`, `trace` und `tool_calls` zurueck. Damit ist der Ablauf sichtbar, bevor spaeter ein LLM selbst ueber Tool-Nutzung entscheidet.

## Embedding-Konfiguration

Eine ausfuehrlichere Uebersicht steht in [CONFIGURATION.md](CONFIGURATION.md).

Der aktuelle Stand nutzt standardmaessig einen lokalen Dummy-Provider:

```text
AGENTIC_RAG_EMBEDDING_PROVIDER=hash
AGENTIC_RAG_EMBEDDING_MODEL=local-hash-v1
AGENTIC_RAG_EMBEDDING_DIMENSION=64
```

Der Hash-Provider ist deterministisch und braucht keine API-Keys oder Modell-Downloads. Er ist nicht als semantisch guter Embedder gedacht, sondern als stabile lokale Implementierung fuer Tests, Docker und die Architekturstudie.

Die Konfiguration ist bereits fuer spaetere Provider vorbereitet:

```text
AGENTIC_RAG_EMBEDDING_PROVIDER=ollama
AGENTIC_RAG_EMBEDDING_MODEL=nomic-embed-text
AGENTIC_RAG_EMBEDDING_API_BASE_URL=http://host.docker.internal:11434
```

`ollama`, `openai` und andere Embedding-Provider sind noch nicht implementiert. Sie sollen spaeter hinter derselben `EmbeddingProvider`-Schnittstelle ergaenzt werden, ohne Ingestion, Vector Store oder Retriever umzubauen.

## LLM-Konfiguration

Die LLM-Konfiguration kann ueber `.env` gesteuert werden. Der aktuelle Agent nutzt standardmaessig den deterministischen lokalen Antwort-Composer, kann aber fuer Chat-Antworten auf Ollama umgestellt werden.

```text
AGENTIC_RAG_LLM_PROVIDER=deterministic
AGENTIC_RAG_LLM_MODEL=local-deterministic-v1
AGENTIC_RAG_LLM_API_BASE_URL=http://host.docker.internal:11434
```

Ollama kann so konfiguriert werden:

```text
AGENTIC_RAG_LLM_PROVIDER=ollama
AGENTIC_RAG_LLM_MODEL=llama3.1
AGENTIC_RAG_LLM_API_BASE_URL=http://ollama:11434
AGENTIC_RAG_LLM_TIMEOUT_SECONDS=300
AGENTIC_RAG_LLM_MAX_TOKENS=160
```

Ollama kann optional als zweiter Compose-Service gestartet werden:

```bash
docker compose --profile ollama up --build
```

## Lokal Starten

Der aktuelle Stand startet eine minimale HTTP API und das statische Chat-Frontend aus einem Container:

```bash
docker compose up --build
```

Danach ist das Frontend unter `http://localhost:8000` erreichbar. Der Health-Check liegt unter `http://localhost:8000/health`; der Chat sendet Nachrichten an `POST /chat`.

Ein kompletter Boot- und Smoke-Test-Aufbau ist in [TEST_SETUP.md](TEST_SETUP.md) beschrieben. Kurzform:

```bash
python3 scripts/smoke_test.py
```

Nuetzliche lokale Endpunkte:

- `GET /collections` zeigt die erkannten Collections unter `data/`
- `GET /apps` zeigt alle konfigurierten App-Instanzen
- `GET /apps/{app_id}` zeigt Profil und Runtime-Pfade einer App
- `GET /apps/{app_id}/collections` zeigt die Collections einer App
- `POST /apps/{app_id}/chat` chattet gegen eine bestimmte App-Instanz
- `GET /apps/{app_id}/evaluation/run` startet die Evaluation einer App
- `GET /ingestion/preview?collection=sample` zeigt die ersten ingestierten Chunks einer Collection
- `GET /vector-store/preview?collection=sample&q=agentic` baut lokal einen In-Memory-Index und zeigt Suchtreffer mit Scores
- `GET /retrieval/search?collection=sample&q=agentic&top_k=3` nutzt den Retriever und liefert agentenfreundliche Suchergebnisse mit Trace
- `GET /evaluation/run` fuehrt die Default-Evaluation aus
- `GET /template/profile` zeigt das aktive Anwendungsprofil
