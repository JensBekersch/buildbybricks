import pytest

from agentic_rag_template.workflows.models import (
    FAILURE_CONTINUE_WITH_WARNING,
    RUN_STATUS_FAILED,
    RUN_STATUS_SUCCEEDED,
    STEP_STATUS_FAILED,
    STEP_STATUS_SKIPPED,
    STEP_STATUS_SUCCEEDED,
    STEP_TYPE_AGENT,
    STEP_TYPE_TASK,
    VERSION_STATUS_PUBLISHED,
    AgentDefinition,
    AgentVersion,
    Workflow,
    WorkflowStep,
    WorkflowVersion,
)
from agentic_rag_template.workflows.providers import FakeLLMProviderAdapter, LLMProviderWorkflowAdapter
from agentic_rag_template.workflows.workflow_execution import LinearWorkflowEngine
from agentic_rag_template.workflows.workflow_validation import WorkflowVersionValidator


def _workflow_version() -> WorkflowVersion:
    return WorkflowVersion(
        workflow=Workflow(name="Django Machine", slug="django-machine"),
        version_number=1,
        final_output_key="final",
    )


def _published_agent(output_schema=None, required_inputs=None, validators=None) -> AgentVersion:
    agent = AgentDefinition(name="Generic Agent", slug="generic-agent")
    return AgentVersion(
        agent=agent,
        version_number=1,
        status=VERSION_STATUS_PUBLISHED,
        system_prompt="Du bist ein generischer Agent.",
        user_prompt_template="Input: {{ description }}",
        input_contract={"required": required_inputs or ["description"]},
        output_schema=output_schema or {},
        model_configuration={"provider": "fake", "model": "fake-json"},
        validators=validators or [],
    )


class StructuredProvider:
    name = "ollama"
    model = "qwen3:14b"

    def __init__(self, output=None) -> None:
        self.output = output or {"artifact_name": "Team Todo"}
        self.calls = []

    def generate_json(self, system_prompt, user_prompt):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.output


class AnswerOnlyProvider:
    name = "deterministic"
    model = "local"


def test_workflow_version_validates_unique_step_keys_and_requires_steps() -> None:
    version = _workflow_version()
    validator = WorkflowVersionValidator()

    result = validator.validate(version)

    assert result.valid is False
    assert "workflow version must contain at least one enabled step" in result.errors

    version.add_step(
        WorkflowStep(version, "One", "duplicate", STEP_TYPE_TASK, 1, task_definition={"task_type": "echo"})
    )
    version.add_step(
        WorkflowStep(version, "Two", "duplicate", STEP_TYPE_TASK, 2, task_definition={"task_type": "echo"})
    )

    result = validator.validate(version)

    assert result.valid is False
    assert "step_key must be unique within a workflow version" in result.errors


def test_workflow_version_publish_rejects_unpublished_agent_and_freezes_version() -> None:
    version = _workflow_version()
    agent_version = _published_agent()
    agent_version.status = "draft"
    version.add_step(
        WorkflowStep(
            version,
            "Analyse",
            "analysis",
            STEP_TYPE_AGENT,
            1,
            agent_version=agent_version,
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="analysis",
        )
    )

    result = WorkflowVersionValidator().publish(version)

    assert result.valid is False
    assert "analysis: agent_version must be published" in result.errors

    agent_version.status = VERSION_STATUS_PUBLISHED
    result = WorkflowVersionValidator().publish(version)

    assert result.valid is True
    assert version.status == VERSION_STATUS_PUBLISHED
    with pytest.raises(ValueError, match="immutable"):
        version.add_step(
            WorkflowStep(version, "Other", "other", STEP_TYPE_TASK, 2, task_definition={"task_type": "echo"})
        )


