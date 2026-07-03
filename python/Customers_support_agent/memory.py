"""Conversation memory service.

Keeps a bounded, in-process history per session id so follow-up questions
can be resolved with context. Swappable for a Redis-backed implementation
later without touching callers, since callers only depend on this class's
public interface.
"""

import logging
import threading
from collections import deque
from typing import Deque, Dict, List

from app.models.schemas import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class ConversationMemoryService:
    """Thread-safe, bounded in-memory store of per-session chat history."""

    def __init__(self, max_history_turns: int) -> None:
        """Initialize the store.

        Args:
            max_history_turns: Max number of (user, assistant) turn pairs to
                retain per session. Older turns are evicted first.
        """
        self._max_messages = max_history_turns * 2
        self._sessions: Dict[str, Deque[ChatMessage]] = {}
        self._lock = threading.Lock()

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to a session's history, evicting old turns as needed.

        Args:
            session_id: The conversation/session identifier.
            message: The message to store.
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = deque(maxlen=self._max_messages)
            self._sessions[session_id].append(message)

    def get_history(self, session_id: str) -> List[ChatMessage]:
        """Return the full stored history for a session, oldest first.

        Args:
            session_id: The conversation/session identifier.

        Returns:
            A list of `ChatMessage`s, empty if the session is unknown.
        """
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def get_history_as_text(self, session_id: str) -> str:
        """Format a session's history as plain text for prompt construction.

        Args:
            session_id: The conversation/session identifier.

        Returns:
            A newline-delimited transcript, or an empty string if none.
        """
        history = self.get_history(session_id)
        if not history:
            return ""
        lines = []
        for msg in history:
            speaker = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"{speaker}: {msg.content}")
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """Remove all history for a session.

        Args:
            session_id: The conversation/session identifier.
        """
        with self._lock:
            self._sessions.pop(session_id, None)
