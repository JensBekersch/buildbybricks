import pytest

from agentic_rag_template.workflows.models import (
    RUN_STATUS_SUCCEEDED,
    STEP_STATUS_SUCCEEDED,
    STEP_TYPE_AGENT,
    STEP_TYPE_TASK,
    VERSION_STATUS_PUBLISHED,
    AgentDefinition,
    AgentVersion,
    StepRun,
    Workflow,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowStep,
    WorkflowVersion,
)

from agentic_rag_template.workflows.store import PostgresWorkflowStore, WorkflowStore, WorkflowStoreError


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        params = params or {}
        self.connection.statements.append((sql, params))
        normalized_sql = " ".join(sql.split()).upper()

        if normalized_sql.startswith("INSERT INTO WORKFLOW_DEFINITIONS"):
            self.connection.workflow_definitions[params["slug"]] = params["payload"]
        elif normalized_sql.startswith("INSERT INTO WORKFLOW_VERSIONS"):
            key = (params["workflow_slug"], params["version_number"])
            self.connection.workflow_versions[key] = params["payload"]
        elif normalized_sql.startswith("INSERT INTO AGENT_DEFINITIONS"):
            self.connection.agent_definitions[params["slug"]] = params["payload"]
        elif normalized_sql.startswith("INSERT INTO AGENT_VERSIONS"):
            key = (params["agent_slug"], params["version_number"])
            self.connection.agent_versions[key] = params["payload"]
        elif normalized_sql.startswith("INSERT INTO WORKFLOW_RUNS"):
            self.connection.workflow_runs[params["id"]] = params["payload"]
        elif normalized_sql.startswith("INSERT INTO WORKFLOW_ARTIFACTS"):
            key = (params["workflow_run_id"], params["artifact_key"])
            self.connection.workflow_artifacts[key] = params["payload"]
        elif normalized_sql.startswith("SELECT PAYLOAD FROM WORKFLOW_VERSIONS WHERE WORKFLOW_SLUG"):
            payload = self.connection.workflow_versions.get((params["workflow_slug"], params["version_number"]))
            self.connection.fetchone_result = (payload,) if payload else None
        elif normalized_sql.startswith("SELECT PAYLOAD FROM WORKFLOW_VERSIONS WHERE WORKFLOW_SLUG =") and "ORDER BY" in normalized_sql:
            rows = [
                payload
                for (workflow_slug, _version_number), payload in self.connection.workflow_versions.items()
                if workflow_slug == params["workflow_slug"]
            ]
            self.connection.fetchall_result = [(payload,) for payload in rows]
        elif normalized_sql.startswith("SELECT PAYLOAD FROM AGENT_VERSIONS WHERE AGENT_SLUG"):
            payload = self.connection.agent_versions.get((params["agent_slug"], params["version_number"]))
            self.connection.fetchone_result = (payload,) if payload else None
        elif normalized_sql.startswith("SELECT PAYLOAD FROM WORKFLOW_RUNS WHERE ID"):
            payload = self.connection.workflow_runs.get(params["id"])
            self.connection.fetchone_result = (payload,) if payload else None
        elif normalized_sql.startswith("SELECT PAYLOAD FROM WORKFLOW_RUNS"):
            rows = list(self.connection.workflow_runs.values())
            if "WORKFLOW_SLUG" in params:
                rows = [
                    payload
                    for payload in rows
                    if payload["workflow_version"]["workflow"]["slug"] == params["workflow_slug"]
                ]
            self.connection.fetchall_result = [(payload,) for payload in rows[: params.get("limit", 50)]]
        elif normalized_sql.startswith("SELECT PAYLOAD FROM WORKFLOW_ARTIFACTS"):
            rows = [
                payload
                for (run_id, _artifact_key), payload in self.connection.workflow_artifacts.items()
                if run_id == params["run_id"] and payload.get("is_validated") is True
            ]
            self.connection.fetchall_result = [(payload,) for payload in rows]

    def fetchone(self):
        return self.connection.fetchone_result

    def fetchall(self):
        return self.connection.fetchall_result


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.workflow_definitions = {}
        self.workflow_versions = {}
        self.agent_definitions = {}
        self.agent_versions = {}
        self.workflow_runs = {}
        self.workflow_artifacts = {}
        self.fetchone_result = None
        self.fetchall_result = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self):
        return FakeCursor(self)


def _store(connection):
    return PostgresWorkflowStore(
        "postgresql://example",
        connection_factory=lambda database_url: connection,
    )


def _agent_version() -> AgentVersion:
    return AgentVersion(
        agent=AgentDefinition(name="Requirement Analyst", slug="requirement-analyst"),
        version_number=1,
        status=VERSION_STATUS_PUBLISHED,
        system_prompt="System",
        user_prompt_template="User {{ description }}",
        input_contract={"required": ["description"]},
        output_schema={"type": "object", "required": ["artifact_name"]},
        model_configuration={"provider": "fake", "model": "fake-json"},
    )


def _workflow_version(agent_version=None) -> WorkflowVersion:
    version = WorkflowVersion(
        workflow=Workflow(name="Django Machine", slug="django-machine"),
        version_number=1,
        status=VERSION_STATUS_PUBLISHED,
        final_output_key="final",
    )
    version.steps = [
        WorkflowStep(
            version,
            "Analyse",
            "analysis",
            STEP_TYPE_AGENT,
            1,
            agent_version=agent_version or _agent_version(),
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="requirements",
        ),
        WorkflowStep(
            version,
            "Final",
            "final",
            STEP_TYPE_TASK,
            2,
            task_definition={"task_type": "echo"},
            output_key="final",
        ),
    ]
    return version


