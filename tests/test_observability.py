from agentic_rag_template.config import Settings
from agentic_rag_template.observability import render_prometheus_metrics
from agentic_rag_template.software_factory import ArchitectureGenerationJob


def test_render_prometheus_metrics_includes_job_step_llm_and_error_metrics() -> None:
    settings = Settings(
        llm_provider="ollama",
        llm_model="qwen3:14b",
        llm_timeout_seconds=1200,
        llm_max_tokens=4096,
        architecture_generation_mode="agentic_with_review",
    )
    completed = ArchitectureGenerationJob.create(
        "Eine Django-Anwendung fuer Arbeitszeiterfassung.",
        generation_mode="agentic_with_review",
        llm_provider="ollama",
        llm_model="qwen3:14b",
        job_id="completed-job",
    )
    completed.start_step("analyze_requirements", "Anforderungen analysieren")
    completed.add_log(
        "LLM call completed.",
        step="analyze_requirements",
        metadata={
            "kind": "llm_call",
            "llm_step": "requirement_analyst",
            "provider": "ollama",
            "model": "qwen3:14b",
            "status": "completed",
            "duration_seconds": 1.25,
        },
    )
    completed.complete_step("analyze_requirements")
    completed.complete({"architecture_sheet": {"artifact_name": "Arbeitszeiterfassung"}})

    failed = ArchitectureGenerationJob.create(
        "Eine Django-Anwendung fuer Aufgaben.",
        generation_mode="agentic",
        llm_provider="ollama",
        llm_model="qwen3:14b",
        job_id="failed-job",
    )
    failed.start_step("synthesize_architecture", "Architecture Sheet erzeugen")
    failed.add_log(
        "LLM call failed.",
        level="error",
        step="synthesize_architecture",
        metadata={
            "kind": "llm_call",
            "llm_step": "architecture_synthesizer",
            "provider": "ollama",
            "model": "qwen3:14b",
            "status": "failed",
            "duration_seconds": 2.5,
            "error": "timeout",
        },
    )
    failed.fail_step("synthesize_architecture", "Ollama request failed: timeout")

    payload = render_prometheus_metrics(settings, [completed, failed])

    assert 'buildbybricks_runtime_info{architecture_mode="agentic_with_review",llm_model="qwen3:14b",llm_provider="ollama"} 1' in payload
    assert "buildbybricks_llm_timeout_seconds 1200" in payload
    assert "buildbybricks_llm_token_budget 4096" in payload
    assert 'buildbybricks_architecture_jobs{status="completed"} 1' in payload
    assert 'buildbybricks_architecture_jobs{status="failed"} 1' in payload
    assert 'buildbybricks_architecture_step_duration_seconds_count{status="completed",step="analyze_requirements"} 1' in payload
    assert 'buildbybricks_llm_call_duration_seconds_sum{llm_step="requirement_analyst",model="qwen3:14b",provider="ollama",status="completed"} 1.25' in payload
    assert 'buildbybricks_llm_call_duration_seconds_sum{llm_step="architecture_synthesizer",model="qwen3:14b",provider="ollama",status="failed"} 2.5' in payload
    assert 'buildbybricks_architecture_job_errors{reason="Ollama request failed: timeout",status="failed"} 1' in payload
