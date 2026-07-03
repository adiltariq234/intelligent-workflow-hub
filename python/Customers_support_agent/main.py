"""Application entrypoint: FastAPI app factory, middleware, routers, and
global exception handling.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import chat, health, upload, websocket
from app.config import get_settings
from app.core.exceptions import SupportAgentError
from app.core.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance.

    Returns:
        A fully configured `FastAPI` app, ready to serve.
    """
    app = FastAPI(
        title="AI Customer Support Agent",
        description="Production-ready RAG-powered customer support agent.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    app.include_router(chat.router)
    app.include_router(upload.router)
    app.include_router(health.router)
    app.include_router(websocket.router)

    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request) -> HTMLResponse:
        """Serve the chat UI."""
        return templates.TemplateResponse(request, "index.html", {})

    @app.exception_handler(SupportAgentError)
    async def handle_app_error(request: Request, exc: SupportAgentError) -> JSONResponse:
        """Translate known application errors into clean JSON responses."""
        logger.warning("Handled error on %s: %s", request.url.path, exc.message)
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler that never leaks internal details to the client."""
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500, content={"error": "An unexpected internal error occurred."}
        )

    return app


app = create_app()
