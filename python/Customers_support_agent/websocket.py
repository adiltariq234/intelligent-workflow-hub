"""WebSocket endpoint for streaming chat responses.

The client sends a JSON payload `{"session_id": str, "message": str}` and
receives a sequence of JSON events:
  - {"type": "chunk", "text": "..."}      streamed answer text
  - {"type": "sources", "sources": [...]} final source citations
  - {"type": "error", "detail": "..."}    on failure
  - {"type": "done"}                      end of turn
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.exceptions import SupportAgentError
from app.dependencies import get_rag_pipeline
from app.utils.security import sanitize_session_id, sanitize_text_input

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Handle a persistent WebSocket connection for streaming chat.

    Args:
        websocket: The client WebSocket connection.
    """
    await websocket.accept()
    pipeline = get_rag_pipeline()

    try:
        while True:
            payload = await websocket.receive_json()
            session_id = sanitize_session_id(str(payload.get("session_id", "")))
            message = sanitize_text_input(str(payload.get("message", "")))
            top_k = payload.get("top_k")

            if not message:
                await websocket.send_json(
                    {"type": "error", "detail": "Message cannot be empty."}
                )
                continue

            try:
                async for chunk_text, sources in pipeline.stream_answer(
                    session_id, message, top_k=top_k
                ):
                    if sources is not None:
                        await websocket.send_json(
                            {
                                "type": "sources",
                                "sources": [s.model_dump(mode="json") for s in sources],
                            }
                        )
                    elif chunk_text:
                        await websocket.send_json({"type": "chunk", "text": chunk_text})

                await websocket.send_json({"type": "done"})
            except SupportAgentError as exc:
                logger.warning("Chat error for session %s: %s", session_id, exc.message)
                await websocket.send_json({"type": "error", "detail": exc.message})
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error during streaming chat.")
                await websocket.send_json(
                    {"type": "error", "detail": "An unexpected error occurred."}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
