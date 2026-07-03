"""Health check endpoint used for monitoring/readiness probes."""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies import get_vector_store_service
from app.models.schemas import HealthResponse
from app.services.vector_store import VectorStoreService

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
) -> HealthResponse:
    """Report application and vector store health.

    Args:
        settings: Injected application settings.
        vector_store: Injected vector store service.

    Returns:
        Current health status.
    """
    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        vector_store_connected=vector_store.is_connected(),
    )
