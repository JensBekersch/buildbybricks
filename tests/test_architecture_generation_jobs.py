from agentic_rag_template.software_factory import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_CANCELED,
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_PENDING,
    ArchitectureGenerationJob,
)


def test_architecture_generation_job_starts_queued_with_steps() -> None:
    job = ArchitectureGenerationJob.create(
        "  Eine Django App fuer Aufgaben.  ",
        generation_mode="agentic",
        llm_provider="ollama",
        llm_model="qwen3:14b",
        job_id="job-1",
    )
    payload = job.to_dict()

    assert payload["id"] == "job-1"
    assert payload["status"] == JOB_STATUS_QUEUED
    assert payload["description"] == "Eine Django App fuer Aufgaben."
    assert payload["llm_provider"] == "ollama"
    assert payload["llm_model"] == "qwen3:14b"
    assert payload["steps"][0]["key"] == "validate_description"
    assert payload["steps"][0]["status"] == STEP_STATUS_PENDING
    assert payload["logs"][0]["message"] == "Job wurde erzeugt."


def test_architecture_generation_job_records_running_steps_and_result() -> None:
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic_with_review",
        job_id="job-2",
    )

    job.start_step("validate_description", "Beschreibung wird geprueft.")
    job.complete_step("validate_description", "Beschreibung ist verwendbar.")
    job.start_step("analyze_requirements", "Requirement Analyst laeuft.")
    job.complete_step("analyze_requirements")
    job.complete({"architecture_sheet": {"artifact_name": "Team Todo"}})

    payload = job.to_dict()
    steps = {step["key"]: step for step in payload["steps"]}

    assert payload["status"] == JOB_STATUS_COMPLETED
    assert payload["current_step"] == ""
    assert payload["started_at"] is not None
    assert payload["finished_at"] is not None
    assert payload["result"]["architecture_sheet"]["artifact_name"] == "Team Todo"
    assert steps["validate_description"]["status"] == STEP_STATUS_COMPLETED
    assert steps["analyze_requirements"]["status"] == STEP_STATUS_COMPLETED
    assert any(log["step"] == "analyze_requirements" for log in payload["logs"])


def test_architecture_generation_job_records_failed_step() -> None:
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic_with_review",
        job_id="job-3",
    )

    job.start_step("synthesize_architecture", "Synthesizer laeuft.")
    job.fail_step("synthesize_architecture", "Ollama request timed out.")

    payload = job.to_dict()
    steps = {step["key"]: step for step in payload["steps"]}

    assert payload["status"] == JOB_STATUS_FAILED
    assert payload["current_step"] == "synthesize_architecture"
    assert payload["error"] == "Ollama request timed out."
    assert steps["synthesize_architecture"]["status"] == STEP_STATUS_FAILED
    assert steps["synthesize_architecture"]["error"] == "Ollama request timed out."
    assert payload["logs"][-1]["level"] == "error"


def test_architecture_generation_job_can_hide_result_in_summary() -> None:
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic",
        job_id="job-4",
    )
    job.mark_running()

    payload = job.to_dict(include_result=False)

    assert payload["status"] == JOB_STATUS_RUNNING
    assert "result" not in payload


def test_architecture_generation_job_rejects_unknown_generation_mode() -> None:
    try:
        ArchitectureGenerationJob.create(
            "Eine Django App fuer Aufgaben.",
            generation_mode="fast",
            job_id="job-5",
        )
    except ValueError as error:
        assert "generation_mode" in str(error)
    else:
        raise AssertionError("Unknown generation modes must be rejected.")


def test_architecture_generation_job_can_be_canceled_before_terminal_state() -> None:
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic",
        job_id="job-6",
    )
    job.mark_running()

    job.cancel("Benutzerabbruch.")
    payload = job.to_dict()

    assert payload["status"] == JOB_STATUS_CANCELED
    assert payload["error"] == "Benutzerabbruch."
    assert payload["finished_at"] is not None
    assert payload["logs"][-1]["level"] == "warning"


def test_architecture_generation_job_rejects_cancel_after_terminal_state() -> None:
    job = ArchitectureGenerationJob.create(
        "Eine Django App fuer Aufgaben.",
        generation_mode="agentic",
        job_id="job-7",
    )
    job.complete({"architecture_sheet": {"artifact_name": "Team Todo"}})

    try:
        job.cancel()
    except ValueError as error:
        assert "Terminal jobs" in str(error)
    else:
        raise AssertionError("Completed jobs must not be canceled.")
