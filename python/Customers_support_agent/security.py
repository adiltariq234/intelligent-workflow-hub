"""Security helper functions: filename sanitization and input cleaning."""

import re
import uuid
from pathlib import Path

_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]")
_MULTI_UNDERSCORE_RE = re.compile(r"_{2,}")


def sanitize_filename(filename: str) -> str:
    """Produce a filesystem-safe, collision-resistant filename.

    Strips directory components, removes unsafe characters, and prefixes a
    short random id to avoid collisions and to make the on-disk name
    unguessable from the original.

    Args:
        filename: The original, untrusted filename from the client.

    Returns:
        A sanitized filename safe to use on the local filesystem.
    """
    base_name = Path(filename).name  # strips any directory components
    stem, suffix = Path(base_name).stem, Path(base_name).suffix

    stem = _UNSAFE_CHARS_RE.sub("_", stem).strip("._")
    stem = _MULTI_UNDERSCORE_RE.sub("_", stem) or "file"

    suffix = _UNSAFE_CHARS_RE.sub("", suffix)

    unique_prefix = uuid.uuid4().hex[:8]
    return f"{unique_prefix}_{stem}{suffix}"[:200]


def sanitize_text_input(text: str, max_length: int = 4000) -> str:
    """Trim, cap length, and strip control characters from user-supplied text.

    Args:
        text: Raw user input (e.g., a chat message).
        max_length: Maximum number of characters to retain.

    Returns:
        A cleaned string safe to forward to the LLM and to store.
    """
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    cleaned = cleaned.strip()
    return cleaned[:max_length]


def sanitize_session_id(session_id: str) -> str:
    """Restrict session ids to a safe alphanumeric/dash/underscore charset.

    Args:
        session_id: Client-supplied session identifier.

    Returns:
        A sanitized session id.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", session_id)
    return cleaned[:128] or uuid.uuid4().hex
