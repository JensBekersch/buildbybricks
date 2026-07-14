from agentic_rag_template.software_factory import (
    JOB_STATUS_COMPLETED,
    ArchitectureGenerationJob,
    PostgresArchitectureGenerationJobStore,
)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.connection.statements.append((sql, params))
        normalized_sql = " ".join(sql.split()).upper()
        if normalized_sql.startswith("INSERT INTO ARCHITECTURE_GENERATION_JOBS"):
            self.connection.rows[params["id"]] = params["payload"]
        if normalized_sql.startswith("SELECT PAYLOAD FROM ARCHITECTURE_GENERATION_JOBS WHERE ID"):
            payload = self.connection.rows.get(params["id"])
            self.connection.fetchone_result = (payload,) if payload else None
        if normalized_sql.startswith("SELECT PAYLOAD FROM ARCHITECTURE_GENERATION_JOBS ORDER BY"):
            self.connection.fetchall_result = [(payload,) for payload in self.connection.rows.values()]

    def fetchone(self):
        return self.connection.fetchone_result

    def fetchall(self):
        return self.connection.fetchall_result


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.rows = {}
        self.fetchone_result = None
        self.fetchall_result = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self):
        return FakeCursor(self)


def test_postgres_job_store_initializes_schema() -> None:
    connection = FakeConnection()
    store = PostgresArchitectureGenerationJobStore(
        "postgresql://example",
        connection_factory=lambda database_url: connection,
    )

    store.initialize()

    statements = [statement for statement, _params in connection.statements]
    assert any("CREATE TABLE IF NOT EXISTS architecture_generation_jobs" in statement for statement in statements)
    assert any("idx_architecture_generation_jobs_status" in statement for statement in statements)
    assert any("idx_architecture_generation_jobs_created_at" in statement for statement in statements)


def test_postgres_job_store_saves_and_loads_job_snapshot() -> None:
    connection = FakeConnection()
    store = PostgresArchitectureGenerationJobStore(
        "postgresql://example",
        connection_factory=lambda database_url: connection,
    )
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic",
        llm_provider="ollama",
        llm_model="qwen3:14b",
        job_id="job-1",
    )
    job.start_step("validate_description")
    job.complete_step("validate_description")
    job.complete({"architecture_sheet": {"artifact_name": "Team Todo"}})

    store.save(job)
    loaded = store.get("job-1")

    assert loaded is not None
    assert loaded.id == "job-1"
    assert loaded.status == JOB_STATUS_COMPLETED
    assert loaded.result["architecture_sheet"]["artifact_name"] == "Team Todo"
    assert loaded.steps[0].status == "completed"


def test_postgres_job_store_lists_recent_jobs() -> None:
    connection = FakeConnection()
    store = PostgresArchitectureGenerationJobStore(
        "postgresql://example",
        connection_factory=lambda database_url: connection,
    )
    first = ArchitectureGenerationJob.create("Erste App.", generation_mode="agentic", job_id="job-1")
    second = ArchitectureGenerationJob.create("Zweite App.", generation_mode="agentic", job_id="job-2")

    store.save(first)
    store.save(second)
    jobs = store.list()

    assert [job.id for job in jobs] == ["job-1", "job-2"]
