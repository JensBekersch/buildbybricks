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
        timeout_seconds: int = 300,
        max_tokens: int = 160,
    ) -> None:
        self.model = model
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

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

        response = self._post_chat(build_payload(request_payload, self.model, self.max_tokens))
        answer = str(response.get("message", {}).get("content", "")).strip()

        if not answer:
            raise RuntimeError("Ollama returned an empty answer")

        return LLMResponse(
            answer=answer,
            uncertainty=build_uncertainty(request_payload.retrieved_chunks),
            trace=["ollama_chat_completed"],
        )

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate a structured JSON object through Ollama."""
        response = self._post_chat(
            build_json_payload(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.model,
                max_tokens=max(self.max_tokens, 2048),
            )
        )
        content = str(response.get("message", {}).get("content", "")).strip()

        if not content:
            raise RuntimeError("Ollama returned an empty JSON response")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise RuntimeError("Ollama returned invalid JSON") from error

        if not isinstance(payload, dict):
            raise RuntimeError("Ollama returned JSON that is not an object")

        return payload

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


def build_payload(request_payload: LLMRequest, model: str, max_tokens: int = 160) -> Dict[str, Any]:
    """Build an Ollama chat payload with local context and citation instructions."""
    return {
        "model": model,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": max_tokens,
        },
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


def build_json_payload(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """Build an Ollama chat payload that requests a JSON object."""
    return {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": max_tokens,
        },
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
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
