"""Centralized, typed application configuration.

All secrets and tunables are loaded from environment variables (via a local
`.env` file in development). No secret is ever hard-coded. Importing this
module gives a single cached `Settings` instance shared across the app.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings.

    Values are populated from environment variables or a `.env` file.
    See `.env.example` for the full list of supported keys.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Mistral LLM ---------------------------------------------------
    mistral_api_key: str = Field(..., description="Mistral API secret key")
    mistral_model: str = Field(default="mistral-large-latest")

    # --- Qdrant vector database -----------------------------------------
    qdrant_url: str = Field(..., description="Qdrant Cloud cluster URL")
    qdrant_api_key: str = Field(..., description="Qdrant Cloud API key")
    qdrant_collection_name: str = Field(default="support_agent_docs")

    # --- Embeddings ------------------------------------------------------
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384, gt=0)

    # --- App ---------------------------------------------------------------
    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000, gt=0, lt=65536)
    log_level: str = Field(default="INFO")
    allowed_origins: str = Field(default="http://localhost:8000")

    # --- Uploads -----------------------------------------------------------
    max_upload_size_mb: int = Field(default=20, gt=0, le=200)
    upload_dir: str = Field(default="uploads")
    allowed_extensions: str = Field(default=".pdf,.txt,.docx,.md")

    # --- RAG -----------------------------------------------------------------
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)
    retrieval_top_k: int = Field(default=5, gt=0)
    mmr_fetch_k: int = Field(default=20, gt=0)
    mmr_lambda: float = Field(default=0.5, ge=0.0, le=1.0)

    # --- Memory ------------------------------------------------------------
    max_history_turns: int = Field(default=10, gt=0)

    @field_validator("mistral_api_key", "qdrant_api_key")
    @classmethod
    def _not_placeholder(cls, value: str) -> str:
        """Reject obvious placeholder secrets so misconfiguration fails fast."""
        if not value or "your_" in value.lower():
            raise ValueError(
                "A required secret is missing or still set to its placeholder "
                "value. Populate it in your .env file."
            )
        return value

    @property
    def allowed_origins_list(self) -> List[str]:
        """Return CORS origins as a clean list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Return allowed upload file extensions as a clean, lowercase list."""
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Max upload size converted to bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide `Settings` instance."""
    return Settings()
