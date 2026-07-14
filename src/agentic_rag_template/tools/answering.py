"""Answer composition helpers for grounded local responses."""

from dataclasses import dataclass, field
from typing import List

from agentic_rag_template.api.schemas import SourceReference
from agentic_rag_template.retrieval import RetrievedChunk


@dataclass(frozen=True)
class Citation:
    """A citation that links an answer statement to a retrieved source."""

    index: int
    title: str
    location: str
    excerpt: str
    score: float

    def to_source_reference(self) -> SourceReference:
        return SourceReference(
            title=self.title,
            location=self.location,
            excerpt=self.excerpt,
            score=round(self.score, 6),
        )


@dataclass(frozen=True)
class AnswerDraft:
    """A composed answer and its grounding metadata."""

    answer: str
    citations: List[Citation] = field(default_factory=list)
    uncertainty: str = ""
    trace: List[str] = field(default_factory=list)

    @property
    def sources(self) -> List[SourceReference]:
        return [citation.to_source_reference() for citation in self.citations]


def compose_grounded_answer(query: str, results: List[RetrievedChunk]) -> AnswerDraft:
    """Compose a deterministic answer from retrieval results."""
    if not results:
        return AnswerDraft(
            answer=(
                "Ich habe in den lokalen Wissensdaten keine passende Quelle gefunden. "
                "Bitte fuege passende Dokumente unter data/<collection>/ hinzu oder praezisiere die Frage."
            ),
            uncertainty=(
                "Keine lokalen Treffer. Die Antwort enthaelt deshalb keine fachliche Aussage "
                "ueber den Inhalt der Wissensbasis."
            ),
        )

    citations = [
        Citation(
            index=index,
            title=result.title,
            location=result.source_path,
            excerpt=build_excerpt(result.text),
            score=result.score,
        )
        for index, result in enumerate(deduplicate_results(results), start=1)
    ]
    best = citations[0]
    answer = "\n".join(
        [
            f"Kurzantwort: Zu deiner Frage '{query}' passt am besten die Quelle [{best.index}] {best.title}.",
            "",
            "Begruendung: Die lokale Wissensbasis enthaelt dazu diesen relevanten Ausschnitt:",
            f"\"{best.excerpt}\"",
            "",
            "Quellen:",
            *[
                f"[{citation.index}] {citation.title} ({citation.location}, score={citation.score:.3f})"
                for citation in citations
            ],
        ]
    )

    return AnswerDraft(
        answer=answer,
        citations=citations,
        uncertainty=build_uncertainty(results),
    )


def deduplicate_results(results: List[RetrievedChunk]) -> List[RetrievedChunk]:
    """Keep the best result per source path while preserving result order."""
    seen = set()
    deduplicated: List[RetrievedChunk] = []

    for result in results:
        if result.source_path in seen:
            continue

        seen.add(result.source_path)
        deduplicated.append(result)

    return deduplicated


def build_excerpt(text: str, limit: int = 260) -> str:
    """Create a compact excerpt for citations and the frontend."""
    compact = " ".join(text.split())

    if len(compact) <= limit:
        return compact

    return compact[: limit - 3].rstrip() + "..."


def build_uncertainty(results: List[RetrievedChunk]) -> str:
    """Explain how strong the local grounding is."""
    if not results:
        return "Keine Quellen gefunden."

    best_score = results[0].score

    if best_score >= 0.45:
        return "Die Antwort ist lokal belegt, basiert aber weiterhin nur auf den gefundenen Dokument-Chunks."

    return (
        "Die gefundene Aehnlichkeit ist eher niedrig. Pruefe die Quelle oder ergaenze passendere "
        "Dokumente, bevor du die Antwort als belastbar verwendest."
    )
