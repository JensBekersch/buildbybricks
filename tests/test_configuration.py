from agentic_rag_template.config import Settings


def test_settings_default_llm_timeout_allows_local_agentic_runs(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_RAG_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("AGENTIC_RAG_LLM_MAX_TOKENS", raising=False)
    settings = Settings.from_env()

    assert settings.llm_timeout_seconds == 1200
    assert settings.llm_max_tokens == 4096


def test_settings_reads_llm_configuration_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_RAG_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("AGENTIC_RAG_LLM_MODEL", "llama3.1")
    monkeypatch.setenv("AGENTIC_RAG_LLM_API_BASE_URL", "http://host.docker.internal:11434")
    monkeypatch.setenv("AGENTIC_RAG_LLM_API_KEY", "secret")
    monkeypatch.setenv("AGENTIC_RAG_LLM_TIMEOUT_SECONDS", "240")
    monkeypatch.setenv("AGENTIC_RAG_LLM_MAX_TOKENS", "80")
    monkeypatch.setenv("AGENTIC_RAG_ARCHITECTURE_GENERATION_MODE", "agentic")
    monkeypatch.setenv("AGENTIC_RAG_DATABASE_URL", "postgresql://user:pass@db:5432/jobs")
    settings = Settings.from_env()

    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "llama3.1"
    assert settings.llm_api_base_url == "http://host.docker.internal:11434"
    assert settings.llm_api_key == "secret"
    assert settings.llm_timeout_seconds == 240
    assert settings.llm_max_tokens == 80
    assert settings.architecture_generation_mode == "agentic"
    assert settings.database_url == "postgresql://user:pass@db:5432/jobs"


def test_settings_exposes_non_secret_runtime_config() -> None:
    settings = Settings(
        llm_provider="ollama",
        llm_model="qwen3:14b",
        llm_api_key="secret",
        llm_timeout_seconds=900,
        llm_max_tokens=2048,
        architecture_generation_mode="agentic",
    )

    payload = settings.runtime_config()

    assert payload["llm"]["provider"] == "ollama"
    assert payload["llm"]["model"] == "qwen3:14b"
    assert payload["llm"]["api_key_configured"] is True
    assert "secret" not in str(payload)
    assert payload["llm"]["timeout_seconds"] == 900
    assert payload["llm"]["max_tokens"] == 2048
    assert payload["pipelines"]["architecture_sheet"]["mode"] == "agentic"
