"""Embedding service backed by HuggingFace sentence-transformers.

Wraps `langchain-huggingface`'s `HuggingFaceEmbeddings` so the rest of the
app depends on a small, stable interface rather than the LangChain object
directly.
"""

import logging
import time
from typing import List

import torch
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Chunks are embedded in batches rather than all at once. This keeps peak
# memory bounded on large uploads and lets progress be logged incrementally
# instead of the caller seeing one long silent hang.
DEFAULT_BATCH_SIZE = 64


class EmbeddingService:
    """Generates dense vector embeddings for text using a local HF model."""

    def __init__(self, model_name: str, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        """Load the embedding model once and reuse it for all calls.

        Args:
            model_name: HuggingFace model id, e.g.
                "sentence-transformers/all-MiniLM-L6-v2".
            batch_size: Number of chunks encoded per batch. Lower this if
                you hit memory pressure on CPU; raise it if you have a GPU.
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading embedding model '%s' on device '%s'...", model_name, device)
        self._batch_size = batch_size
        self._model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": batch_size,
            },
        )
        logger.info("Embedding model loaded (device=%s, batch_size=%d).", device, batch_size)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document chunks, processed in smaller sub-batches.

        Args:
            texts: List of chunk texts to embed.

        Returns:
            A list of embedding vectors, one per input text, in input order.
        """
        if not texts:
            return []

        total = len(texts)
        vectors: List[List[float]] = []
        start = time.perf_counter()

        for batch_start in range(0, total, self._batch_size):
            batch = texts[batch_start : batch_start + self._batch_size]
            vectors.extend(self._model.embed_documents(batch))
            done = min(batch_start + self._batch_size, total)
            logger.info("Embedded %d/%d chunks...", done, total)

        elapsed = time.perf_counter() - start
        logger.info("Finished embedding %d chunks in %.1fs.", total, elapsed)
        return vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string.

        Args:
            text: The user query text.

        Returns:
            The embedding vector for the query.
        """
        return self._model.embed_query(text)
