"""
Document ingestion orchestrator (Phase A).

**Transaction contract (ARCHITECTURE.md §2.1):** Extraction and embedding run outside
the DB-critical section. The replace of searchable rows is **one logical unit**:
``DELETE FROM document_chunks WHERE document_id = :id`` followed by bulk insert of
new rows and a final ``documents`` status update in a **single** database commit so
readers never see doubled chunks for the same document version.

**Entry points:** ``ingest_bytes_for_document`` (bytes + MIME), ``ingest_plain_text``,
and legacy ``ingest_pdf`` (admin PDF uploads).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from database.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    ProcessingStage,
)
from google import genai
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.chunking_service import ChunkingService
from ai_engine.document_processor import extract_bytes
from ai_engine.e5_embedder import embed_passages_sync, get_tokenizer
from ai_engine.extractor import PageText
from ai_engine.heuristics import (
    guess_article_number_from_text,
    guess_proclamation_number,
)
from ai_engine.text_utils import normalize_unicode_nfc

logger = logging.getLogger(__name__)


def _stage_value(stage: ProcessingStage) -> str:
    return stage.value


async def _persist_stage(db: AsyncSession, doc: Document, stage: str | None) -> None:
    doc.processing_stage = stage
    await db.flush()
    await db.commit()


async def _persist_status(
    db: AsyncSession,
    doc: Document,
    status: DocumentStatus,
    *,
    stage: str | None = None,
    error: str | None = None,
) -> None:
    doc.status = status
    doc.processing_stage = stage
    doc.ingest_error = error
    await db.flush()
    await db.commit()


async def _ingest_from_pages(
    db: AsyncSession,
    doc: Document,
    pages: list[PageText],
) -> int:
    """Chunk, embed, replace chunks, and mark indexed. Caller sets status=processing."""
    await _persist_stage(db, doc, _stage_value(ProcessingStage.CHUNKING))

    tokenizer = get_tokenizer()
    normalized_pages = [
        PageText(
            page_number=p.page_number,
            text=normalize_unicode_nfc(p.text),
            extraction_mode=p.extraction_mode,
            ocr_mean_confidence=p.ocr_mean_confidence,
        )
        for p in pages
        if p.text.strip()
    ]
    if not normalized_pages:
        raise ValueError("No text content to chunk")

    chunks = ChunkingService.chunk_pages_tokenized(normalized_pages, tokenizer)
    if not chunks:
        raise ValueError("Chunking produced no chunks")

    await _persist_stage(db, doc, _stage_value(ProcessingStage.EMBEDDING))
    texts = [c.content for c in chunks]
    embeddings = await asyncio.to_thread(embed_passages_sync, texts)

    if len(embeddings) != len(chunks):
        raise RuntimeError("Embedding count does not match chunk count")

    await _persist_stage(db, doc, _stage_value(ProcessingStage.INDEXING))

    now = datetime.now(timezone.utc)
    if doc.proclamation_number is None:
        doc.proclamation_number = guess_proclamation_number(doc.title)

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

    for chunk, embedding in zip(chunks, embeddings):
        chunk_uuid = uuid.uuid4()
        article = guess_article_number_from_text(chunk.content)
        meta = {
            **chunk.metadata,
            "document_id": str(doc.id),
            "chunk_id": str(chunk_uuid),
            "source_url": doc.source_url or "",
            "document_title": doc.title,
            "proclamation_number": doc.proclamation_number or "",
            "article_number": article or "",
            "effective_date": doc.effective_date.isoformat()
            if doc.effective_date
            else "",
            "language": doc.language,
            "created_at": now.isoformat(),
        }
        db.add(
            DocumentChunk(
                id=chunk_uuid,
                document_id=doc.id,
                chunk_index=chunk.index,
                content=chunk.content,
                embedding=embedding,
                chunk_metadata=meta,
            )
        )

    doc.status = DocumentStatus.INDEXED
    doc.processing_stage = None
    doc.ingest_error = None
    await db.flush()
    await db.commit()

    logger.info("Indexed document %s with %d chunks", doc.id, len(chunks))
    return len(chunks)


async def ingest_bytes_for_document(
    db: AsyncSession,
    document: Document,
    file_bytes: bytes,
    *,
    mime_type: str | None,
    filename: str | None,
    genai_client: genai.Client | None = None,
) -> int:
    """
    Full pipeline: extract → (optional manual-review gate) → chunk → embed → store.

    Returns number of chunks stored (0 when manual review is required).
    """
    result = await db.execute(select(Document).where(Document.id == document.id))
    doc = result.scalar_one()
    doc.byte_size = len(file_bytes)
    doc.status = DocumentStatus.PROCESSING
    doc.processing_stage = _stage_value(ProcessingStage.PARSING)
    doc.ingest_error = None
    await db.flush()
    await db.commit()

    logger.info(
        "Ingest start doc_id=%s bytes=%d mime=%r file=%r",
        doc.id,
        len(file_bytes),
        mime_type,
        filename,
    )

    outcome = await extract_bytes(
        file_bytes,
        mime_type=mime_type,
        filename=filename,
        genai_client=genai_client,
    )

    if outcome.review_reason == "empty_extract" or not any(
        p.text.strip() for p in outcome.pages
    ):
        await _persist_status(
            db,
            doc,
            DocumentStatus.FAILED,
            stage=None,
            error="empty_extract",
        )
        raise ValueError("No text could be extracted from the document")

    if outcome.requires_manual_review:
        await _persist_status(
            db,
            doc,
            DocumentStatus.REQUIRES_MANUAL_REVIEW,
            stage=None,
            error=outcome.review_reason or "manual_review",
        )
        logger.warning(
            "Document %s requires manual review (%s)", doc.id, outcome.review_reason
        )
        return 0

    return await _ingest_from_pages(db, doc, outcome.pages)


async def ingest_plain_text(
    db: AsyncSession,
    document: Document,
    text: str,
) -> int:
    """Ingest corrected plain text (bypasses PDF/OCR) for AWA-9 follow-up."""
    result = await db.execute(select(Document).where(Document.id == document.id))
    doc = result.scalar_one()
    doc.status = DocumentStatus.PROCESSING
    doc.processing_stage = _stage_value(ProcessingStage.PARSING)
    doc.ingest_error = None
    await db.flush()
    await db.commit()

    pages = [
        PageText(
            page_number=1,
            text=normalize_unicode_nfc(text),
            extraction_mode="manual_txt",
            ocr_mean_confidence=None,
        )
    ]
    if not pages[0].text.strip():
        await _persist_status(
            db,
            doc,
            DocumentStatus.FAILED,
            stage=None,
            error="empty_text",
        )
        raise ValueError("Empty text")

    return await _ingest_from_pages(db, doc, pages)


async def ingest_pdf(
    pdf_bytes: bytes,
    document_id: uuid.UUID,
    db: AsyncSession,
    client: genai.Client | None = None,
) -> int:
    """Backward-compatible PDF ingestion entry point."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one()
    return await ingest_bytes_for_document(
        db,
        doc,
        pdf_bytes,
        mime_type="application/pdf",
        filename="upload.pdf",
        genai_client=client,
    )
