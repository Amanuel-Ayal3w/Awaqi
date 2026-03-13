"""
Text chunker for the ingestion pipeline.

Splits extracted page texts into overlapping chunks suitable for embedding
and retrieval. Each chunk carries metadata about which page(s) it spans.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ai_engine.extractor import PageText

logger = logging.getLogger(__name__)

# Target ~1000 tokens ≈ 4000 characters
DEFAULT_CHUNK_SIZE = 4000
# Overlap ~100 tokens ≈ 400 characters
DEFAULT_OVERLAP = 400


@dataclass
class Chunk:
    """A text chunk ready for embedding."""
    index: int
    content: str
    metadata: dict = field(default_factory=dict)


def chunk_pages(
    pages: list[PageText],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """
    Split page texts into overlapping chunks.

    Strategy:
    1. Concatenate all page texts with page markers.
    2. Slide a window of `chunk_size` chars with `overlap`.
    3. Each chunk records the page range it spans.

    Args:
        pages: Ordered list of PageText from the extractor.
        chunk_size: Target chunk size in characters.
        overlap: Overlap between consecutive chunks in characters.

    Returns:
        List of Chunk objects with 0-indexed chunk_index.
    """
    if not pages:
        return []

    # Build a flat text with page boundary tracking
    full_text = ""
    # Map character offset → page number
    page_boundaries: list[tuple[int, int]] = []  # (start_offset, page_number)
    for page in pages:
        if not page.text.strip():
            continue
        page_boundaries.append((len(full_text), page.page_number))
        full_text += page.text + "\n\n"

    if not full_text.strip():
        logger.warning("No text content to chunk")
        return []

    # Sliding window chunking
    chunks: list[Chunk] = []
    step = max(chunk_size - overlap, 1)
    start = 0
    chunk_idx = 0

    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        content = full_text[start:end].strip()

        if not content:
            start += step
            continue

        # Determine which pages this chunk spans
        chunk_pages_set = _pages_for_range(page_boundaries, start, end)

        chunks.append(Chunk(
            index=chunk_idx,
            content=content,
            metadata={
                "pages": sorted(chunk_pages_set),
                "char_start": start,
                "char_end": end,
            },
        ))
        chunk_idx += 1
        start += step

    logger.info(
        "Chunked %d chars into %d chunks (size=%d, overlap=%d)",
        len(full_text), len(chunks), chunk_size, overlap,
    )
    return chunks


def _pages_for_range(
    boundaries: list[tuple[int, int]],
    start: int,
    end: int,
) -> set[int]:
    """Find which page numbers a character range spans."""
    pages: set[int] = set()
    for i, (offset, page_num) in enumerate(boundaries):
        # Next boundary (or end of text)
        next_offset = boundaries[i + 1][0] if i + 1 < len(boundaries) else float("inf")
        # Check if this page overlaps with [start, end)
        if offset < end and next_offset > start:
            pages.add(page_num)
    return pages
