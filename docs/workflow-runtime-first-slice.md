# Generischer Workflow-Bereich: Erste Ausbaustufe

## Zusammenfassung

Diese Ausbaustufe fuehrt eine generische, konfigurierbare Workflow-Runtime ein.
Sie bildet noch keinen vollstaendigen Adminbereich und keine Datenbank-Migrationen
ab, legt aber die testbare Kernarchitektur fuer lineare Workflows an.

Ziel dieser Stufe ist ein stabiler technischer Kern, auf dem spaeter
Persistenz, Admin-UI, Versionierung und Berechtigungen aufbauen koennen.

## Umgesetzte Bausteine

- generische Workflow-, Version-, Step-, Run-, StepRun- und Artifact-Modelle
- generische AgentDefinition- und AgentVersion-Modelle
- Postgres-Snapshot-Store fuer Workflow- und Agent-Versionen, Runs und Artefakte
- erster konfigurierter Software-Factory-Workflow fuer Architecture-Sheet-Erzeugung
- providerneutrales `LLMProviderAdapter`-Interface
- Fake-Provider fuer Tests
- Input-Resolver fuer Workflow-Input, Step-Output, Artefakte, statische Werte und Run-Metadaten
- Prompt-Builder fuer AgentVersionen
- Validator-Registry
- Task-Registry
- lineare Workflow-Engine
- Retry-Grundmechanik
- Fehlerstrategien `STOP_WORKFLOW` und `CONTINUE_WITH_WARNING`
- Step-Bedingungen fuer einfache lineare Workflows
- validierte Workflow-Artefakte als Uebergabepunkt zum bestehenden Frontend

## Unterstuetzte Step-Typen

- `AGENT`
- `TASK`
- `VALIDATION`
- `TRANSFORMATION`
- `ARTIFACT`

`CONDITION` ist im Datenmodell vorgesehen. In dieser Stufe werden Bedingungen
als optionale Ausfuehrungsbedingung an Steps ausgewertet.

## Unterstuetzte Provider

- providerneutrales Adapter-Interface
- `FakeLLMProviderAdapter` fuer automatisierte Tests

Produktive Provider-Adapter fuer Ollama, OpenAI-kompatible APIs, OpenAI,
Anthropic oder Custom HTTP Provider sind noch offen.

## Unterstuetzte Validatoren

- `json_parse`
- `json_schema`
- `required_fields`
- `no_additional_properties`
- `unique_ids`

Weitere Validatoren aus dem Zielbild, etwa Numeric Preservation,
Explicit Test Count, Forbidden Terms, Evidence Required und Cross Field
Consistency, sind noch offen.

## Unterstuetzte Tasks

- `echo`
- `field_mapping`
- `text_merge`
- `result_extraction`

Weitere Task-Typen wie Template Rendering, Compatibility Mapping,
Condition Evaluation und registrierte Python-Tasks sind noch offen.

## Artefaktuebergabe

Jeder erfolgreich validierte Step erzeugt ein `WorkflowArtifact`.
Das finale Ergebnis eines Runs wird aus `WorkflowVersion.final_output_key`
oder, falls nicht gesetzt, aus dem letzten validierten Artefakt abgeleitet.

Damit kann das bestehende fachliche Frontend spaeter kontrolliert auf
validierte Artefakte zugreifen, ohne rohe LLM-Ausgaben direkt zu rendern.

## Persistenz

Die erste Persistenzstufe verwendet einen leichten Postgres-Store analog zum
bestehenden Architecture-Job-Store. Es wurden bewusst noch keine Django Models
oder Migrationen eingefuehrt, weil das aktuelle Projekt keine Django-App-Struktur
besitzt.

Der Store legt indexierbare Tabellen an und speichert vollstaendige Snapshots
als JSONB:

- `workflow_definitions`
- `workflow_versions`
- `agent_definitions`
- `agent_versions`
- `workflow_runs`
- `workflow_artifacts`

Die indexierten Spalten dienen der Suche nach Slug, Version, Run-ID, Status und
validierten Artefakten. Die Payloads halten die vollstaendige versionierte
Konfiguration und Ausfuehrungshistorie.

## Erster Workflow-Blueprint

Der bestehende Architecture-Sheet-Prozess ist als YAML-Blueprint hinterlegt:

- `apps/software-factory/workflows/architecture_sheet.yaml`

Der Blueprint beschreibt diese Schritte:

1. `validate_description`
2. `load_schema`
3. `load_method_sources`
4. `analyze_requirements`
5. `synthesize_architecture`
6. `review_architecture`
7. `validate_contract`

Die Agentenschritte referenzieren YAML-Agentenkonfigurationen:

- `requirement_analyst`
- `architecture_synthesizer`
- `architecture_reviewer`

Ein Loader uebersetzt den Blueprint in eine generische `WorkflowVersion`.
Damit ist der Prozess jetzt maschinenlesbar konfiguriert und strukturell mit
der generischen Workflow-Validierung pruefbar.

## Architekturentscheidungen

- Die erste Stufe bleibt framework-neutral, weil das bestehende Projekt aktuell
  keine Django-App ist.
- Die Engine enthaelt keine agentenspezifischen Rollen.
- Agentenverhalten entsteht ueber `AgentVersion`, Prompt, Modellkonfiguration,
  Input-Contract, Output-Schema und Validatoren.
- Deterministische Tasks werden nur aus einer Registry ausgefuehrt.
- Es wird kein frei eingegebener Python-Code ausgefuehrt.
- Die Runtime ist ohne echten LLM-Aufruf testbar.

## Ausgefuehrte Tests

- `python -m py_compile ...`
- `PYTHONPATH=src:. python -m pytest tests/test_workflow_runtime.py`
- `PYTHONPATH=src:. python -m pytest tests/test_workflow_runtime.py tests/test_workflow_store.py`
- `PYTHONPATH=src:. python -m pytest tests/test_software_factory_bootstrap.py tests/test_workflow_runtime.py`

Ergebnis:

```text
12 passed
```

## Bekannte Einschraenkungen

- Noch kein Adminbereich.
- Noch keine Django Models oder Migrationen, weil das aktuelle Projekt keine
  Django-App-Struktur besitzt.
- Noch keine produktiven Provider-Adapter.
- Der neue Architecture-Sheet-Workflow-Blueprint ist validierbar, aber die
  bestehende Generatorfunktion nutzt fuer die Produktion noch den bisherigen
  spezialisierten Codepfad.
- Noch keine Rechte-/Mandantentrennung fuer Workflow-Runs.
- Noch keine UI fuer Workflow-Konfiguration.
- Noch keine Anbindung der bestehenden Django-Machine-Ansicht an generische
  Workflow-Artefakte.

## Naechste sinnvolle Schritte

1. Die bestehende Architecture-Sheet-Ausfuehrung schrittweise auf den
   konfigurierten Workflow-Blueprint umstellen.
2. Admin-/Workflow-UI listenbasiert ergaenzen.
3. Produktive Provider-Adapter hinter dem Adapter-Interface implementieren.
4. Weitere Validatoren fuer fachliche Review-Regeln ergaenzen.
5. Optional spaeter: Migration von Snapshot-Store zu Django Models, falls das
   Projekt zur vollwertigen Django-App umgebaut wird.
