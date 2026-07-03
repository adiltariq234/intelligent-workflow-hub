"""REST endpoint for multi-file document upload and ingestion into the
vector store.
"""

import logging
import os
import time
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.core.exceptions import FileValidationError
from app.dependencies import get_document_processor, get_vector_store_service
from app.models.schemas import UploadedDocumentInfo, UploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService
from app.utils.file_validation import (
    build_safe_upload_path,
    read_upload_within_limit,
    validate_file_extension,
    validate_file_size,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
    processor: DocumentProcessor = Depends(get_document_processor),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
) -> UploadResponse:
    """Validate, parse, chunk, and index one or more uploaded documents.

    Parsing/chunking and embedding are CPU-bound, so they are run in a
    worker thread via `run_in_threadpool`. This keeps the async event loop
    free — meaning other requests (like active WebSocket chats) stay
    responsive while a large file is being indexed, instead of the whole
    server appearing to freeze.

    Args:
        files: One or more files sent as multipart/form-data.
        settings: Injected application settings.
        processor: Injected document processor.
        vector_store: Injected vector store service.

    Returns:
        Per-file ingestion results and the total number of chunks indexed.

    Raises:
        FileValidationError: If any file fails validation. Handled globally
            and converted into a 400 response.
    """
    results: List[UploadedDocumentInfo] = []
    total_chunks = 0

    for upload in files:
        if not upload.filename:
            raise FileValidationError("An uploaded file is missing a filename.")

        validate_file_extension(upload.filename, settings)
        content = await read_upload_within_limit(upload, settings)
        validate_file_size(len(content), settings)

        safe_path = build_safe_upload_path(upload.filename, settings.upload_dir)
        try:
            with open(safe_path, "wb") as f:
                f.write(content)

            t0 = time.perf_counter()
            chunks = await run_in_threadpool(processor.process, safe_path, upload.filename)
            t1 = time.perf_counter()
            logger.info(
                "Parsed '%s' into %d chunks in %.1fs.",
                upload.filename, len(chunks), t1 - t0,
            )

            indexed_count = await run_in_threadpool(vector_store.upsert_chunks, chunks)
            t2 = time.perf_counter()
            logger.info(
                "Embedded + indexed '%s' (%d chunks) in %.1fs.",
                upload.filename, indexed_count, t2 - t1,
            )

            results.append(
                UploadedDocumentInfo(
                    filename=upload.filename,
                    chunk_count=indexed_count,
                    file_type=upload.filename.rsplit(".", 1)[-1].lower(),
                    size_bytes=len(content),
                )
            )
            total_chunks += indexed_count
            logger.info(
                "Indexed '%s' into %d chunks (total %.1fs).",
                upload.filename, indexed_count, t2 - t0,
            )
        finally:
            # Uploaded files are only needed transiently for parsing; the
            # vector store, not the filesystem, is the durable record.
            if os.path.exists(safe_path):
                os.remove(safe_path)

    return UploadResponse(
        documents=results,
        total_chunks_indexed=total_chunks,
        message=f"Successfully indexed {len(results)} document(s).",
    )
