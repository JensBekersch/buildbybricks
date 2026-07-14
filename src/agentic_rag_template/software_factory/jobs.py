"""Job model for long-running Software Factory workflows."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELED = "canceled"

STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_COMPLETED = "completed"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_SKIPPED = "skipped"


@dataclass(frozen=True)
class ArchitectureGenerationStepDefinition:
    """Stable step contract exposed to UI and API clients."""

    key: str
    label: str


ARCHITECTURE_GENERATION_STEPS: Tuple[ArchitectureGenerationStepDefinition, ...] = (
    ArchitectureGenerationStepDefinition("validate_description", "Beschreibung pruefen"),
    ArchitectureGenerationStepDefinition("load_schema", "Schema laden"),
    ArchitectureGenerationStepDefinition("load_method_sources", "Methodenwissen laden"),
    ArchitectureGenerationStepDefinition("analyze_requirements", "Anforderungen analysieren"),
    ArchitectureGenerationStepDefinition("synthesize_architecture", "Architecture Sheet erzeugen"),
    ArchitectureGenerationStepDefinition("review_architecture", "Architecture Review ausfuehren"),
    ArchitectureGenerationStepDefinition("validate_contract", "Schema validieren"),
)


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for persisted job events."""
    return datetime.now(timezone.utc)


def timestamp(value: Optional[datetime]) -> Optional[str]:
    """Serialize datetimes consistently for API responses and persistence."""
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse serialized timestamps from API/JSONB payloads."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass
class ArchitectureGenerationLogEntry:
    """Append-only job log entry."""

    message: str
    level: str = "info"
    step: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": timestamp(self.created_at),
            "level": self.level,
            "step": self.step,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ArchitectureGenerationLogEntry":
        return cls(
            message=str(payload.get("message", "")),
            level=str(payload.get("level", "info")),
            step=str(payload.get("step", "")),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
        )


@dataclass
class ArchitectureGenerationStep:
    """Current state of a single architecture generation step."""

    key: str
    label: str
    status: str = STEP_STATUS_PENDING
    message: str = ""
    error: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def start(self, message: str = "") -> None:
        self.status = STEP_STATUS_RUNNING
        self.message = message or self.message
        self.error = ""
        self.started_at = self.started_at or utc_now()
        self.finished_at = None

    def complete(self, message: str = "") -> None:
        self.status = STEP_STATUS_COMPLETED
        self.message = message or self.message
        self.error = ""
        self.started_at = self.started_at or utc_now()
        self.finished_at = utc_now()

    def fail(self, error: str) -> None:
        self.status = STEP_STATUS_FAILED
        self.error = error
        self.started_at = self.started_at or utc_now()
        self.finished_at = utc_now()

    def skip(self, message: str = "") -> None:
        self.status = STEP_STATUS_SKIPPED
        self.message = message or self.message
        self.finished_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "started_at": timestamp(self.started_at),
            "finished_at": timestamp(self.finished_at),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ArchitectureGenerationStep":
        return cls(
            key=str(payload.get("key", "")),
            label=str(payload.get("label", "")),
            status=str(payload.get("status", STEP_STATUS_PENDING)),
            message=str(payload.get("message", "")),
            error=str(payload.get("error", "")),
            started_at=parse_timestamp(payload.get("started_at")),
            finished_at=parse_timestamp(payload.get("finished_at")),
        )


