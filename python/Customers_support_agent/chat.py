"""REST endpoints for non-streaming chat and session management."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_memory_service, get_rag_pipeline
from app.models.schemas import ChatRequest, ChatResponse
from app.services.memory import ConversationMemoryService
from app.services.rag_pipeline import RAGPipeline
from app.utils.security import sanitize_session_id, sanitize_text_input

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ChatResponse:
    """Answer a user question with full RAG grounding (single JSON response).

    Args:
        request: The chat request payload.
        pipeline: Injected RAG pipeline.

    Returns:
        The generated answer along with the source citations used.
    """
    session_id = sanitize_session_id(request.session_id)
    question = sanitize_text_input(request.message)

    answer, sources = pipeline.answer(session_id, question, top_k=request.top_k)
    return ChatResponse(session_id=session_id, answer=answer, sources=sources)


@router.delete("/{session_id}")
async def clear_session(
    session_id: str,
    memory: ConversationMemoryService = Depends(get_memory_service),
) -> dict:
    """Clear a session's conversation history.

    Args:
        session_id: The session to clear.
        memory: Injected memory service.

    Returns:
        A confirmation message.
    """
    clean_id = sanitize_session_id(session_id)
    memory.clear_session(clean_id)
    return {"message": f"Session '{clean_id}' cleared."}
