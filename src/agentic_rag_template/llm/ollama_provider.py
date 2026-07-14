"""Ollama-backed LLM provider."""

import json
from typing import Any, Dict, List
from urllib import error, request

from agentic_rag_template.llm.models import LLMRequest, LLMResponse
from agentic_rag_template.tools.answering import build_uncertainty


class OllamaLLMProvider:
    """Generate grounded answers through Ollama's chat API."""

    name = "ollama"

    def __init__(
        self,
        model: str,
        api_base_url: str = "http://localhost:11434",
        api_key: str = "",
        timeout_seconds: int = 120,
    ) -> None:
        self.model = model
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def generate_answer(self, request_payload: LLMRequest) -> LLMResponse:
        if not request_payload.retrieved_chunks:
            return LLMResponse(
                answer=(
                    "Ich habe in den lokalen Wissensdaten keine passende Quelle gefunden. "
                    "Bitte fuege passende Dokumente unter data/<collection>/ hinzu oder praezisiere die Frage."
                ),
                uncertainty="Keine lokalen Treffer. Es wurde kein Ollama-Call ausgefuehrt.",
                trace=["skipped_ollama_no_context"],
            )

        response = self._post_chat(build_payload(request_payload, self.model))
        answer = str(response.get("message", {}).get("content", "")).strip()

        if not answer:
            raise RuntimeError("Ollama returned an empty answer")

        return LLMResponse(
            answer=answer,
            uncertainty=build_uncertainty(request_payload.retrieved_chunks),
            trace=["ollama_chat_completed"],
        )

    def _post_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(
            f"{self.api_base_url}/api/chat",
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc


def build_payload(request_payload: LLMRequest, model: str) -> Dict[str, Any]:
    """Build an Ollama chat payload with local context and citation instructions."""
    return {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": build_system_prompt(request_payload.answer_policy),
            },
            {
                "role": "user",
                "content": build_user_prompt(request_payload),
            },
        ],
    }


def build_system_prompt(answer_policy: str) -> str:
    return "\n".join(
        [
            "Du bist ein lokaler Agentic-RAG-Assistent.",
            answer_policy,
            "Antworte ausschliesslich auf Basis des bereitgestellten Kontexts.",
            "Wenn der Kontext nicht ausreicht, sage das klar.",
            "Nenne Quellen im Format [1], [2] und erfinde keine Quellen.",
        ]
    )


def build_user_prompt(request_payload: LLMRequest) -> str:
    context_blocks: List[str] = []

    for index, chunk in enumerate(request_payload.retrieved_chunks, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[{index}] {chunk.title}",
                    f"Pfad: {chunk.source_path}",
                    f"Score: {chunk.score:.3f}",
                    "Ausschnitt:",
                    chunk.text,
                ]
            )
        )

    return "\n\n".join(
        [
            f"Frage: {request_payload.query}",
            "Kontext:",
            "\n\n".join(context_blocks),
            "Aufgabe: Formuliere eine hilfreiche Antwort mit Quellenangaben.",
        ]
    )
