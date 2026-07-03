"""RAG pipeline: orchestrates MMR retrieval, token-aware context compression,
conversation memory, and grounded LLM generation.
"""

import logging
from typing import AsyncIterator, List, Tuple

import tiktoken

from app.models.schemas import ChatMessage, MessageRole, SourceCitation
from app.services.llm_service import LLMService
from app.services.memory import ConversationMemoryService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 3000
CITATION_PREVIEW_CHARS = 280


class RAGPipeline:
    """High-level entry point used by the API layer to answer a question."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_service: LLMService,
        memory_service: ConversationMemoryService,
        default_top_k: int,
        mmr_fetch_k: int,
        mmr_lambda: float,
    ) -> None:
        """Wire together the pipeline's collaborators.

        Args:
            vector_store: Retrieval backend.
            llm_service: Generation backend.
            memory_service: Conversation history store.
            default_top_k: Default number of chunks to retrieve.
            mmr_fetch_k: Candidate pool size for MMR.
            mmr_lambda: MMR relevance/diversity trade-off.
        """
        self._vector_store = vector_store
        self._llm = llm_service
        self._memory = memory_service
        self._default_top_k = default_top_k
        self._mmr_fetch_k = mmr_fetch_k
        self._mmr_lambda = mmr_lambda
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def _retrieve(self, question: str, top_k: int) -> List[dict]:
        """Retrieve candidate chunks via MMR."""
        fetch_k = max(self._mmr_fetch_k, top_k)
        return self._vector_store.mmr_search(
            query=question, top_k=top_k, fetch_k=fetch_k, lambda_mult=self._mmr_lambda
        )

    def _compress_context(self, payloads: List[dict]) -> Tuple[str, List[SourceCitation]]:
        """Build a token-budgeted context string and matching citations.

        Truncates the pool to fit within `MAX_CONTEXT_TOKENS`, prioritizing
        the highest-scored chunks first (payloads arrive pre-ranked by MMR).

        Args:
            payloads: Ranked retrieval payload dicts.

        Returns:
            A tuple of (context_text, citation_list).
        """
        context_parts: List[str] = []
        citations: List[SourceCitation] = []
        used_tokens = 0

        for payload in payloads:
            text = payload.get("text", "")
            token_count = len(self._tokenizer.encode(text))
            if used_tokens + token_count > MAX_CONTEXT_TOKENS and context_parts:
                break

            doc_name = payload.get("document_name", "unknown")
            page = payload.get("page")
            label = f"[{doc_name}{f', p.{page}' if page else ''}]"
            context_parts.append(f"{label}\n{text}")
            used_tokens += token_count

            citations.append(
                SourceCitation(
                    document_name=doc_name,
                    chunk_text=text[:CITATION_PREVIEW_CHARS],
                    score=round(float(payload.get("score", 0.0)), 4),
                    page=page,
                    chunk_id=payload.get("chunk_id", ""),
                )
            )

        return "\n\n".join(context_parts), citations

    def answer(
        self, session_id: str, question: str, top_k: int | None = None
    ) -> Tuple[str, List[SourceCitation]]:
        """Answer a question synchronously (non-streaming).

        Args:
            session_id: Conversation/session identifier.
            question: The user's question.
            top_k: Optional override for the number of chunks to retrieve.

        Returns:
            A tuple of (answer_text, source_citations).
        """
        resolved_top_k = top_k or self._default_top_k
        payloads = self._retrieve(question, resolved_top_k)
        context, citations = self._compress_context(payloads)
        history_text = self._memory.get_history_as_text(session_id)

        answer = self._llm.generate_answer(question, context, history_text)

        self._memory.add_message(
            session_id, ChatMessage(role=MessageRole.USER, content=question)
        )
        self._memory.add_message(
            session_id,
            ChatMessage(role=MessageRole.ASSISTANT, content=answer, sources=citations),
        )
        return answer, citations

    async def stream_answer(
        self, session_id: str, question: str, top_k: int | None = None
    ) -> AsyncIterator[Tuple[str, List[SourceCitation] | None]]:
        """Answer a question with streaming output.

        Yields text chunks first (with `None` sources), then a final tuple
        carrying an empty string and the resolved source citations so the
        caller can emit a terminal "sources" event.

        Args:
            session_id: Conversation/session identifier.
            question: The user's question.
            top_k: Optional override for the number of chunks to retrieve.

        Yields:
            Tuples of (text_chunk, sources_or_none).
        """
        resolved_top_k = top_k or self._default_top_k
        payloads = self._retrieve(question, resolved_top_k)
        context, citations = self._compress_context(payloads)
        history_text = self._memory.get_history_as_text(session_id)

        self._memory.add_message(
            session_id, ChatMessage(role=MessageRole.USER, content=question)
        )

        full_answer_parts: List[str] = []
        async for chunk in self._llm.stream_answer(question, context, history_text):
            full_answer_parts.append(chunk)
            yield chunk, None

        full_answer = "".join(full_answer_parts)
        self._memory.add_message(
            session_id,
            ChatMessage(role=MessageRole.ASSISTANT, content=full_answer, sources=citations),
        )
        yield "", citations
