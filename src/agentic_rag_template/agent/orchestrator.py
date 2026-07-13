"""First deterministic agent orchestration flow."""

from pathlib import Path
from typing import List

from agentic_rag_template.agent.models import AgentRequest, AgentResponse
from agentic_rag_template.embeddings.models import EmbeddingProvider
from agentic_rag_template.tools import (
    ToolCall,
    answer_with_citations,
    build_source_references,
    read_source,
    search_knowledge_base,
)


class StudyAgent:
    """A small agent that uses explicit tools in a fixed order."""

    def __init__(self, data_dir: Path, embedding_provider: EmbeddingProvider) -> None:
        self.data_dir = data_dir
        self.embedding_provider = embedding_provider

    def answer(self, request: AgentRequest) -> AgentResponse:
        query = request.message.strip()

        if not query:
            return AgentResponse(
                answer="Bitte gib eine Frage ein.",
                trace=["validated_message"],
            )

        tool_calls: List[ToolCall] = []
        trace = ["validated_message"]

        results = search_knowledge_base(
            data_dir=self.data_dir,
            embedding_provider=self.embedding_provider,
            query=query,
            collection=request.collection,
            top_k=request.top_k,
        )
        tool_calls.append(
            ToolCall(
                name="search_knowledge_base",
                arguments={
                    "query": query,
                    "collection": request.collection,
                    "top_k": request.top_k,
                },
                result_summary=f"{len(results)} result(s)",
            )
        )
        trace.append("searched_knowledge_base")

        if results:
            source_text = read_source(self.data_dir, results[0].source_path)
            tool_calls.append(
                ToolCall(
                    name="read_source",
                    arguments={"source_path": results[0].source_path},
                    result_summary=f"{len(source_text)} character(s)",
                )
            )
            trace.append("read_top_source")
        else:
            trace.append("skipped_source_read")

        answer = answer_with_citations(query, results)
        sources = build_source_references(results)
        tool_calls.append(
            ToolCall(
                name="answer_with_citations",
                arguments={"source_count": len(sources)},
                result_summary="answer composed",
            )
        )
        trace.append("composed_answer")

        return AgentResponse(
            answer=answer,
            sources=sources,
            trace=trace,
            tool_calls=tool_calls,
        )
