"""
Document ingestion orchestrator.

Single entry point for both admin upload and future scraper.
Pipeline: extract text (Gemini Flash) → chunk → embed → store in DB.
"""

from __future__ import annotations

import logging
import uuid

from database.models.document import DocumentChunk
from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.chunker import chunk_pages
from ai_engine.embedder import embed_texts
from ai_engine.extractor import extract_text

logger = logging.getLogger(__name__)


async def ingest_pdf(
    pdf_bytes: bytes,
    document_id: uuid.UUID,
    db: AsyncSession,
    client: genai.Client | None = None,
) -> int:
    """
    Process a PDF end-to-end: extract → chunk → embed → store.

    This is the **single entry point** for document ingestion.
    Both the admin upload endpoint and a future scraper should call this.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF.
        document_id: UUID of the parent Document record (must already exist).
        db: Active async database session.
        client: Optional pre-configured genai.Client.

    Returns:
        Number of chunks created and stored.

    Raises:
        ValueError: If extraction yields no text.
        Exception: Propagated from Gemini API or database.
    """
    if client is None:
        client = genai.Client()

    # 1. Extract text from PDF pages via Gemini Flash
    logger.info("Starting ingestion for document %s", document_id)
    pages = await extract_text(pdf_bytes, client=client)

    non_empty_pages = [p for p in pages if p.text.strip()]
    if not non_empty_pages:
        raise ValueError("No text could be extracted from the PDF")

    logger.info(
        "Extracted text from %d/%d pages", len(non_empty_pages), len(pages)
    )

    # 2. Chunk the extracted text
    chunks = chunk_pages(non_empty_pages)
    if not chunks:
        raise ValueError("Text chunking produced no chunks")

    logger.info("Created %d chunks", len(chunks))

    # 3. Generate embeddings for all chunks
    chunk_texts = [c.content for c in chunks]
    embeddings = await embed_texts(chunk_texts, client=client)

    # 4. Store chunks with embeddings in the database
    for chunk, embedding in zip(chunks, embeddings):
        db_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            chunk_index=chunk.index,
            content=chunk.content,
            embedding=embedding,
            chunk_metadata=chunk.metadata,
        )
        db.add(db_chunk)

    await db.flush()
    logger.info(
        "Stored %d chunks with embeddings for document %s",
        len(chunks), document_id,
    )

    return len(chunks)
