import json
from pathlib import Path

from agentic_rag_template.evaluation import load_evaluation_cases
from agentic_rag_template.template_config import load_application_profile


def test_load_application_profile_from_template_json(tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "app_profile.json").write_text(
        json.dumps(
            {
                "name": "Policy Assistant",
                "description": "Answers from policy docs.",
                "default_collection": "policies",
                "default_top_k": 4,
                "answer_policy": "Use policy sources only.",
                "enabled_tools": ["search_knowledge_base"],
            }
        ),
        encoding="utf-8",
    )

    profile = load_application_profile(template_dir)

    assert profile.name == "Policy Assistant"
    assert profile.default_collection == "policies"
    assert profile.default_top_k == 4
    assert profile.enabled_tools == ["search_knowledge_base"]


def test_load_evaluation_cases_from_template_json(tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "evaluation_cases.json").write_text(
        json.dumps(
            [
                {
                    "id": "policy-case",
                    "question": "What is the policy?",
                    "collection": "policies",
                    "expected_source_locations": ["policies/policy.md"],
                    "required_answer_terms": ["Quellen"],
                    "required_tool_calls": ["search_knowledge_base"],
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_evaluation_cases(template_dir)

    assert len(cases) == 1
    assert cases[0].id == "policy-case"
    assert cases[0].collection == "policies"
    assert cases[0].expected_source_locations == ["policies/policy.md"]
