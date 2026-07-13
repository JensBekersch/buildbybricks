"""Data structures used by the local file ingestion pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class SourceDocument:
    """A text document loaded from one collection below the data directory."""

    collection: str
    path: Path
    relative_path: Path
    title: str
    content: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk prepared for later embedding and retrieval steps."""

    id: str
    collection: str
    source_path: str
    title: str
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    metadata: Dict[str, str] = field(default_factory=dict)
