"""Data contracts for configurable workflow execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


WORKFLOW_STATUS_DRAFT = "draft"
WORKFLOW_STATUS_ACTIVE = "active"
WORKFLOW_STATUS_ARCHIVED = "archived"

VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_PUBLISHED = "published"
VERSION_STATUS_RETIRED = "retired"

STEP_TYPE_AGENT = "AGENT"
STEP_TYPE_TASK = "TASK"
STEP_TYPE_VALIDATION = "VALIDATION"
STEP_TYPE_TRANSFORMATION = "TRANSFORMATION"
STEP_TYPE_CONDITION = "CONDITION"
STEP_TYPE_ARTIFACT = "ARTIFACT"

RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCEEDED = "succeeded"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"
RUN_STATUS_WAITING_FOR_REVIEW = "waiting_for_review"

STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_SUCCEEDED = "succeeded"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_SKIPPED = "skipped"

FAILURE_STOP_WORKFLOW = "STOP_WORKFLOW"
FAILURE_RETRY_STEP = "RETRY_STEP"
FAILURE_CONTINUE_WITH_WARNING = "CONTINUE_WITH_WARNING"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Workflow:
    name: str
    slug: str
    description: str = ""
    status: str = WORKFLOW_STATUS_DRAFT
    created_by: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": timestamp(self.created_at),
            "updated_at": timestamp(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Workflow":
        return cls(
            name=str(payload.get("name", "")),
            slug=str(payload.get("slug", "")),
            description=str(payload.get("description", "")),
            status=str(payload.get("status", WORKFLOW_STATUS_DRAFT)),
            created_by=str(payload.get("created_by", "")),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
            updated_at=parse_timestamp(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class WorkflowVersion:
    workflow: Workflow
    version_number: int
    status: str = VERSION_STATUS_DRAFT
    change_summary: str = ""
    created_by: str = ""
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=utc_now)
    steps: List["WorkflowStep"] = field(default_factory=list)
    final_output_key: str = ""

    def assert_mutable(self) -> None:
        if self.status == VERSION_STATUS_PUBLISHED:
            raise ValueError("published workflow versions are immutable")

    def add_step(self, step: "WorkflowStep") -> None:
        self.assert_mutable()
        step.workflow_version = self
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow": self.workflow.to_dict(),
            "version_number": self.version_number,
            "status": self.status,
            "change_summary": self.change_summary,
            "created_by": self.created_by,
            "published_at": timestamp(self.published_at),
            "created_at": timestamp(self.created_at),
            "final_output_key": self.final_output_key,
            "steps": [step.to_dict(include_agent=True) for step in self.steps],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkflowVersion":
        workflow = Workflow.from_dict(payload.get("workflow", {}))
        version = cls(
            workflow=workflow,
            version_number=int(payload.get("version_number", 1)),
            status=str(payload.get("status", VERSION_STATUS_DRAFT)),
            change_summary=str(payload.get("change_summary", "")),
            created_by=str(payload.get("created_by", "")),
            published_at=parse_timestamp(payload.get("published_at")),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
            final_output_key=str(payload.get("final_output_key", "")),
        )
        version.steps = [
            WorkflowStep.from_dict(step_payload, workflow_version=version)
            for step_payload in payload.get("steps", [])
        ]
        return version


@dataclass
class AgentDefinition:
    name: str
    slug: str
    description: str = ""
    status: str = WORKFLOW_STATUS_DRAFT
    created_by: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": timestamp(self.created_at),
            "updated_at": timestamp(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AgentDefinition":
        return cls(
            name=str(payload.get("name", "")),
            slug=str(payload.get("slug", "")),
            description=str(payload.get("description", "")),
            status=str(payload.get("status", WORKFLOW_STATUS_DRAFT)),
            created_by=str(payload.get("created_by", "")),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
            updated_at=parse_timestamp(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class AgentVersion:
    agent: AgentDefinition
    version_number: int
    status: str = VERSION_STATUS_DRAFT
    system_prompt: str = ""
    user_prompt_template: str = ""
    input_contract: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    model_configuration: Dict[str, Any] = field(default_factory=dict)
    retry_configuration: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    created_by: str = ""
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=utc_now)
    validators: List[Dict[str, Any]] = field(default_factory=list)
    method_packs: List[Dict[str, Any]] = field(default_factory=list)

    def assert_mutable(self) -> None:
        if self.status == VERSION_STATUS_PUBLISHED:
            raise ValueError("published agent versions are immutable")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent.to_dict(),
            "version_number": self.version_number,
            "status": self.status,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "input_contract": self.input_contract,
            "output_schema": self.output_schema,
            "model_configuration": self.model_configuration,
            "retry_configuration": self.retry_configuration,
            "timeout_seconds": self.timeout_seconds,
            "created_by": self.created_by,
            "published_at": timestamp(self.published_at),
            "created_at": timestamp(self.created_at),
            "validators": self.validators,
            "method_packs": self.method_packs,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AgentVersion":
        return cls(
            agent=AgentDefinition.from_dict(payload.get("agent", {})),
            version_number=int(payload.get("version_number", 1)),
            status=str(payload.get("status", VERSION_STATUS_DRAFT)),
            system_prompt=str(payload.get("system_prompt", "")),
            user_prompt_template=str(payload.get("user_prompt_template", "")),
            input_contract=dict(payload.get("input_contract", {})),
            output_schema=dict(payload.get("output_schema", {})),
            model_configuration=dict(payload.get("model_configuration", {})),
            retry_configuration=dict(payload.get("retry_configuration", {})),
            timeout_seconds=int(payload.get("timeout_seconds", 300) or 300),
            created_by=str(payload.get("created_by", "")),
            published_at=parse_timestamp(payload.get("published_at")),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
            validators=list(payload.get("validators", [])),
            method_packs=list(payload.get("method_packs", [])),
        )


@dataclass
class ModelProvider:
    name: str
    provider_type: str
    base_url: str = ""
    is_active: bool = True
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class ModelDefinition:
    provider: ModelProvider
    name: str
    model_identifier: str
    capabilities: List[str] = field(default_factory=list)
    context_window: int = 0
    supports_structured_output: bool = False
    supports_tool_calls: bool = False
    is_active: bool = True
    default_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    workflow_version: Optional[WorkflowVersion]
    name: str
    step_key: str
    step_type: str
    position: int
    description: str = ""
    is_enabled: bool = True
    agent_version: Optional[AgentVersion] = None
    task_definition: Dict[str, Any] = field(default_factory=dict)
    input_mapping: Dict[str, Any] = field(default_factory=dict)
    output_key: str = ""
    condition_expression: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    failure_strategy: str = FAILURE_STOP_WORKFLOW
    configuration: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_agent: bool = True) -> Dict[str, Any]:
        return {
            "name": self.name,
            "step_key": self.step_key,
            "step_type": self.step_type,
            "position": self.position,
            "description": self.description,
            "is_enabled": self.is_enabled,
            "agent_version": self.agent_version.to_dict() if include_agent and self.agent_version else None,
            "task_definition": self.task_definition,
            "input_mapping": self.input_mapping,
            "output_key": self.output_key,
            "condition_expression": self.condition_expression,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self.retry_policy,
            "failure_strategy": self.failure_strategy,
            "configuration": self.configuration,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Dict[str, Any],
        workflow_version: Optional[WorkflowVersion] = None,
    ) -> "WorkflowStep":
        agent_payload = payload.get("agent_version")
        return cls(
            workflow_version=workflow_version,
            name=str(payload.get("name", "")),
            step_key=str(payload.get("step_key", "")),
            step_type=str(payload.get("step_type", "")),
            position=int(payload.get("position", 0)),
            description=str(payload.get("description", "")),
            is_enabled=bool(payload.get("is_enabled", True)),
            agent_version=AgentVersion.from_dict(agent_payload) if isinstance(agent_payload, dict) else None,
            task_definition=dict(payload.get("task_definition", {})),
            input_mapping=dict(payload.get("input_mapping", {})),
            output_key=str(payload.get("output_key", "")),
            condition_expression=dict(payload.get("condition_expression", {})),
            timeout_seconds=int(payload.get("timeout_seconds", 300) or 300),
            retry_policy=dict(payload.get("retry_policy", {})),
            failure_strategy=str(payload.get("failure_strategy", FAILURE_STOP_WORKFLOW)),
            configuration=dict(payload.get("configuration", {})),
        )


@dataclass
class StepRun:
    workflow_run_id: str
    workflow_step: WorkflowStep
    status: str = STEP_STATUS_PENDING
    attempt_number: int = 0
    resolved_input: Dict[str, Any] = field(default_factory=dict)
    rendered_system_prompt: str = ""
    rendered_user_prompt: str = ""
    raw_output: Any = None
    parsed_output: Any = None
    validated_output: Any = None
    validation_result: Dict[str, Any] = field(default_factory=dict)
    model_metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: str = ""

    def start(self) -> None:
        self.status = STEP_STATUS_RUNNING
        self.started_at = self.started_at or utc_now()
        self.finished_at = None

    def succeed(self) -> None:
        self.status = STEP_STATUS_SUCCEEDED
        self.finished_at = utc_now()

    def fail(self, message: str) -> None:
        self.status = STEP_STATUS_FAILED
        self.error_message = message
        self.finished_at = utc_now()

    def skip(self, message: str = "") -> None:
        self.status = STEP_STATUS_SKIPPED
        self.error_message = message
        self.finished_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_run_id": self.workflow_run_id,
            "workflow_step": self.workflow_step.to_dict(include_agent=False),
            "status": self.status,
            "attempt_number": self.attempt_number,
            "resolved_input": self.resolved_input,
            "rendered_system_prompt": self.rendered_system_prompt,
            "rendered_user_prompt": self.rendered_user_prompt,
            "raw_output": self.raw_output,
            "parsed_output": self.parsed_output,
            "validated_output": self.validated_output,
            "validation_result": self.validation_result,
            "model_metadata": self.model_metadata,
            "started_at": timestamp(self.started_at),
            "finished_at": timestamp(self.finished_at),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Dict[str, Any],
        workflow_version: Optional[WorkflowVersion] = None,
    ) -> "StepRun":
        return cls(
            workflow_run_id=str(payload.get("workflow_run_id", "")),
            workflow_step=WorkflowStep.from_dict(
                payload.get("workflow_step", {}),
                workflow_version=workflow_version,
            ),
            status=str(payload.get("status", STEP_STATUS_PENDING)),
            attempt_number=int(payload.get("attempt_number", 0)),
            resolved_input=dict(payload.get("resolved_input", {})),
            rendered_system_prompt=str(payload.get("rendered_system_prompt", "")),
            rendered_user_prompt=str(payload.get("rendered_user_prompt", "")),
            raw_output=payload.get("raw_output"),
            parsed_output=payload.get("parsed_output"),
            validated_output=payload.get("validated_output"),
            validation_result=dict(payload.get("validation_result", {})),
            model_metadata=dict(payload.get("model_metadata", {})),
            started_at=parse_timestamp(payload.get("started_at")),
            finished_at=parse_timestamp(payload.get("finished_at")),
            error_message=str(payload.get("error_message", "")),
        )


@dataclass
class WorkflowArtifact:
    workflow_run_id: str
    artifact_key: str
    content: Any
    step_run: Optional[StepRun] = None
    artifact_type: str = "json"
    schema_identifier: str = ""
    created_at: datetime = field(default_factory=utc_now)
    is_validated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_run_id": self.workflow_run_id,
            "step_key": self.step_run.workflow_step.step_key if self.step_run else "",
            "artifact_key": self.artifact_key,
            "artifact_type": self.artifact_type,
            "schema_identifier": self.schema_identifier,
            "content": self.content,
            "created_at": timestamp(self.created_at),
            "is_validated": self.is_validated,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Dict[str, Any],
        step_runs: Optional[List[StepRun]] = None,
    ) -> "WorkflowArtifact":
        step_key = str(payload.get("step_key", ""))
        step_run = next(
            (
                item
                for item in step_runs or []
                if item.workflow_step.step_key == step_key
            ),
            None,
        )
        return cls(
            workflow_run_id=str(payload.get("workflow_run_id", "")),
            step_run=step_run,
            artifact_key=str(payload.get("artifact_key", "")),
            artifact_type=str(payload.get("artifact_type", "json")),
            schema_identifier=str(payload.get("schema_identifier", "")),
            content=payload.get("content"),
            created_at=parse_timestamp(payload.get("created_at")) or utc_now(),
            is_validated=bool(payload.get("is_validated", True)),
        )


@dataclass
class WorkflowRun:
    workflow_version: WorkflowVersion
    initial_input: Dict[str, Any]
    id: str = field(default_factory=lambda: uuid4().hex)
    status: str = RUN_STATUS_PENDING
    started_by: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    final_output: Any = None
    error_summary: str = ""
    step_runs: List[StepRun] = field(default_factory=list)
    artifacts: List[WorkflowArtifact] = field(default_factory=list)

    def start(self) -> None:
        self.status = RUN_STATUS_RUNNING
        self.started_at = self.started_at or utc_now()

    def succeed(self, final_output: Any) -> None:
        self.status = RUN_STATUS_SUCCEEDED
        self.final_output = final_output
        self.finished_at = utc_now()

    def fail(self, message: str) -> None:
        self.status = RUN_STATUS_FAILED
        self.error_summary = message
        self.finished_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_version": self.workflow_version.to_dict(),
            "initial_input": self.initial_input,
            "status": self.status,
            "started_by": self.started_by,
            "started_at": timestamp(self.started_at),
            "finished_at": timestamp(self.finished_at),
            "final_output": self.final_output,
            "error_summary": self.error_summary,
            "step_runs": [step_run.to_dict() for step_run in self.step_runs],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkflowRun":
        workflow_version = WorkflowVersion.from_dict(payload.get("workflow_version", {}))
        run = cls(
            workflow_version=workflow_version,
            initial_input=dict(payload.get("initial_input", {})),
            id=str(payload.get("id", "")),
            status=str(payload.get("status", RUN_STATUS_PENDING)),
            started_by=str(payload.get("started_by", "")),
            started_at=parse_timestamp(payload.get("started_at")),
            finished_at=parse_timestamp(payload.get("finished_at")),
            final_output=payload.get("final_output"),
            error_summary=str(payload.get("error_summary", "")),
        )
        run.step_runs = [
            StepRun.from_dict(step_payload, workflow_version=workflow_version)
            for step_payload in payload.get("step_runs", [])
        ]
        run.artifacts = [
            WorkflowArtifact.from_dict(artifact_payload, step_runs=run.step_runs)
            for artifact_payload in payload.get("artifacts", [])
        ]
        return run


def timestamp(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
