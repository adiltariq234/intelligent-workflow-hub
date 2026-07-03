"""Document loading and chunking.

Supports PDF, DOCX, TXT, and Markdown. Uses a recursive, sentence-aware
splitter so chunks break on paragraph/sentence boundaries wherever possible
rather than mid-sentence, and every chunk carries metadata for citations.
"""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pypdf
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A single chunk of a source document, ready for embedding + indexing."""

    chunk_id: str
    text: str
    document_name: str
    file_type: str
    chunk_index: int
    page: int | None = None
    metadata: dict = field(default_factory=dict)


class DocumentProcessor:
    """Loads raw files into text and splits them into overlapping chunks."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        """Configure the recursive, sentence-aware text splitter.

        Args:
            chunk_size: Target maximum characters per chunk.
            chunk_overlap: Overlap (in characters) between consecutive chunks.
        """
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Ordered from largest to smallest semantic unit so splits prefer
            # paragraph breaks, then sentence breaks, before falling back to
            # words/characters.
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
            length_function=len,
        )

    def process(self, file_path: str, original_filename: str) -> List[DocumentChunk]:
        """Load a file from disk and split it into `DocumentChunk`s.

        Args:
            file_path: Path to the file already saved on disk.
            original_filename: The user-facing filename (used for citations).

        Returns:
            A list of chunks with populated metadata.

        Raises:
            DocumentProcessingError: If the file type is unsupported or
                parsing fails.
        """
        extension = Path(original_filename).suffix.lower()
        try:
            if extension == ".pdf":
                pages_text = self._load_pdf(file_path)
                return self._chunk_pages(pages_text, original_filename, extension)
            elif extension == ".docx":
                text = self._load_docx(file_path)
            elif extension in (".txt", ".md"):
                text = self._load_text(file_path)
            else:
                raise DocumentProcessingError(f"Unsupported file type: {extension}")
        except DocumentProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001 - convert any parser failure
            logger.exception("Failed to process file '%s'", original_filename)
            raise DocumentProcessingError(
                f"Could not parse '{original_filename}': {exc}"
            ) from exc

        return self._chunk_text(text, original_filename, extension, page=None)

    @staticmethod
    def _load_pdf(file_path: str) -> List[tuple[int, str]]:
        """Extract text from a PDF, page by page.

        Returns:
            A list of (page_number, page_text) tuples (1-indexed pages).
        """
        reader = pypdf.PdfReader(file_path)
        pages: List[tuple[int, str]] = []
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((idx, text))
        if not pages:
            raise DocumentProcessingError("PDF contains no extractable text.")
        return pages

    @staticmethod
    def _load_docx(file_path: str) -> str:
        """Extract text from a DOCX file, paragraph by paragraph."""
        doc = DocxDocument(file_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if not text.strip():
            raise DocumentProcessingError("DOCX contains no extractable text.")
        return text

    @staticmethod
    def _load_text(file_path: str) -> str:
        """Read a plain text or Markdown file as UTF-8."""
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            raise DocumentProcessingError("File is empty.")
        return text

    def _chunk_text(
        self, text: str, document_name: str, file_type: str, page: int | None
    ) -> List[DocumentChunk]:
        """Split raw text into `DocumentChunk`s using the recursive splitter."""
        raw_chunks = self._splitter.split_text(text)
        return [
            DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                text=chunk,
                document_name=document_name,
                file_type=file_type,
                chunk_index=i,
                page=page,
                metadata={"document_name": document_name, "file_type": file_type},
            )
            for i, chunk in enumerate(raw_chunks)
        ]

    def _chunk_pages(
        self, pages_text: List[tuple[int, str]], document_name: str, file_type: str
    ) -> List[DocumentChunk]:
        """Split PDF pages into chunks while preserving page-level metadata."""
        chunks: List[DocumentChunk] = []
        global_index = 0
        for page_number, page_text in pages_text:
            for chunk_text_value in self._splitter.split_text(page_text):
                chunks.append(
                    DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        text=chunk_text_value,
                        document_name=document_name,
                        file_type=file_type,
                        chunk_index=global_index,
                        page=page_number,
                        metadata={
                            "document_name": document_name,
                            "file_type": file_type,
                            "page": page_number,
                        },
                    )
                )
                global_index += 1
        return chunks
