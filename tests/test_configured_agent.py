from pathlib import Path

import pytest

from agentic_rag_template.applications import FileApplicationRegistry
from agentic_rag_template.config import Settings
from agentic_rag_template.software_factory.configured_agent import (
    ConfiguredAgent,
    ConfiguredAgentError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class JsonProvider:
    name = "test-provider"
    model = "test-model"

    def __init__(self) -> None:
        self.prompts = []

    def generate_json(self, system_prompt: str, user_prompt: str):
        self.prompts.append((system_prompt, user_prompt))
        return {"ok": True}


def _software_factory_application():
    settings = Settings(
        apps_dir=PROJECT_ROOT / "apps",
        data_dir=PROJECT_ROOT / "data",
        template_dir=PROJECT_ROOT / "template",
    )
    return FileApplicationRegistry(settings).get("software-factory")


def test_configured_agent_loads_yaml_and_renders_prompt_context() -> None:
    agent = ConfiguredAgent.load(_software_factory_application(), "requirement_analyst")

    assert agent.summary() == {
        "id": "requirement_analyst",
        "name": "Requirement Analyst",
        "version": 2,
    }
    system_prompt = agent.build_system_prompt()
    user_prompt = agent.build_user_prompt(
        {
            "user_description": "Eine Todo-Liste fuer Teams.",
            "method_sources": [{"title": "arc42", "location": "architecture-method/arc42_sections.json"}],
        }
    )

    assert "verlustarmer Requirements Parser" in system_prompt
    assert "preserve_explicit_test_cases" in system_prompt
    assert "Output-Contract" in system_prompt
    assert "domain_entities" in system_prompt
    assert "Eine Todo-Liste fuer Teams." in user_prompt
    assert "architecture-method/arc42_sections.json" in user_prompt


def test_configured_agent_runs_json_provider_and_emits_llm_metrics() -> None:
    agent = ConfiguredAgent.load(_software_factory_application(), "requirement_analyst")
    provider = JsonProvider()
    events = []

    result = agent.run_json(
        llm_provider=provider,
        context={
            "user_description": "Eine Todo-Liste fuer Teams.",
            "method_sources": [],
        },
        event_handler=events.append,
        step="analyze_requirements",
        llm_step="requirement_analyst",
    )

    assert result == {"ok": True}
    assert provider.prompts
    assert events[0].metadata["kind"] == "llm_call"
    assert events[0].metadata["llm_step"] == "requirement_analyst"
    assert events[0].metadata["status"] == "completed"


def test_configured_agent_renders_optional_template_blocks() -> None:
    agent = ConfiguredAgent.load(_software_factory_application(), "requirement_analyst")

    user_prompt = agent.build_user_prompt(
        {
            "user_description": "Eine Todo-Liste fuer Teams.",
            "method_sources": [],
        }
    )

    assert "Eine Todo-Liste fuer Teams." in user_prompt
    assert "{% if method_sources %}" not in user_prompt
    assert "{{ method_sources }}" not in user_prompt
    assert "Methodenhinweise:" not in user_prompt


def test_configured_agent_validates_required_inputs() -> None:
    agent = ConfiguredAgent.load(_software_factory_application(), "requirement_analyst")

    with pytest.raises(ConfiguredAgentError, match="user_description"):
        agent.run_json(
            llm_provider=JsonProvider(),
            context={"method_sources": []},
            event_handler=None,
            step="analyze_requirements",
        )
