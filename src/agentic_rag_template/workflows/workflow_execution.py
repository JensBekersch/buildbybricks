"""Linear workflow execution engine."""

import json
from typing import Any, Dict, List, Optional

from agentic_rag_template.workflows.input_resolution import InputResolver
from agentic_rag_template.workflows.models import (
    FAILURE_CONTINUE_WITH_WARNING,
    FAILURE_STOP_WORKFLOW,
    RUN_STATUS_SUCCEEDED,
    STEP_STATUS_FAILED,
    STEP_TYPE_AGENT,
    STEP_TYPE_ARTIFACT,
    STEP_TYPE_TASK,
    STEP_TYPE_TRANSFORMATION,
    STEP_TYPE_VALIDATION,
    StepRun,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowVersion,
)
from agentic_rag_template.workflows.prompt_builder import PromptBuilder
from agentic_rag_template.workflows.providers import LLMProviderAdapter, WorkflowLLMRequest
from agentic_rag_template.workflows.tasks import TaskContext, TaskRegistry
from agentic_rag_template.workflows.validators import (
    ValidationContext,
    ValidationResult,
    ValidatorRegistry,
)


class WorkflowExecutionError(RuntimeError):
    """Raised when a workflow run cannot continue."""


class LinearWorkflowEngine:
    def __init__(
        self,
        provider_adapter: Optional[LLMProviderAdapter] = None,
        task_registry: Optional[TaskRegistry] = None,
        validator_registry: Optional[ValidatorRegistry] = None,
        input_resolver: Optional[InputResolver] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self.provider_adapter = provider_adapter
        self.task_registry = task_registry or TaskRegistry.defaults()
        self.validator_registry = validator_registry or ValidatorRegistry.defaults()
        self.input_resolver = input_resolver or InputResolver()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def run(self, workflow_version: WorkflowVersion, initial_input: Dict[str, Any]) -> WorkflowRun:
        workflow_run = WorkflowRun(workflow_version=workflow_version, initial_input=initial_input)
        workflow_run.start()

        try:
            for step in sorted(workflow_version.steps, key=lambda item: item.position):
                step_run = StepRun(workflow_run_id=workflow_run.id, workflow_step=step)
                workflow_run.step_runs.append(step_run)
                if not step.is_enabled:
                    step_run.skip("step is disabled")
                    continue
                if step.condition_expression and not _evaluate_condition(step.condition_expression, workflow_run):
                    step_run.skip("condition evaluated to false")
                    continue
                self._execute_with_retries(workflow_run, step_run)
                if step_run.status == STEP_STATUS_FAILED and step.failure_strategy != FAILURE_CONTINUE_WITH_WARNING:
                    raise WorkflowExecutionError(step_run.error_message)

            final_output = self._final_output(workflow_run)
            workflow_run.succeed(final_output)
        except Exception as error:
            workflow_run.fail(str(error))

        return workflow_run

    def _execute_with_retries(self, workflow_run: WorkflowRun, step_run: StepRun) -> None:
        max_attempts = int(step_run.workflow_step.retry_policy.get("max_attempts", 1) or 1)
        for attempt in range(1, max_attempts + 1):
            step_run.attempt_number = attempt
            step_run.start()
            try:
                self._execute_once(workflow_run, step_run)
                step_run.succeed()
                return
            except Exception as error:
                step_run.fail(str(error))
                if attempt >= max_attempts:
                    if step_run.workflow_step.failure_strategy == FAILURE_CONTINUE_WITH_WARNING:
                        return
                    raise

    def _execute_once(self, workflow_run: WorkflowRun, step_run: StepRun) -> None:
        step = step_run.workflow_step
        resolved_input = self.input_resolver.resolve(step.input_mapping, workflow_run)
        step_run.resolved_input = resolved_input
        self._validate_required_inputs(step, resolved_input)

        if step.step_type == STEP_TYPE_AGENT:
            output = self._execute_agent(step_run, resolved_input)
        elif step.step_type in {STEP_TYPE_TASK, STEP_TYPE_TRANSFORMATION, STEP_TYPE_ARTIFACT}:
            output = self._execute_task(step_run, resolved_input)
        elif step.step_type == STEP_TYPE_VALIDATION:
            output = resolved_input
        else:
            raise WorkflowExecutionError(f"unsupported step type: {step.step_type}")

        step_run.raw_output = output
        step_run.parsed_output = _parse_json_if_needed(output)
        validation_results = self._validate_output(step_run, step_run.parsed_output)
        step_run.validation_result = {
            "valid": all(result.valid or result.severity != "error" for result in validation_results),
            "results": [result.to_dict() for result in validation_results],
        }
        if not step_run.validation_result["valid"]:
            raise WorkflowExecutionError("step output validation failed")
        step_run.validated_output = step_run.parsed_output
        self._save_artifact(workflow_run, step_run)

    def _execute_agent(self, step_run: StepRun, resolved_input: Dict[str, Any]) -> Any:
        if self.provider_adapter is None:
            raise WorkflowExecutionError("provider adapter is required for agent steps")
        agent_version = step_run.workflow_step.agent_version
        if agent_version is None:
            raise WorkflowExecutionError("agent_version is required")
        prompts = self.prompt_builder.build(agent_version, resolved_input)
        step_run.rendered_system_prompt = prompts["system_prompt"]
        step_run.rendered_user_prompt = prompts["user_prompt"]
        model_configuration = agent_version.model_configuration
        response = self.provider_adapter.invoke(
            WorkflowLLMRequest(
                system_prompt=step_run.rendered_system_prompt,
                user_prompt=step_run.rendered_user_prompt,
                provider=str(model_configuration.get("provider", "")),
                model=str(model_configuration.get("model", "")),
                parameters=dict(model_configuration.get("parameters", {})),
                response_format=str(model_configuration.get("response_format", "json")),
            )
        )
        step_run.model_metadata = response.metadata
        return response.parsed_output if response.parsed_output is not None else response.raw_output

    def _execute_task(self, step_run: StepRun, resolved_input: Dict[str, Any]) -> Any:
        task_definition = step_run.workflow_step.task_definition
        task = self.task_registry.get(str(task_definition.get("task_type", "")))
        return task.execute(
            TaskContext(
                input=resolved_input,
                configuration=dict(task_definition.get("configuration", {})),
            )
        )

    def _validate_required_inputs(self, step: Any, resolved_input: Dict[str, Any]) -> None:
        required = []
        if step.agent_version is not None:
            required = step.agent_version.input_contract.get("required", [])
        required.extend(step.configuration.get("required_inputs", []))
        missing = [item for item in required if item not in resolved_input or resolved_input[item] is None]
        if missing:
            raise WorkflowExecutionError(f"missing required input(s): {', '.join(missing)}")

    def _validate_output(self, step_run: StepRun, value: Any) -> List[ValidationResult]:
        validators = []
        step = step_run.workflow_step
        if step.agent_version and step.agent_version.output_schema:
            validators.append({"validator": "json_schema", "configuration": {"schema": step.agent_version.output_schema}})
        if step.agent_version:
            validators.extend(step.agent_version.validators)
        validators.extend(step.configuration.get("validators", []))
        results = []
        for definition in validators:
            validator_id = definition.get("validator") or definition.get("validator_id")
            validator = self.validator_registry.get(str(validator_id))
            results.append(
                validator.validate(
                    value,
                    ValidationContext(
                        initial_input=step_run.resolved_input,
                        configuration=dict(definition.get("configuration", {})),
                    ),
                )
            )
        return results

    def _save_artifact(self, workflow_run: WorkflowRun, step_run: StepRun) -> None:
        step = step_run.workflow_step
        artifact_key = step.output_key or step.step_key
        workflow_run.artifacts.append(
            WorkflowArtifact(
                workflow_run_id=workflow_run.id,
                step_run=step_run,
                artifact_key=artifact_key,
                artifact_type=str(step.configuration.get("artifact_type", "json")),
                schema_identifier=str(step.configuration.get("schema_identifier", "")),
                content=step_run.validated_output,
                is_validated=True,
            )
        )

    def _final_output(self, workflow_run: WorkflowRun) -> Any:
        final_key = workflow_run.workflow_version.final_output_key
        if final_key:
            artifact = next((item for item in workflow_run.artifacts if item.artifact_key == final_key), None)
            if artifact is not None:
                return artifact.content
        if workflow_run.artifacts:
            return workflow_run.artifacts[-1].content
        return None


def _parse_json_if_needed(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return value


def _evaluate_condition(condition: Dict[str, Any], workflow_run: WorkflowRun) -> bool:
    if "all" in condition:
        return all(_evaluate_condition(item, workflow_run) for item in condition.get("all", []))
    value = _resolve_condition_path(str(condition.get("path", "")), workflow_run)
    operator = condition.get("operator")
    expected = condition.get("value")
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "exists":
        return value is not None
    if operator == "not_exists":
        return value is None
    if operator == "contains":
        return expected in value if isinstance(value, (list, str)) else False
    if operator == "in":
        return value in expected if isinstance(expected, list) else False
    if operator == "greater_than":
        return value > expected
    if operator == "less_than":
        return value < expected
    return False


def _resolve_condition_path(path: str, workflow_run: WorkflowRun) -> Any:
    payload = {
        "workflow": {"status": workflow_run.status},
        "steps": {
            step_run.workflow_step.step_key: {
                "status": step_run.status,
                "validated_output": step_run.validated_output,
            }
            for step_run in workflow_run.step_runs
        },
    }
    current: Any = payload
    for part in path.split("."):
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
