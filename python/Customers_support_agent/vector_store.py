"""Vector store service backed directly by `qdrant-client` (no LangChain
vector-store wrapper, per project requirements).

Implements upsert, similarity search, and Maximal Marginal Relevance (MMR)
re-ranking so retrieval balances relevance with diversity.
"""

import logging
import uuid
from typing import List, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.exceptions import VectorStoreError
from app.services.document_processor import DocumentChunk
from app.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Manages document vectors in a Qdrant Cloud collection."""

    def __init__(
        self,
        url: str,
        api_key: str,
        collection_name: str,
        embedding_dimension: int,
        embedding_service: EmbeddingService,
    ) -> None:
        """Connect to Qdrant and ensure the target collection exists.

        Args:
            url: Qdrant Cloud cluster URL.
            api_key: Qdrant Cloud API key.
            collection_name: Name of the collection to use/create.
            embedding_dimension: Dimensionality of stored vectors.
            embedding_service: Service used to embed queries.
        """
        self._collection_name = collection_name
        self._embedding_service = embedding_service
        try:
            self._client = QdrantClient(url=url, api_key=api_key, timeout=30)
            self._ensure_collection(embedding_dimension)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to connect to Qdrant.")
            raise VectorStoreError(f"Could not connect to vector database: {exc}") from exc

    def _ensure_collection(self, dimension: int) -> None:
        """Create the collection if it does not already exist."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection_name not in existing:
            logger.info("Creating Qdrant collection '%s'...", self._collection_name)
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=qmodels.VectorParams(
                    size=dimension, distance=qmodels.Distance.COSINE
                ),
            )

    def is_connected(self) -> bool:
        """Check whether the Qdrant connection is healthy."""
        try:
            self._client.get_collections()
            return True
        except Exception:  # noqa: BLE001
            return False

    def upsert_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Embed and upsert a batch of document chunks into Qdrant.

        Args:
            chunks: Document chunks produced by `DocumentProcessor`.

        Returns:
            The number of chunks successfully indexed.

        Raises:
            VectorStoreError: If embedding or the Qdrant write fails.
        """
        if not chunks:
            return 0
        try:
            vectors = self._embedding_service.embed_documents([c.text for c in chunks])
            points = [
                qmodels.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "document_name": chunk.document_name,
                        "file_type": chunk.file_type,
                        "chunk_index": chunk.chunk_index,
                        "page": chunk.page,
                        **chunk.metadata,
                    },
                )
                for chunk, vector in zip(chunks, vectors)
            ]
            self._client.upsert(collection_name=self._collection_name, points=points)
            return len(points)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to upsert chunks into Qdrant.")
            raise VectorStoreError(f"Failed to index document chunks: {exc}") from exc

    def similarity_search(self, query: str, top_k: int) -> List[qmodels.ScoredPoint]:
        """Plain top-k cosine similarity search.

        Args:
            query: The user's query text.
            top_k: Number of results to return.

        Returns:
            A list of Qdrant `ScoredPoint` results.
        """
        try:
            query_vector = self._embedding_service.embed_query(query)
            return self._client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            ).points
        except Exception as exc:  # noqa: BLE001
            logger.exception("Similarity search failed.")
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

    def mmr_search(
        self,
        query: str,
        top_k: int,
        fetch_k: int,
        lambda_mult: float,
    ) -> List[dict]:
        """Retrieve documents using Maximal Marginal Relevance (MMR).

        MMR balances relevance to the query with diversity among the
        selected results, reducing redundant near-duplicate chunks.

        Args:
            query: The user's query text.
            top_k: Number of final results to return.
            fetch_k: Number of candidates to fetch before re-ranking.
            lambda_mult: Trade-off between relevance (1.0) and diversity (0.0).

        Returns:
            A list of payload dicts (with `score`) for the selected chunks,
            ordered by MMR rank.
        """
        try:
            query_vector = self._embedding_service.embed_query(query)
            candidates = self._client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                limit=fetch_k,
                with_payload=True,
                with_vectors=True,
            ).points

            if not candidates:
                return []

            selected = self._maximal_marginal_relevance(
                query_vector=np.array(query_vector),
                candidate_vectors=[np.array(c.vector) for c in candidates],
                candidates=candidates,
                top_k=min(top_k, len(candidates)),
                lambda_mult=lambda_mult,
            )
            return selected
        except Exception as exc:  # noqa: BLE001
            logger.exception("MMR search failed.")
            raise VectorStoreError(f"MMR retrieval failed: {exc}") from exc

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two vectors (embeddings are pre-normalized)."""
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-10
        return float(np.dot(a, b) / denom)

    def _maximal_marginal_relevance(
        self,
        query_vector: np.ndarray,
        candidate_vectors: List[np.ndarray],
        candidates: List[qmodels.ScoredPoint],
        top_k: int,
        lambda_mult: float,
    ) -> List[dict]:
        """Greedy MMR selection over a candidate pool.

        Args:
            query_vector: Embedding of the query.
            candidate_vectors: Embeddings of each candidate, same order as
                `candidates`.
            candidates: The candidate Qdrant points.
            top_k: How many to select.
            lambda_mult: Relevance/diversity trade-off (1.0 = pure relevance).

        Returns:
            Payload dicts for the selected candidates, in selection order.
        """
        relevance_scores = [
            self._cosine_similarity(query_vector, vec) for vec in candidate_vectors
        ]
        selected_indices: List[int] = []
        remaining_indices = list(range(len(candidates)))

        while remaining_indices and len(selected_indices) < top_k:
            if not selected_indices:
                best_idx = max(remaining_indices, key=lambda i: relevance_scores[i])
            else:
                best_idx, best_score = None, float("-inf")
                for i in remaining_indices:
                    diversity_penalty = max(
                        self._cosine_similarity(candidate_vectors[i], candidate_vectors[j])
                        for j in selected_indices
                    )
                    mmr_score = (
                        lambda_mult * relevance_scores[i]
                        - (1 - lambda_mult) * diversity_penalty
                    )
                    if mmr_score > best_score:
                        best_idx, best_score = i, mmr_score
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        results = []
        for i in selected_indices:
            payload = dict(candidates[i].payload or {})
            payload["score"] = relevance_scores[i]
            results.append(payload)
        return results

    def delete_by_document_name(self, document_name: str) -> None:
        """Delete all chunks belonging to a given source document.

        Args:
            document_name: The original filename to remove.
        """
        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_name",
                                match=qmodels.MatchValue(value=document_name),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to delete document '%s'.", document_name)
            raise VectorStoreError(f"Failed to delete document: {exc}") from exc
