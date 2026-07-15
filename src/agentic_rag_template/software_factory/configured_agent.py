"""Generic YAML-configured software factory agent runtime."""

from dataclasses import dataclass
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from agentic_rag_template.applications import ApplicationInstance
from agentic_rag_template.llm.models import LLMProvider
from agentic_rag_template.software_factory.jobs import (
    EVENT_LOG,
    ArchitectureGenerationEvent,
)


ArchitectureGenerationEventHandler = Callable[[ArchitectureGenerationEvent], None]


class ConfiguredAgentError(RuntimeError):
    """Raised when a configured agent cannot be loaded or executed."""


@dataclass(frozen=True)
class ConfiguredAgent:
    """An agent whose behavior is defined by a YAML configuration."""

    config: Dict[str, Any]
    config_path: Optional[Path] = None

    @classmethod
    def load(cls, application: ApplicationInstance, agent_id: str) -> "ConfiguredAgent":
        config_path = application.template_dir / "agents" / f"{agent_id}.yaml"

        if not config_path.is_file():
            return cls(config={}, config_path=config_path)

        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ConfiguredAgentError(f"Agent config must be a YAML object: {config_path}")
        return cls(config=payload, config_path=config_path)

    @property
    def id(self) -> str:
        return _string_value(self.config.get("id")) or "configured_agent"

    @property
    def name(self) -> str:
        return _string_value(self.config.get("name")) or self.id

    @property
    def version(self) -> Any:
        return self.config.get("version", "")

    def summary(self) -> Dict[str, Any]:
        if not self.config:
            return {}
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
        }

    def run_json(
        self,
        llm_provider: LLMProvider,
        context: Dict[str, Any],
        event_handler: Optional[ArchitectureGenerationEventHandler],
        step: str,
        llm_step: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._validate_input_contract(context)
        generate_json = getattr(llm_provider, "generate_json", None)
        if not callable(generate_json):
            raise ConfiguredAgentError(
                f"LLM provider '{getattr(llm_provider, 'name', 'none')}' does not support structured JSON generation."
            )

        return self._call_generate_json_with_metrics(
            generate_json=generate_json,
            llm_provider=llm_provider,
            event_handler=event_handler,
            step=step,
            llm_step=llm_step or self.id,
            system_prompt=self.build_system_prompt(),
            user_prompt=self.build_user_prompt(context),
        )

    def build_system_prompt(self) -> str:
        configured_prompt = _string_value((self.config.get("prompt") or {}).get("system"))
        lines = configured_prompt.splitlines() if configured_prompt else [
            f"Du bist {self.name} einer agentischen Softwarefabrik.",
            "Erzeuge ausschliesslich valides JSON.",
            "Schreibe fachliche Inhalte in der Sprache der Nutzerbeschreibung.",
        ]

        if self.config:
            lines.extend(
                [
                    "",
                    f"Agent-Konfiguration: {self.id} v{self.version or '-'}",
                    "Output-Contract:",
                    json.dumps(self._output_contract(), ensure_ascii=True),
                    "Review-Regeln:",
                    json.dumps(self.config.get("review_rules", []), ensure_ascii=True),
                    "Normalisierung:",
                    json.dumps(self.config.get("normalization", {}), ensure_ascii=True),
                ]
            )

        return "\n".join(line for line in lines if line is not None)

    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        configured_template = _string_value((self.config.get("prompt") or {}).get("user_template"))
        prompt_context = {
            **context,
            "agent_config": {
                "output_contract": self._output_contract(),
                "output_schema": self.config.get("output_schema", {}),
                "review_rules": self.config.get("review_rules", []),
                "normalization": self.config.get("normalization", {}),
                "quality_gate": self.config.get("quality_gate", {}),
            },
        }
        if configured_template:
            prompt = self._render_conditionals(configured_template, prompt_context)
            for key, value in prompt_context.items():
                rendered_value = _render_prompt_value(value)
                prompt = prompt.replace("{{ " + key + " }}", rendered_value)
                prompt = prompt.replace("{{" + key + "}}", rendered_value)
            return prompt

        return "\n\n".join(
            [
                f"{key}:\n{_render_prompt_value(value)}"
                for key, value in prompt_context.items()
            ]
        )

    def _validate_input_contract(self, context: Dict[str, Any]) -> None:
        required_inputs = (self.config.get("input_contract") or {}).get("required", [])
        missing = [
            _string_value(item)
            for item in required_inputs
            if _string_value(item) and _string_value(item) not in context
        ]
        if missing:
            raise ConfiguredAgentError(
                f"Configured agent '{self.id}' is missing required input(s): {', '.join(missing)}"
            )

    def _output_contract(self) -> Dict[str, Any]:
        return self.config.get("output_contract") or self.config.get("output_schema") or {}

    def _render_conditionals(self, template: str, context: Dict[str, Any]) -> str:
        def replace(match: re.Match) -> str:
            key = match.group("key").strip()
            body = match.group("body")
            return body if context.get(key) else ""

        return re.sub(
            r"{%\s*if\s+(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)\s*%}(?P<body>.*?){%\s*endif\s*%}",
            replace,
            template,
            flags=re.DOTALL,
        )

    def _call_generate_json_with_metrics(
        self,
        generate_json: Callable[..., Dict[str, Any]],
        llm_provider: LLMProvider,
        event_handler: Optional[ArchitectureGenerationEventHandler],
        step: str,
        llm_step: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        metadata = {
            "kind": "llm_call",
            "llm_step": llm_step,
            "provider": getattr(llm_provider, "name", "none"),
            "model": getattr(llm_provider, "model", "none"),
        }

        try:
            result = generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as error:
            duration_seconds = time.perf_counter() - started_at
            _emit_log(
                event_handler,
                step,
                f"LLM call failed: {error}",
                level="error",
                metadata={
                    **metadata,
                    "status": "failed",
                    "duration_seconds": round(duration_seconds, 6),
                    "error": str(error),
                },
            )
            raise

        duration_seconds = time.perf_counter() - started_at
        _emit_log(
            event_handler,
            step,
            "LLM call completed.",
            metadata={
                **metadata,
                "status": "completed",
                "duration_seconds": round(duration_seconds, 6),
            },
        )

        if not isinstance(result, dict):
            raise ConfiguredAgentError(f"Configured agent '{self.id}' did not return a JSON object.")
        return result


def _emit_log(
    event_handler: Optional[ArchitectureGenerationEventHandler],
    step: str,
    message: str,
    level: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if event_handler is None:
        return
    event_handler(
        ArchitectureGenerationEvent(
            type=EVENT_LOG,
            step=step,
            message=message,
            level=level,
            metadata=metadata or {},
        )
    )


def _render_prompt_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