def test_postgres_workflow_store_initializes_schema() -> None:
    connection = FakeConnection()

    _store(connection).initialize()

    statements = [statement for statement, _params in connection.statements]
    assert any("CREATE TABLE IF NOT EXISTS workflow_definitions" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS workflow_versions" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS agent_versions" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS workflow_runs" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS workflow_artifacts" in statement for statement in statements)


def test_postgres_workflow_store_sql_guards_published_version_updates() -> None:
    connection = FakeConnection()
    store = _store(connection)

    store.save_workflow_version(_workflow_version())
    store.save_agent_version(_agent_version())

    statements = [" ".join(statement.split()) for statement, _params in connection.statements]
    assert any(
        "WHERE workflow_versions.status <> 'published' OR workflow_versions.payload = EXCLUDED.payload" in statement
        for statement in statements
    )
    assert any(
        "WHERE agent_versions.status <> 'published' OR agent_versions.payload = EXCLUDED.payload" in statement
        for statement in statements
    )


def test_postgres_workflow_store_implements_workflow_store_contract() -> None:
    assert isinstance(_store(FakeConnection()), WorkflowStore)


def test_postgres_workflow_store_saves_and_loads_agent_version() -> None:
    connection = FakeConnection()
    store = _store(connection)
    agent_version = _agent_version()

    store.save_agent_version(agent_version)
    loaded = store.get_agent_version("requirement-analyst", 1)

    assert loaded is not None
    assert loaded.agent.slug == "requirement-analyst"
    assert loaded.status == VERSION_STATUS_PUBLISHED
    assert loaded.input_contract["required"] == ["description"]


def test_postgres_workflow_store_saves_and_loads_workflow_version() -> None:
    connection = FakeConnection()
    store = _store(connection)
    version = _workflow_version()

    store.save_workflow_version(version)
    loaded = store.get_workflow_version("django-machine", 1)

    assert loaded is not None
    assert loaded.workflow.slug == "django-machine"
    assert loaded.steps[0].agent_version is not None
    assert loaded.steps[0].agent_version.agent.slug == "requirement-analyst"
    assert loaded.steps[1].task_definition["task_type"] == "echo"


def test_postgres_workflow_store_allows_idempotent_published_workflow_save() -> None:
    connection = FakeConnection()
    store = _store(connection)
    version = _workflow_version()

    store.save_workflow_version(version)
    store.save_workflow_version(version)

    loaded = store.get_workflow_version("django-machine", 1)
    assert loaded is not None
    assert loaded.final_output_key == "final"


def test_postgres_workflow_store_rejects_published_workflow_version_mutation() -> None:
    connection = FakeConnection()
    store = _store(connection)
    version = _workflow_version()
    store.save_workflow_version(version)

    changed_version = _workflow_version()
    changed_version.final_output_key = "changed-final"

    with pytest.raises(WorkflowStoreError, match="published workflow version django-machine v1 is immutable"):
        store.save_workflow_version(changed_version)

    loaded = store.get_workflow_version("django-machine", 1)
    assert loaded is not None
    assert loaded.final_output_key == "final"


def test_postgres_workflow_store_rejects_published_agent_version_mutation() -> None:
    connection = FakeConnection()
    store = _store(connection)
    agent_version = _agent_version()
    store.save_agent_version(agent_version)

    changed_agent = _agent_version()
    changed_agent.system_prompt = "Changed system prompt"

    with pytest.raises(WorkflowStoreError, match="published agent version requirement-analyst v1 is immutable"):
        store.save_agent_version(changed_agent)

    loaded = store.get_agent_version("requirement-analyst", 1)
    assert loaded is not None
    assert loaded.system_prompt == "System"


def test_postgres_workflow_store_saves_and_loads_run_snapshot_and_artifacts() -> None:
    connection = FakeConnection()
    store = _store(connection)
    version = _workflow_version()
    run = WorkflowRun(workflow_version=version, initial_input={"description": "Eine Todo-App."}, id="run-1")
    run.start()
    step_run = StepRun(workflow_run_id=run.id, workflow_step=version.steps[0])
    step_run.status = STEP_STATUS_SUCCEEDED
    step_run.validated_output = {"artifact_name": "Todo"}
    run.step_runs.append(step_run)
    run.artifacts.append(
        WorkflowArtifact(
            workflow_run_id=run.id,
            step_run=step_run,
            artifact_key="requirements",
            content={"artifact_name": "Todo"},
            is_validated=True,
        )
    )
    run.succeed({"artifact_name": "Todo"})

    store.save_run(run)
    loaded = store.get_run("run-1")
    artifacts = store.list_validated_artifacts("run-1")
    runs = store.list_runs(workflow_slug="django-machine")

    assert loaded is not None
    assert loaded.status == RUN_STATUS_SUCCEEDED
    assert loaded.final_output == {"artifact_name": "Todo"}
    assert loaded.step_runs[0].validated_output == {"artifact_name": "Todo"}
    assert artifacts[0].artifact_key == "requirements"
    assert artifacts[0].content == {"artifact_name": "Todo"}
    assert [run.id for run in runs] == ["run-1"]
