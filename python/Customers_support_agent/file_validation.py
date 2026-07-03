"""File upload validation helpers.

Centralizes every check we run against an uploaded file so the API layer
stays thin and every upload path enforces the same security rules.
"""

import os
from pathlib import Path

from fastapi import UploadFile

from app.config import Settings
from app.core.exceptions import FileValidationError
from app.utils.security import sanitize_filename


def validate_file_extension(filename: str, settings: Settings) -> str:
    """Validate that a filename has an allowed extension.

    Args:
        filename: The original client-supplied filename.
        settings: Application settings holding the allow-list.

    Returns:
        The lower-cased extension (including the leading dot).

    Raises:
        FileValidationError: If the extension is missing or not allowed.
    """
    extension = Path(filename).suffix.lower()
    if not extension:
        raise FileValidationError("Uploaded file has no extension.")
    if extension not in settings.allowed_extensions_list:
        allowed = ", ".join(settings.allowed_extensions_list)
        raise FileValidationError(
            f"File type '{extension}' is not supported. Allowed types: {allowed}"
        )
    return extension


def validate_file_size(size_bytes: int, settings: Settings) -> None:
    """Validate that a file does not exceed the configured size limit.

    Args:
        size_bytes: Size of the uploaded file in bytes.
        settings: Application settings holding the size limit.

    Raises:
        FileValidationError: If the file is empty or too large.
    """
    if size_bytes <= 0:
        raise FileValidationError("Uploaded file is empty.")
    if size_bytes > settings.max_upload_size_bytes:
        raise FileValidationError(
            f"File exceeds the maximum allowed size of {settings.max_upload_size_mb} MB."
        )


def build_safe_upload_path(filename: str, upload_dir: str) -> str:
    """Build a filesystem path for an uploaded file, preventing path traversal.

    Args:
        filename: The original client-supplied filename.
        upload_dir: The directory uploads should be written to.

    Returns:
        An absolute, sanitized path guaranteed to live inside `upload_dir`.

    Raises:
        FileValidationError: If the resolved path would escape `upload_dir`.
    """
    safe_name = sanitize_filename(filename)
    base_dir = Path(upload_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    candidate = (base_dir / safe_name).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise FileValidationError("Resolved upload path is invalid.")
    if os.path.commonpath([str(base_dir), str(candidate)]) != str(base_dir):
        raise FileValidationError("Path traversal detected in filename.")

    return str(candidate)


async def read_upload_within_limit(file: UploadFile, settings: Settings) -> bytes:
    """Read an `UploadFile` fully while enforcing the size limit as it streams.

    Reading in chunks (rather than trusting `Content-Length`) prevents a
    client from lying about size in headers.

    Args:
        file: The incoming FastAPI `UploadFile`.
        settings: Application settings holding the size limit.

    Returns:
        The full file content as bytes.

    Raises:
        FileValidationError: If the stream exceeds the configured limit.
    """
    chunk_size = 1024 * 1024
    total = 0
    chunks = []

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_upload_size_bytes:
            raise FileValidationError(
                f"File exceeds the maximum allowed size of {settings.max_upload_size_mb} MB."
            )
        chunks.append(chunk)

    await file.seek(0)
    return b"".join(chunks)