def test_linear_workflow_runs_agent_and_task_in_order_with_step_output_mapping() -> None:
    version = _workflow_version()
    schema = {
        "type": "object",
        "required": ["artifact_name"],
        "additionalProperties": False,
        "properties": {"artifact_name": {"type": "string"}},
    }
    version.add_step(
        WorkflowStep(
            version,
            "Requirement Agent",
            "requirement_analysis",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(output_schema=schema),
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="requirements",
        )
    )
    version.add_step(
        WorkflowStep(
            version,
            "Final Mapping",
            "final_mapping",
            STEP_TYPE_TASK,
            2,
            task_definition={"task_type": "field_mapping", "configuration": {"mapping": {"title": "requirements.artifact_name"}}},
            input_mapping={"requirements": {"source": "step_output", "step_key": "requirement_analysis", "path": "validated_output"}},
            output_key="final",
        )
    )

    run = LinearWorkflowEngine(
        provider_adapter=FakeLLMProviderAdapter(
            [{"parsed_output": {"artifact_name": "Team Todo"}}]
        )
    ).run(version, {"description": "Eine Todo-Liste fuer Teams."})

    assert run.status == RUN_STATUS_SUCCEEDED
    assert [step.status for step in run.step_runs] == [STEP_STATUS_SUCCEEDED, STEP_STATUS_SUCCEEDED]
    assert run.final_output == {"title": "Team Todo"}
    assert [artifact.artifact_key for artifact in run.artifacts] == ["requirements", "final"]
    assert run.step_runs[0].rendered_system_prompt
    assert run.step_runs[0].model_metadata["provider"] == "fake"


def test_productive_llm_provider_adapter_runs_structured_agent_step() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Requirement Agent",
            "requirement_analysis",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(),
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="final",
        )
    )
    provider = StructuredProvider()

    run = LinearWorkflowEngine(provider_adapter=LLMProviderWorkflowAdapter(provider)).run(
        version,
        {"description": "Eine Todo-Liste fuer Teams."},
    )

    assert run.status == RUN_STATUS_SUCCEEDED
    assert run.final_output == {"artifact_name": "Team Todo"}
    assert provider.calls == [
        {
            "system_prompt": "Du bist ein generischer Agent.\n\nOutput-Schema:\n\n{}",
            "user_prompt": "Input: Eine Todo-Liste fuer Teams.",
        }
    ]
    assert run.step_runs[0].raw_output == {"artifact_name": "Team Todo"}
    assert run.step_runs[0].model_metadata == {
        "provider": "ollama",
        "model": "qwen3:14b",
        "requested_provider": "fake",
        "requested_model": "fake-json",
    }


def test_productive_llm_provider_adapter_requires_structured_generation() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Requirement Agent",
            "requirement_analysis",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(),
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="final",
        )
    )

    run = LinearWorkflowEngine(provider_adapter=LLMProviderWorkflowAdapter(AnswerOnlyProvider())).run(
        version,
        {"description": "Eine Todo-Liste fuer Teams."},
    )

    assert run.status == RUN_STATUS_FAILED
    assert "does not support structured JSON generation" in run.error_summary


def test_agent_configured_scope_evidence_validator_rejects_unsupported_terms() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Architecture Synthesizer",
            "synthesize_architecture",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(
                validators=[
                    {
                        "validator": "scope_evidence",
                        "configuration": {
                            "requirement_analysis_path": "requirement_analysis",
                            "watched_terms": ["Projektmanagement", "Cloud"],
                        },
                    }
                ]
            ),
            input_mapping={
                "description": {"source": "workflow_input", "path": "description"},
                "requirement_analysis": {
                    "source": "static",
                    "value": {
                        "input_summary": "Eine einfache Todo-Liste fuer Teams.",
                        "in_scope": [{"description": "Aufgaben erfassen und Status pflegen."}],
                        "out_of_scope": [{"description": "Keine Integration in Projektmanagement-Tools."}],
                        "not_evidenced": [],
                    },
                },
            },
            output_key="final",
        )
    )
    provider = StructuredProvider(
        {
            "artifact_name": "Team Todo",
            "context": "Die Anwendung bietet eine Projektmanagement-Integration.",
        }
    )

    run = LinearWorkflowEngine(provider_adapter=LLMProviderWorkflowAdapter(provider)).run(
        version,
        {"description": "Eine Todo-Liste fuer Teams."},
    )

    assert run.status == RUN_STATUS_FAILED
    assert "step output validation failed" in run.error_summary
    assert run.step_runs[0].validation_result["valid"] is False
    assert run.step_runs[0].validation_result["results"][0]["validator_id"] == "scope_evidence"
    assert "Projektmanagement" in run.step_runs[0].validation_result["results"][0]["errors"][0]


