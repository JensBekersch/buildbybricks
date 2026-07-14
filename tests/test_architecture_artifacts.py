import json
from pathlib import Path

from agentic_rag_template.applications.models import ApplicationInstance
from agentic_rag_template.software_factory import ArchitectureGenerationJob, FileArchitectureArtifactStore
from agentic_rag_template.template_config.models import ApplicationProfile


def test_file_architecture_artifact_store_writes_json_and_markdown(tmp_path: Path) -> None:
    application = ApplicationInstance(
        id="software-factory",
        profile=ApplicationProfile(name="Software Factory"),
        template_dir=tmp_path / "apps" / "software-factory",
        data_dir=tmp_path / "data" / "software-factory",
    )
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic",
        job_id="job-1",
    )
    result = {
        "architecture_sheet": {
            "artifact_name": "Team Todo",
            "business_goal": "Aufgaben im Team sichtbar machen.",
            "building_blocks": [{"name": "Aufgabe", "responsibility": "Speichert Aufgaben."}],
        },
        "schema_id": "software-factory.architecture-sheet.v1",
        "validation": {"valid": True},
        "generation": {"llm_provider": "ollama"},
    }

    artifact = FileArchitectureArtifactStore(application).save_architecture_sheet(job, result)

    json_path = application.data_dir / artifact.json_path
    markdown_path = application.data_dir / artifact.markdown_path
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert artifact.id == "job-1"
    assert artifact.title == "Team Todo"
    assert artifact.json_path == "architecture-sheets/team-todo-job-1.json"
    assert payload["artifact"]["job_id"] == "job-1"
    assert payload["result"]["architecture_sheet"]["artifact_name"] == "Team Todo"
    assert "# Team Todo" in markdown
    assert "## Bausteine" in markdown


def test_file_architecture_artifact_store_lists_and_loads_payload(tmp_path: Path) -> None:
    application = ApplicationInstance(
        id="software-factory",
        profile=ApplicationProfile(name="Software Factory"),
        template_dir=tmp_path / "apps" / "software-factory",
        data_dir=tmp_path / "data" / "software-factory",
    )
    store = FileArchitectureArtifactStore(application)
    job = ArchitectureGenerationJob.create("Eine App.", generation_mode="agentic", job_id="job-1")

    store.save_architecture_sheet(
        job,
        {
            "architecture_sheet": {"artifact_name": "Team Todo"},
            "schema_id": "schema",
            "validation": {"valid": True},
            "generation": {},
        },
    )

    artifacts = store.list_architecture_sheets()
    loaded = store.load_architecture_sheet_payload("job-1")

    assert [artifact.id for artifact in artifacts] == ["job-1"]
    assert loaded["artifact"]["id"] == "job-1"
