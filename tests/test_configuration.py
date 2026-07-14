from agentic_rag_template.config import Settings


def test_settings_default_llm_timeout_allows_local_agentic_runs(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_RAG_LLM_TIMEOUT_SECONDS", raising=False)
    settings = Settings.from_env()

    assert settings.llm_timeout_seconds == 1200


def test_settings_reads_llm_configuration_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_RAG_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("AGENTIC_RAG_LLM_MODEL", "llama3.1")
    monkeypatch.setenv("AGENTIC_RAG_LLM_API_BASE_URL", "http://host.docker.internal:11434")
    monkeypatch.setenv("AGENTIC_RAG_LLM_API_KEY", "secret")
    monkeypatch.setenv("AGENTIC_RAG_LLM_TIMEOUT_SECONDS", "240")
    monkeypatch.setenv("AGENTIC_RAG_LLM_MAX_TOKENS", "80")
    settings = Settings.from_env()

    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "llama3.1"
    assert settings.llm_api_base_url == "http://host.docker.internal:11434"
    assert settings.llm_api_key == "secret"
    assert settings.llm_timeout_seconds == 240
    assert settings.llm_max_tokens == 80
