import json
from pathlib import Path

from agentic_rag_template.applications import FileApplicationRegistry
from agentic_rag_template.config import Settings


def test_file_application_registry_lists_default_and_configured_apps(tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    apps_dir = tmp_path / "apps"
    data_dir = tmp_path / "data"
    app_dir = apps_dir / "policy-assistant"
    template_dir.mkdir()
    app_dir.mkdir(parents=True)
    data_dir.mkdir()
    (template_dir / "app_profile.json").write_text(
        json.dumps({"name": "Default Assistant"}),
        encoding="utf-8",
    )
    (app_dir / "app_profile.json").write_text(
        json.dumps(
            {
                "name": "Policy Assistant",
                "description": "Answers from policy documents.",
                "default_collection": "policies",
                "default_top_k": 2,
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(template_dir=template_dir, apps_dir=apps_dir, data_dir=data_dir)

    registry = FileApplicationRegistry(settings)
    applications = registry.list()
    policy_app = registry.get("policy-assistant")

    assert [application.id for application in applications] == ["default", "policy-assistant"]
    assert applications[0].profile.name == "Default Assistant"
    assert policy_app.profile.name == "Policy Assistant"
    assert policy_app.profile.default_collection == "policies"
    assert policy_app.data_dir == data_dir / "policy-assistant"


def test_file_application_registry_rejects_unknown_apps(tmp_path: Path) -> None:
    registry = FileApplicationRegistry(Settings(apps_dir=tmp_path / "apps"))

    try:
        registry.get("missing")
    except KeyError as error:
        assert "missing" in str(error)
    else:
        raise AssertionError("Expected missing app to raise KeyError")