def test_agent_configured_scope_evidence_validator_allows_supported_terms() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Architecture Synthesizer",
            "synthesize_architecture",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(
                validators=[
                    {
                        "validator": "scope_evidence",
                        "configuration": {
                            "requirement_analysis_path": "requirement_analysis",
                            "watched_terms": ["REST API"],
                        },
                    }
                ]
            ),
            input_mapping={
                "description": {"source": "workflow_input", "path": "description"},
                "requirement_analysis": {
                    "source": "static",
                    "value": {
                        "input_summary": "Eine Todo-Liste mit REST API.",
                        "in_scope": [{"description": "REST API fuer externe Clients."}],
                        "out_of_scope": [],
                        "not_evidenced": [],
                    },
                },
            },
            output_key="final",
        )
    )
    provider = StructuredProvider(
        {
            "artifact_name": "Team Todo",
            "context": "Die REST API stellt Aufgaben fuer externe Clients bereit.",
        }
    )

    run = LinearWorkflowEngine(provider_adapter=LLMProviderWorkflowAdapter(provider)).run(
        version,
        {"description": "Eine Todo-Liste mit REST API."},
    )

    assert run.status == RUN_STATUS_SUCCEEDED
    assert run.final_output["context"] == "Die REST API stellt Aufgaben fuer externe Clients bereit."


def test_disabled_and_conditioned_steps_are_skipped() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Disabled",
            "disabled",
            STEP_TYPE_TASK,
            1,
            is_enabled=False,
            task_definition={"task_type": "echo"},
            output_key="disabled",
        )
    )
    version.add_step(
        WorkflowStep(
            version,
            "Conditioned",
            "conditioned",
            STEP_TYPE_TASK,
            2,
            task_definition={"task_type": "echo"},
            condition_expression={"path": "workflow.status", "operator": "equals", "value": "not-running"},
            output_key="conditioned",
        )
    )

    run = LinearWorkflowEngine().run(version, {"description": "x"})

    assert run.status == RUN_STATUS_SUCCEEDED
    assert [step.status for step in run.step_runs] == [STEP_STATUS_SKIPPED, STEP_STATUS_SKIPPED]
    assert run.artifacts == []


def test_missing_required_input_fails_before_provider_call() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Agent",
            "agent",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(required_inputs=["description"]),
            input_mapping={},
            output_key="agent",
        )
    )
    provider = FakeLLMProviderAdapter([{"parsed_output": {"ok": True}}])

    run = LinearWorkflowEngine(provider_adapter=provider).run(version, {"description": "x"})

    assert run.status == RUN_STATUS_FAILED
    assert "missing required input" in run.error_summary
    assert provider.requests == []


def test_failed_required_validator_stops_workflow() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Strict Task",
            "strict",
            STEP_TYPE_TASK,
            1,
            task_definition={"task_type": "echo"},
            input_mapping={"name": {"source": "static", "value": "x"}},
            output_key="strict",
            configuration={
                "validators": [
                    {"validator": "required_fields", "configuration": {"required": ["missing"]}},
                ]
            },
        )
    )

    run = LinearWorkflowEngine().run(version, {})

    assert run.status == RUN_STATUS_FAILED
    assert run.step_runs[0].status == STEP_STATUS_FAILED
    assert run.step_runs[0].validation_result["valid"] is False
    assert run.artifacts == []


def test_retry_policy_retries_provider_failures() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Agent",
            "agent",
            STEP_TYPE_AGENT,
            1,
            agent_version=_published_agent(),
            input_mapping={"description": {"source": "workflow_input", "path": "description"}},
            output_key="agent",
            retry_policy={"max_attempts": 2},
        )
    )
    provider = FakeLLMProviderAdapter(
        [
            RuntimeError("temporary model error"),
            {"parsed_output": {"ok": True}},
        ]
    )

    run = LinearWorkflowEngine(provider_adapter=provider).run(version, {"description": "x"})

    assert run.status == RUN_STATUS_SUCCEEDED
    assert run.step_runs[0].attempt_number == 2
    assert len(provider.requests) == 2


def test_continue_with_warning_keeps_workflow_running_after_step_failure() -> None:
    version = _workflow_version()
    version.add_step(
        WorkflowStep(
            version,
            "Warn",
            "warn",
            STEP_TYPE_TASK,
            1,
            task_definition={"task_type": "unknown"},
            failure_strategy=FAILURE_CONTINUE_WITH_WARNING,
            output_key="warn",
        )
    )
    version.add_step(
        WorkflowStep(
            version,
            "Final",
            "final",
            STEP_TYPE_TASK,
            2,
            task_definition={"task_type": "echo"},
            input_mapping={"value": {"source": "static", "value": "ok"}},
            output_key="final",
        )
    )

    run = LinearWorkflowEngine().run(version, {})

    assert run.status == RUN_STATUS_SUCCEEDED
    assert [step.status for step in run.step_runs] == [STEP_STATUS_FAILED, STEP_STATUS_SUCCEEDED]
    assert run.final_output == {"value": "ok"}
