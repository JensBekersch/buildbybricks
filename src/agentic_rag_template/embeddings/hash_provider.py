"""Deterministic local embedding provider used for tests and offline runs."""

from hashlib import sha256
import math
import re
from typing import List

from agentic_rag_template.embeddings.models import Vector

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class HashEmbeddingProvider:
    """Create stable bag-of-token vectors without external services."""

    name = "hash"

    def __init__(self, model: str = "local-hash-v1", dimension: int = 64) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be greater than zero")

        self.model = model
        self.dimension = dimension

    def embed_text(self, text: str) -> Vector:
        vector = [0.0] * self.dimension

        for token in tokenize(text):
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        return normalize(vector)

    def embed_texts(self, texts: List[str]) -> List[Vector]:
        return [self.embed_text(text) for text in texts]


def tokenize(text: str) -> List[str]:
    """Extract lowercase tokens for deterministic local embeddings."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def normalize(vector: Vector) -> Vector:
    """Normalize a vector to unit length when possible."""
    magnitude = math.sqrt(sum(value * value for value in vector))

    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]
