"""Pydantic data models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of a message within a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SourceCitation(BaseModel):
    """A single retrieved source used to ground an assistant answer."""

    document_name: str = Field(..., description="Original filename of the source document")
    chunk_text: str = Field(..., description="The retrieved chunk text, truncated for display")
    score: float = Field(..., description="Similarity score for this chunk (0-1)")
    page: Optional[int] = Field(default=None, description="Page number, if available")
    chunk_id: str = Field(..., description="Unique id of the chunk in the vector store")


class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: List[SourceCitation] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Incoming chat request from the client."""

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)
    top_k: Optional[int] = Field(default=None, gt=0, le=20)


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    session_id: str
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UploadedDocumentInfo(BaseModel):
    """Metadata returned after a document has been ingested."""

    filename: str
    chunk_count: int
    file_type: str
    size_bytes: int


class UploadResponse(BaseModel):
    """Response returned after processing one or more uploaded files."""

    documents: List[UploadedDocumentInfo]
    total_chunks_indexed: int
    message: str


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    app_env: str
    vector_store_connected: bool


class ErrorResponse(BaseModel):
    """Standard error payload returned to clients."""

    error: str
    detail: Optional[str] = None
