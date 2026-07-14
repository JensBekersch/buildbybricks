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


class DummyResult:
    def to_dict(self):
        return {"architecture_sheet": {"artifact_name": "Team Todo"}}


class DummyProvider:
    name = "test-llm"
    model = "test-model"

    def generate_answer(self, request):
        raise NotImplementedError


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
        llm_provider_factory=lambda settings: DummyProvider(),
    )

    processed = worker.process_next()

    assert processed is True
    assert job.status == JOB_STATUS_COMPLETED
    assert job.result["architecture_sheet"]["artifact_name"] == "Team Todo"
    assert job.steps[0].status == "completed"
    assert any(snapshot["status"] == JOB_STATUS_RUNNING for snapshot in store.saved_jobs)
    assert store.saved_jobs[-1]["status"] == JOB_STATUS_COMPLETED


def test_architecture_worker_returns_false_without_queued_job() -> None:
    store = DummyStore()
    worker = ArchitectureGenerationWorker(
        settings=Settings(),
        job_store=store,
        llm_provider_factory=lambda settings: DummyProvider(),
    )

    assert worker.process_next() is False


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
        llm_provider_factory=lambda settings: DummyProvider(),
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
        llm_provider_factory=lambda settings: DummyProvider(),
    )

    processed = worker.process_next()

    assert processed is True
    assert job.status == JOB_STATUS_CANCELED
    assert job.result is None
    assert store.saved_jobs[-1]["status"] == JOB_STATUS_CANCELED
