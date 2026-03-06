"""Persist scraped documents and chunks to PostgreSQL."""

from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
)
from scraper.crawler import PdfInfo
from scraper.processor import Chunk

logger = logging.getLogger(__name__)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def is_duplicate(file_hash: str, db: AsyncSession) -> bool:
    """Return True if a document with this hash is already stored."""
    result = await db.execute(
        select(Document.id).where(Document.file_hash == file_hash).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def ingest_document(
    pdf_info: PdfInfo,
    pdf_bytes: bytes,
    chunks: list[Chunk],
    db: AsyncSession,
) -> Document | None:
    """
    Store a document and its chunks. Returns the Document if new, None if
    it was a duplicate or had no extractable content.
    """
    file_hash = _sha256(pdf_bytes)

    if await is_duplicate(file_hash, db):
        logger.info("Skipping duplicate: %s (hash=%s…)", pdf_info.title, file_hash[:12])
        return None

    if not chunks:
        logger.warning("No chunks for %s — storing as failed", pdf_info.title)
        doc = Document(
            id=uuid.uuid4(),
            title=pdf_info.title,
            source_url=pdf_info.url,
            file_hash=file_hash,
            status=DocumentStatus.FAILED,
        )
        db.add(doc)
        await db.flush()
        return doc

    doc = Document(
        id=uuid.uuid4(),
        title=pdf_info.title,
        source_url=pdf_info.url,
        file_hash=file_hash,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()

    for chunk in chunks:
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=None,
                chunk_metadata=chunk.metadata or {},
            )
        )

    doc.status = DocumentStatus.INDEXED
    await db.flush()

    logger.info(
        "Ingested %s → %d chunk(s) (doc_id=%s)",
        pdf_info.title,
        len(chunks),
        doc.id,
    )
    return doc