@dataclass
class ArchitectureGenerationJob:
    """Lifecycle state for one long-running Architecture Sheet generation."""

    id: str
    app_id: str
    description: str
    generation_mode: str
    llm_provider: str = "none"
    llm_model: str = "none"
    status: str = JOB_STATUS_QUEUED
    current_step: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    steps: List[ArchitectureGenerationStep] = field(default_factory=list)
    logs: List[ArchitectureGenerationLogEntry] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: str = ""

    @classmethod
    def create(
        cls,
        description: str,
        generation_mode: str,
        app_id: str = "software-factory",
        llm_provider: str = "none",
        llm_model: str = "none",
        job_id: Optional[str] = None,
    ) -> "ArchitectureGenerationJob":
        normalized_description = " ".join(description.strip().split())
        if not normalized_description:
            raise ValueError("description is required")
        normalized_generation_mode = (generation_mode or "agentic_with_review").strip().lower().replace("-", "_")
        if normalized_generation_mode not in {"agentic", "agentic_with_review"}:
            raise ValueError("generation_mode must be 'agentic' or 'agentic_with_review'")

        job = cls(
            id=job_id or uuid4().hex,
            app_id=app_id,
            description=normalized_description,
            generation_mode=normalized_generation_mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
            steps=[
                ArchitectureGenerationStep(key=definition.key, label=definition.label)
                for definition in ARCHITECTURE_GENERATION_STEPS
            ],
        )
        job.add_log("Job wurde erzeugt.", step="")
        return job

    def mark_running(self, message: str = "Job wird ausgefuehrt.") -> None:
        if self.status == JOB_STATUS_QUEUED:
            self.started_at = utc_now()
            self.add_log(message)
        self.status = JOB_STATUS_RUNNING
        self.error = ""
        self._touch()

    def start_step(self, key: str, message: str = "") -> None:
        self.mark_running()
        step = self._step(key)
        step.start(message)
        self.current_step = key
        self._touch()
        self.add_log(message or step.label, step=key)

    def complete_step(self, key: str, message: str = "") -> None:
        step = self._step(key)
        step.complete(message)
        self.current_step = key
        self._touch()
        self.add_log(message or f"Schritt abgeschlossen: {step.label}", step=key)

    def fail_step(self, key: str, error: str) -> None:
        step = self._step(key)
        step.fail(error)
        self.current_step = key
        self.fail(error)

    def skip_step(self, key: str, message: str = "") -> None:
        step = self._step(key)
        step.skip(message)
        self._touch()
        self.add_log(message or f"Schritt uebersprungen: {step.label}", step=key)

    def complete(self, result: Dict[str, Any]) -> None:
        self.status = JOB_STATUS_COMPLETED
        self.result = result
        self.error = ""
        self.finished_at = utc_now()
        self.current_step = ""
        self._touch()
        self.add_log("Job wurde erfolgreich abgeschlossen.")

    def fail(self, error: str) -> None:
        self.status = JOB_STATUS_FAILED
        self.error = error
        self.finished_at = utc_now()
        self._touch()
        self.add_log(error, level="error", step=self.current_step)

    def cancel(self, message: str = "Job wurde abgebrochen.") -> None:
        self.status = JOB_STATUS_CANCELED
        self.error = message
        self.finished_at = utc_now()
        self._touch()
        self.add_log(message, level="warning", step=self.current_step)

    def add_log(self, message: str, level: str = "info", step: str = "") -> None:
        self.logs.append(ArchitectureGenerationLogEntry(message=message, level=level, step=step))
        self._touch()

    def to_dict(self, include_result: bool = True) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "app_id": self.app_id,
            "status": self.status,
            "current_step": self.current_step,
            "description": self.description,
            "generation_mode": self.generation_mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "created_at": timestamp(self.created_at),
            "updated_at": timestamp(self.updated_at),
            "started_at": timestamp(self.started_at),
            "finished_at": timestamp(self.finished_at),
            "error": self.error,
            "steps": [step.to_dict() for step in self.steps],
            "logs": [entry.to_dict() for entry in self.logs],
        }

        if include_result:
            payload["result"] = self.result

        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ArchitectureGenerationJob":
        return cls(
            id=str(payload["id"]),
            app_id=str(payload.get("app_id", "software-factory")),
            description=str(payload.get("description", "")),
            generation_mode=str(payload.get("generation_mode", "agentic_with_review")),
            llm_provider=str(payload.get("llm_provider", "none")),
            llm_model=str(payload.get("llm_model", "none")),
            status=str(payload.get("status", JOB_STATUS_QUEUED)),
            current_step=str(payload.get("current_step", "")),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
            updated_at=parse_timestamp(payload.get("updated_at")) or utc_now(),
            started_at=parse_timestamp(payload.get("started_at")),
            finished_at=parse_timestamp(payload.get("finished_at")),
            steps=[
                ArchitectureGenerationStep.from_dict(step)
                for step in payload.get("steps", [])
            ],
            logs=[
                ArchitectureGenerationLogEntry.from_dict(entry)
                for entry in payload.get("logs", [])
            ],
            result=payload.get("result"),
            error=str(payload.get("error", "")),
        )

    def _step(self, key: str) -> ArchitectureGenerationStep:
        for step in self.steps:
            if step.key == key:
                return step
        raise KeyError(f"Unknown architecture generation step: {key}")

    def _touch(self) -> None:
        self.updated_at = utc_now()
