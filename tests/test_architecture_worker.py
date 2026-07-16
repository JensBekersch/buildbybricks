from agentic_rag_template.config import Settings
from agentic_rag_template.software_factory import (
    EVENT_STEP_COMPLETED,
    EVENT_STEP_STARTED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_CANCELED,
    JOB_STATUS_FAILED,
    JOB_STATUS_RUNNING,
    ArchitectureGenerationEvent,
    ArchitectureGenerationJob,
)
from agentic_rag_template.software_factory.worker import ArchitectureGenerationWorker
from agentic_rag_template.workflows.models import (
    STEP_TYPE_AGENT,
    VERSION_STATUS_PUBLISHED,
    AgentDefinition,
    AgentVersion,
    Workflow,
    WorkflowRun,
    WorkflowStep,
    WorkflowVersion,
)


class DummyResult:
    def to_dict(self):
        return {"architecture_sheet": {"artifact_name": "Team Todo"}}


class DummyProvider:
    name = "test-llm"
    model = "test-model"

    def generate_answer(self, request):
        raise NotImplementedError

    def generate_json(self, system_prompt, user_prompt):
        return {"artifact_name": "Team Todo"}


class DummyArtifact:
    def to_dict(self):
        return {
            "id": "job-1",
            "job_id": "job-1",
            "title": "Team Todo",
            "json_path": "architecture-sheets/team-todo-job-1.json",
            "markdown_path": "architecture-sheets/team-todo-job-1.md",
        }


class DummyArtifactStore:
    def __init__(self):
        self.saved_results = []

    def save_architecture_sheet(self, job, result):
        self.saved_results.append((job.id, result))
        return DummyArtifact()


class DummyStore:
    def __init__(self, job=None):
        self.job = job
        self.saved_jobs = []
        self.initialized = False
        self.claimed = False

    def initialize(self):
        self.initialized = True

    def claim_next(self, app_id=None):
        if self.claimed:
            return None
        self.claimed = True
        if self.job is None:
            return None
        self.job.mark_running("Worker hat den Job uebernommen.")
        return self.job

    def get(self, job_id):
        if self.job is not None and self.job.id == job_id:
            return self.job
        return None

    def save(self, job):
        self.saved_jobs.append(job.to_dict())


class DummyWorkflowStore:
    def __init__(self, workflow_run=None):
        self.workflow_run = workflow_run
        self.saved_runs = []
        self.initialized = False
        self.claimed = False

    def initialize(self):
        self.initialized = True

    def claim_next_run(self, workflow_slug=None):
        if self.claimed:
            return None
        self.claimed = True
        if self.workflow_run is None:
            return None
        self.workflow_run.start()
        return self.workflow_run

    def save_run(self, workflow_run):
        self.workflow_run = WorkflowRun.from_dict(workflow_run.to_dict())
        self.saved_runs.append(workflow_run.to_dict())


def _workflow_run() -> WorkflowRun:
    agent_version = AgentVersion(
        agent=AgentDefinition(name="Requirement Analyst", slug="requirement-analyst"),
        version_number=1,
        status=VERSION_STATUS_PUBLISHED,
        system_prompt="System",
        user_prompt_template="Input: {{ description }}",
        input_contract={"required": ["description"]},
        output_schema={"type": "object", "required": ["artifact_name"]},
        model_configuration={"provider": "fake", "model": "fake-json"},
    )
    workflow_version = WorkflowVersion(
        workflow=Workflow(name="Architecture Sheet", slug="architecture-sheet"),
        version_number=1,
        status=VERSION_STATUS_PUBLISHED,
        final_output_key="requirements",
    )
    workflow_version.steps = [
        WorkflowStep(
            workflow_version,
            "Analyse",
            "analysis",
            STEP_TYPE_AGENT,
            1,
            agent_version=agent_version,
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="requirements",
        )
    ]
    return WorkflowRun(
        workflow_version=workflow_version,
        initial_input={"description": "Eine einfache Team Todo Liste."},
        id="workflow-run-1",
        started_by="test",
    )


