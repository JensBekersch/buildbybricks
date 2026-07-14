"""Load text-like files from collection folders below the data directory."""

from pathlib import Path
from typing import Iterable, List, Optional

from agentic_rag_template.ingestion.models import SourceDocument

SUPPORTED_EXTENSIONS = {".json", ".md", ".txt"}


def discover_collections(data_dir: Path) -> List[str]:
    """Return collection names represented by first-level folders in data_dir."""
    if not data_dir.exists():
        return []

    return sorted(
        path.name
        for path in data_dir.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def iter_source_files(collection_dir: Path) -> Iterable[Path]:
    """Yield supported files in stable order for reproducible ingestion."""
    if not collection_dir.exists():
        return []

    files = [
        path
        for path in collection_dir.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)


def load_documents(data_dir: Path, collection: Optional[str] = None) -> List[SourceDocument]:
    """Load supported documents from one collection or from all collections."""
    collections = [collection] if collection else discover_collections(data_dir)
    documents: List[SourceDocument] = []

    for collection_name in collections:
        collection_dir = data_dir / collection_name
        for file_path in iter_source_files(collection_dir):
            relative_path = file_path.relative_to(data_dir)
            content = file_path.read_text(encoding="utf-8").strip()

            if not content:
                continue

            documents.append(
                SourceDocument(
                    collection=collection_name,
                    path=file_path,
                    relative_path=relative_path,
                    title=file_path.stem.replace("_", " ").replace("-", " ").strip(),
                    content=content,
                    metadata={
                        "extension": file_path.suffix.lower(),
                        "filename": file_path.name,
                        "relative_path": relative_path.as_posix(),
                    },
                )
            )

    return documents
