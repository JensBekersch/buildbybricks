"""Run a local end-to-end smoke test against a running app instance."""

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
from urllib import error, parse, request


def main() -> int:
    parser = argparse.ArgumentParser(description="Run app smoke checks against a live server.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output-dir", default="artifacts/smoke-test")
    parser.add_argument("--question", default="Was ist Agentic RAG?")
    parser.add_argument("--collection", default="")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wait_for_health(base_url)

    checks = [
        ("health", get_json(base_url, "/health")),
        ("template_profile", get_json(base_url, "/template/profile")),
        ("collections", get_json(base_url, "/collections")),
        ("ingestion_preview", get_json(base_url, "/ingestion/preview?collection=sample")),
        ("retrieval_search", get_json(base_url, "/retrieval/search?collection=sample&q=agentic&top_k=3")),
        ("evaluation", get_json(base_url, "/evaluation/run")),
        (
            "chat",
            post_json(
                base_url,
                "/chat",
                {
                    "message": args.question,
                    "collection": args.collection or None,
                    "top_k": args.top_k,
                },
            ),
        ),
    ]

    for name, payload in checks:
        write_json(output_dir / f"{name}.json", payload)

    summary = build_summary(checks)
    (output_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


def wait_for_health(base_url: str, timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Optional[Exception] = None

    while time.time() < deadline:
        try:
            payload = get_json(base_url, "/health")
            if payload.get("status") == "ok":
                return
        except Exception as exc:  # pragma: no cover - only used while waiting for external server.
            last_error = exc
        time.sleep(1)

    raise RuntimeError(f"App did not become healthy within {timeout_seconds}s: {last_error}")


def get_json(base_url: str, path: str) -> Dict[str, Any]:
    with request.urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(base_url: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    clean_payload = {key: value for key, value in payload.items() if value is not None}
    body = json.dumps(clean_payload).encode("utf-8")
    req = request.Request(
        f"{base_url}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_summary(checks: List[tuple]) -> str:
    payloads = {name: payload for name, payload in checks}
    evaluation = payloads["evaluation"]
    chat = payloads["chat"]
    collections = payloads["collections"].get("collections", [])
    sources = chat.get("sources", [])
    tool_calls = chat.get("tool_calls", [])

    lines = [
        "# Smoke Test Summary",
        "",
        f"- Health: `{payloads['health'].get('status')}`",
        f"- Template: `{payloads['template_profile'].get('name')}`",
        f"- Collections: {', '.join(collection['name'] for collection in collections) or 'none'}",
        f"- Evaluation: {evaluation.get('passed_cases')}/{evaluation.get('total_cases')} passed",
        f"- Chat sources: {len(sources)}",
        f"- Chat tool calls: {', '.join(tool_call['name'] for tool_call in tool_calls) or 'none'}",
        "",
        "## Chat Answer",
        "",
        chat.get("answer", ""),
        "",
        "## Uncertainty",
        "",
        chat.get("uncertainty", ""),
    ]
    return "\n".join(lines).strip() + "\n"


if __name__ == "__main__":
    sys.exit(main())
