"""Dependency-injection wiring.

Builds each service exactly once (process-wide singletons) and exposes
FastAPI-friendly getter functions for use with `Depends(...)`. Keeping
construction here — rather than inside route handlers — keeps routes thin
and makes services easy to swap or mock in tests.
"""

from functools import lru_cache

from app.config import get_settings
from app.services.document_processor import DocumentProcessor
from app.services.embeddings import EmbeddingService
from app.services.llm_service import LLMService
from app.services.memory import ConversationMemoryService
from app.services.rag_pipeline import RAGPipeline
from app.services.vector_store import VectorStoreService


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return the process-wide `EmbeddingService` singleton."""
    settings = get_settings()
    return EmbeddingService(model_name=settings.embedding_model)


@lru_cache
def get_vector_store_service() -> VectorStoreService:
    """Return the process-wide `VectorStoreService` singleton."""
    settings = get_settings()
    return VectorStoreService(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection_name,
        embedding_dimension=settings.embedding_dimension,
        embedding_service=get_embedding_service(),
    )


@lru_cache
def get_document_processor() -> DocumentProcessor:
    """Return the process-wide `DocumentProcessor` singleton."""
    settings = get_settings()
    return DocumentProcessor(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )


@lru_cache
def get_llm_service() -> LLMService:
    """Return the process-wide `LLMService` singleton."""
    settings = get_settings()
    return LLMService(api_key=settings.mistral_api_key, model_name=settings.mistral_model)


@lru_cache
def get_memory_service() -> ConversationMemoryService:
    """Return the process-wide `ConversationMemoryService` singleton."""
    settings = get_settings()
    return ConversationMemoryService(max_history_turns=settings.max_history_turns)


@lru_cache
def get_rag_pipeline() -> RAGPipeline:
    """Return the process-wide `RAGPipeline` singleton."""
    settings = get_settings()
    return RAGPipeline(
        vector_store=get_vector_store_service(),
        llm_service=get_llm_service(),
        memory_service=get_memory_service(),
        default_top_k=settings.retrieval_top_k,
        mmr_fetch_k=settings.mmr_fetch_k,
        mmr_lambda=settings.mmr_lambda,
    )
