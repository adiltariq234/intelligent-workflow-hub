"""Custom exception hierarchy used across the application.

Using specific exception types (instead of bare `Exception`) lets the API
layer translate failures into precise, user-safe HTTP responses without
leaking internal details.
"""


class SupportAgentError(Exception):
    """Base class for all application-specific errors."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class FileValidationError(SupportAgentError):
    """Raised when an uploaded file fails validation (type, size, name)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class DocumentProcessingError(SupportAgentError):
    """Raised when a document cannot be parsed or chunked."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class VectorStoreError(SupportAgentError):
    """Raised when a Qdrant operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)


class LLMError(SupportAgentError):
    """Raised when the Mistral LLM call fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)


class ConversationNotFoundError(SupportAgentError):
    """Raised when a conversation/session id is unknown."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
