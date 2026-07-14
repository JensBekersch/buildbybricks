from pathlib import Path

from agentic_rag_template.ingestion import discover_collections, ingest_data, load_documents


def test_discovers_collections_from_first_level_data_folders(tmp_path: Path) -> None:
    (tmp_path / "sample").mkdir()
    (tmp_path / "policies").mkdir()
    (tmp_path / ".ignored").mkdir()
    (tmp_path / "root-note.md").write_text("Ignored at root level", encoding="utf-8")

    assert discover_collections(tmp_path) == ["policies", "sample"]


def test_loads_supported_documents_recursively_with_collection_metadata(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policies" / "security"
    policy_dir.mkdir(parents=True)
    (policy_dir / "access-control.md").write_text("# Access Control\n\nUse least privilege.", encoding="utf-8")
    (policy_dir / "rules.json").write_text('{"rule": "Review before deploy"}', encoding="utf-8")
    (policy_dir / "diagram.png").write_text("not text", encoding="utf-8")

    documents = load_documents(tmp_path, collection="policies")
    paths = [document.relative_path.as_posix() for document in documents]

    assert paths == [
        "policies/security/access-control.md",
        "policies/security/rules.json",
    ]
    assert documents[0].collection == "policies"
    assert documents[0].relative_path.as_posix() == "policies/security/access-control.md"
    assert documents[0].metadata["filename"] == "access-control.md"
    assert documents[1].metadata["extension"] == ".json"


def test_ingest_data_chunks_documents_with_stable_ids_and_positions(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "guide.txt").write_text("Alpha Beta Gamma Delta Epsilon", encoding="utf-8")

    chunks = ingest_data(tmp_path, collection="sample", chunk_size=12, overlap=3)

    assert [chunk.id for chunk in chunks] == [
        "sample:sample/guide.txt:0",
        "sample:sample/guide.txt:1",
        "sample:sample/guide.txt:2",
    ]
    assert chunks[0].collection == "sample"
    assert chunks[0].source_path == "sample/guide.txt"
    assert chunks[0].chunk_index == 0
    assert chunks[0].char_start == 0
    assert chunks[0].metadata["extension"] == ".txt"
