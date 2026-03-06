"""Extract text from PDFs and split into overlapping chunks."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

import pdfplumber

from scraper.config import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """One text chunk ready for storage."""

    chunk_index: int
    content: str
    metadata: dict = field(default_factory=dict)


def extract_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF, page by page."""
    text_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception:
        logger.exception("pdfplumber failed to open PDF")
        return ""

    return "\n\n".join(text_parts)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Split text into overlapping chunks of approximately *chunk_size* tokens.

    Tokens are approximated as whitespace-split words (good enough for
    multilingual content until a proper tokenizer is added).
    """
    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        content = " ".join(chunk_words)
        chunks.append(Chunk(chunk_index=idx, content=content))
        idx += 1
        start += chunk_size - overlap

    return chunks


def extract_and_chunk(pdf_bytes: bytes) -> list[Chunk]:
    """Full pipeline: PDF bytes → text → chunks."""
    text = extract_text(pdf_bytes)
    if not text.strip():
        logger.warning("No text extracted from PDF")
        return []
    chunks = chunk_text(text)
    logger.info("Extracted %d chunk(s) from PDF (%d chars)", len(chunks), len(text))
    return chunks