def test_architecture_worker_processes_claimed_job(monkeypatch) -> None:
    job = ArchitectureGenerationJob.create(
        "Eine einfache Team Todo Liste.",
        generation_mode="agentic",
        job_id="job-1",
    )
    store = DummyStore(job)

    def fake_generate_architecture_sheet(*args, **kwargs):
        event_handler = kwargs["event_handler"]
        event_handler(
            ArchitectureGenerationEvent(
                type=EVENT_STEP_STARTED,
                step="validate_description",
                message="Beschreibung wird geprueft.",
            )
        )
        event_handler(
            ArchitectureGenerationEvent(
                type=EVENT_STEP_COMPLETED,
                step="validate_description",
                message="Beschreibung ist verwendbar.",
            )
        )
        return DummyResult()

    monkeypatch.setattr(
        "agentic_rag_template.software_factory.worker.generate_architecture_sheet",
        fake_generate_architecture_sheet,
    )
    worker = ArchitectureGenerationWorker(
        settings=Settings(),
        job_store=store,
        workflow_store=DummyWorkflowStore(),
        llm_provider_factory=lambda settings: DummyProvider(),
        artifact_store_factory=lambda application: DummyArtifactStore(),
    )

    processed = worker.process_next()

    assert processed is True
    assert job.status == JOB_STATUS_COMPLETED
    assert job.result["architecture_sheet"]["artifact_name"] == "Team Todo"
    assert job.result["artifact"]["json_path"] == "architecture-sheets/team-todo-job-1.json"
    assert job.steps[0].status == "completed"
    assert any(snapshot["status"] == JOB_STATUS_RUNNING for snapshot in store.saved_jobs)
    assert store.saved_jobs[-1]["status"] == JOB_STATUS_COMPLETED


def test_architecture_worker_returns_false_without_queued_job() -> None:
    store = DummyStore()
    workflow_store = DummyWorkflowStore()
    worker = ArchitectureGenerationWorker(
        settings=Settings(),
        job_store=store,
        workflow_store=workflow_store,
        llm_provider_factory=lambda settings: DummyProvider(),
        artifact_store_factory=lambda application: DummyArtifactStore(),
    )

    assert worker.process_next() is False
    assert workflow_store.claimed is True


def test_architecture_worker_marks_job_failed_on_error(monkeypatch) -> None:
    job = ArchitectureGenerationJob.create(
        "Eine einfache Team Todo Liste.",
        generation_mode="agentic",
        job_id="job-1",
    )
    store = DummyStore(job)

    def failing_generate_architecture_sheet(*args, **kwargs):
        raise RuntimeError("LLM nicht erreichbar")

    monkeypatch.setattr(
        "agentic_rag_template.software_factory.worker.generate_architecture_sheet",
        failing_generate_architecture_sheet,
    )
    worker = ArchitectureGenerationWorker(
        settings=Settings(),
        job_store=store,
        workflow_store=DummyWorkflowStore(),
        llm_provider_factory=lambda settings: DummyProvider(),
        artifact_store_factory=lambda application: DummyArtifactStore(),
    )

    processed = worker.process_next()

    assert processed is True
    assert job.status == JOB_STATUS_FAILED
    assert "LLM nicht erreichbar" in job.error
    assert store.saved_jobs[-1]["status"] == JOB_STATUS_FAILED


def test_architecture_worker_does_not_complete_canceled_job(monkeypatch) -> None:
    job = ArchitectureGenerationJob.create(
        "Eine einfache Team Todo Liste.",
        generation_mode="agentic",
        job_id="job-1",
    )
    store = DummyStore(job)

    def fake_generate_architecture_sheet(*args, **kwargs):
        job.cancel("Benutzerabbruch.")
        store.save(job)
        return DummyResult()

    monkeypatch.setattr(
        "agentic_rag_template.software_factory.worker.generate_architecture_sheet",
        fake_generate_architecture_sheet,
    )
    worker = ArchitectureGenerationWorker(
        settings=Settings(),
        job_store=store,
        workflow_store=DummyWorkflowStore(),
        llm_provider_factory=lambda settings: DummyProvider(),
        artifact_store_factory=lambda application: DummyArtifactStore(),
    )

    processed = worker.process_next()

    assert processed is True
    assert job.status == JOB_STATUS_CANCELED
    assert job.result is None
    assert store.saved_jobs[-1]["status"] == JOB_STATUS_CANCELED


def test_worker_processes_generic_workflow_run_when_no_architecture_job() -> None:
    architecture_store = DummyStore()
    workflow_store = DummyWorkflowStore(_workflow_run())
    worker = ArchitectureGenerationWorker(
        settings=Settings(),
        job_store=architecture_store,
        workflow_store=workflow_store,
        llm_provider_factory=lambda settings: DummyProvider(),
        artifact_store_factory=lambda application: DummyArtifactStore(),
    )

    processed = worker.process_next()

    assert processed is True
    assert workflow_store.saved_runs[-1]["id"] == "workflow-run-1"
    assert workflow_store.saved_runs[-1]["status"] == "succeeded"
    assert workflow_store.saved_runs[-1]["final_output"] == {"artifact_name": "Team Todo"}
    assert workflow_store.saved_runs[-1]["artifacts"][0]["artifact_key"] == "requirements"
