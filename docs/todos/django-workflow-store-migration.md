# TODO: Migration zu Django Workflow Models

Diese Notiz beschreibt den spaeteren Migrationspfad vom aktuellen
Postgres-Snapshot-Store zu vollwertigen Django Models.

## Ziel

Die generische Workflow-Runtime soll nicht vom konkreten Persistenzmechanismus
abhaengen. Der aktuelle `PostgresWorkflowStore` bleibt kurzfristig produktiv
nutzbar. Ein spaeterer `DjangoWorkflowStore` muss denselben `WorkflowStore`
Contract erfuellen.

## Neuer Architekturanker

`agentic_rag_template.workflows.store.WorkflowStore` ist der Persistenz-Port fuer:

- Workflow-Versionen
- Agent-Versionen
- Workflow-Runs
- validierte Artefakte

Alle kuenftigen Store-Implementierungen muessen diesen Contract erfuellen.

## Vorgeschlagene Django Models

1. `WorkflowDefinition`
   - `slug`
   - `name`
   - `status`
   - `payload`
   - `created_at`
   - `updated_at`

2. `WorkflowVersionModel`
   - `workflow`
   - `version_number`
   - `status`
   - `payload`
   - `created_at`
   - `published_at`
   - eindeutiger Constraint auf `workflow + version_number`

3. `AgentDefinitionModel`
   - `slug`
   - `name`
   - `status`
   - `payload`
   - `created_at`
   - `updated_at`

4. `AgentVersionModel`
   - `agent`
   - `version_number`
   - `status`
   - `payload`
   - `created_at`
   - `published_at`
   - eindeutiger Constraint auf `agent + version_number`

5. `WorkflowRunModel`
   - `id`
   - `workflow_slug`
   - `workflow_version_number`
   - `status`
   - `payload`
   - `started_at`
   - `finished_at`

6. `WorkflowArtifactModel`
   - `workflow_run`
   - `artifact_key`
   - `is_validated`
   - `payload`
   - `created_at`
   - eindeutiger Constraint auf `workflow_run + artifact_key`

## Migrationsprinzip

- Der Snapshot in `payload` bleibt die fuehrende Kompatibilitaetsschicht.
- Indexierte Spalten dienen Suche, Filterung, Listenansichten und Admin-UI.
- Domain-Objekte bleiben vorerst dataclass-basiert.
- Der Django Store uebersetzt zwischen Models und bestehenden `to_dict` /
  `from_dict` Methoden.
- Die Workflow-Engine darf weder Django Models noch QuerySets importieren.

## Umsetzungsschritte

1. Django-App-Struktur definieren, sobald das Gesamtprojekt auf Django umgebaut
   wird.
2. Models mit JSONField und den oben genannten Constraints anlegen.
3. `DjangoWorkflowStore` implementieren und gegen dieselben Store-Contract-Tests
   laufen lassen.
4. Datenmigration vom Snapshot-Store nur dann bauen, wenn produktive Daten aus
   dem aktuellen Store uebernommen werden muessen.
5. Admin-Views auf indexierte Spalten und validierte Artefakte setzen.

## Nicht Jetzt

- Kein Django als neue Runtime-Abhaengigkeit einfuehren.
- Keine halbfertigen Models ohne Django-App-Struktur anlegen.
- Keine doppelte Persistenzlogik in Engine oder Frontend einbauen.
