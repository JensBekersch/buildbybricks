# Boot and Smoke Test Setup

This setup boots the app, exercises the full local RAG path, and writes inspectable results.

## Default Deterministic Run

Start the app:

```bash
docker compose up --build
```

In a second terminal, run:

```bash
python3 scripts/smoke_test.py
```

The script writes JSON responses and a summary to:

```text
artifacts/smoke-test/
```

Useful live URLs:

- `http://localhost:8000`
- `http://localhost:8000/template/profile`
- `http://localhost:8000/collections`
- `http://localhost:8000/evaluation/run`

## Optional Ollama Service

Start the app plus Ollama:

```bash
docker compose --profile ollama up --build
```

Pull models when needed:

```bash
docker compose --profile ollama exec ollama ollama pull llama3.1
docker compose --profile ollama exec ollama ollama pull nomic-embed-text
```

Ollama is available inside the Compose network at `http://ollama:11434` and on the host at `http://localhost:11434`.

The current app still uses the deterministic answer composer. The Ollama service is ready for the next implementation step: adding real `OllamaLLMProvider` and `OllamaEmbeddingProvider` adapters.

## What The Smoke Test Checks

- API health
- active template profile
- available data collections
- ingestion preview
- retrieval search
- evaluation report
- chat answer with sources, uncertainty, trace, and tool calls
