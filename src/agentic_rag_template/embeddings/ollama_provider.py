"""Ollama-backed embedding provider."""

import json
import math
from typing import Any, Dict, List
from urllib import error, request

from agentic_rag_template.embeddings.models import Vector


class OllamaEmbeddingProvider:
    """Create embeddings through Ollama's embeddings API."""

    name = "ollama"

    def __init__(
        self,
        model: str = "nomic-embed-text",
        api_base_url: str = "http://localhost:11434",
        api_key: str = "",
        dimension: int = 0,
        timeout_seconds: int = 300,
    ) -> None:
        self.model = model
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.dimension = dimension
        self.timeout_seconds = timeout_seconds

    def embed_text(self, text: str) -> Vector:
        payload = self._post_embedding(text)
        embedding = payload.get("embedding")

        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("Ollama returned no embedding vector")

        vector = [float(value) for value in embedding]

        if self.dimension == 0:
            self.dimension = len(vector)
        elif len(vector) != self.dimension:
            raise RuntimeError(
                f"Ollama embedding dimension mismatch: expected {self.dimension}, got {len(vector)}"
            )

        return normalize(vector)

    def embed_texts(self, texts: List[str]) -> List[Vector]:
        return [self.embed_text(text) for text in texts]

    def _post_embedding(self, text: str) -> Dict[str, Any]:
        body = json.dumps({"model": self.model, "prompt": text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(
            f"{self.api_base_url}/api/embeddings",
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"Ollama embedding request failed: {exc}") from exc


def normalize(vector: Vector) -> Vector:
    """Normalize a vector to unit length when possible."""
    magnitude = math.sqrt(sum(value * value for value in vector))

    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]
