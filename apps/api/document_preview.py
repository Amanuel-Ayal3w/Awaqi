"""Build admin document content previews (chunks vs live PDF extract)."""

from __future__ import annotations

import os
import uuid

from ai_engine.document_processor import extract_bytes, get_tesseract_languages, resolve_ocr_langs
from ai_engine.text_quality import assess_extracted_text
from ai_engine.scraper.storage import read_document_pdf
from database.models.document import Document, DocumentChunk, DocumentStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def load_document_bytes(doc: Document) -> bytes | None:
    data = read_document_pdf(doc.storage_path)
    if data:
        return data
    return None


async def build_content_preview(db: AsyncSession, doc: Document) -> dict:
    """Return serializable preview payload for admin UI."""
    status = str(getattr(doc.status, "value", doc.status))
    chunk_rows = (
        await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
    ).scalars().all()

    pages: list[dict] = []
    text_source = "empty"
    full_text = ""
    requires_manual_review = False
    review_reason: str | None = None
    mean_ocr_confidence: float | None = None
    text_quality_warning = False
    text_quality_reasons: list[str] = []

    if chunk_rows and status == DocumentStatus.INDEXED.value:
        full_text = "\n\n".join(c.content for c in chunk_rows if c.content.strip())
        text_source = "chunks"
        assessment = assess_extracted_text(full_text)
        text_quality_warning = assessment.is_likely_corrupt
        text_quality_reasons = list(assessment.reasons)
    else:
        pdf_bytes = await load_document_bytes(doc)
        if pdf_bytes:
            outcome = await extract_bytes(
                pdf_bytes,
                mime_type="application/pdf",
                filename=f"{doc.id}.pdf",
                genai_client=None,
            )
            pages = [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "extraction_mode": p.extraction_mode,
                    "ocr_mean_confidence": p.ocr_mean_confidence,
                }
                for p in outcome.pages
            ]
            full_text = "\n\n".join(
                f"--- Page {p['page_number']} ({p['extraction_mode']}) ---\n{p['text']}"
                for p in pages
                if p["text"].strip()
            )
            text_source = "live_extract"
            requires_manual_review = outcome.requires_manual_review
            review_reason = outcome.review_reason
            ocr_vals = [
                p.ocr_mean_confidence
                for p in outcome.pages
                if p.ocr_mean_confidence is not None
            ]
            if ocr_vals:
                mean_ocr_confidence = sum(ocr_vals) / len(ocr_vals)
            assessment = assess_extracted_text(full_text)
            text_quality_warning = assessment.is_likely_corrupt
            text_quality_reasons = list(assessment.reasons)

    stored = read_document_pdf(doc.storage_path) is not None
    tess_langs = sorted(get_tesseract_languages())

    return {
        "doc_id": str(doc.id),
        "title": doc.title,
        "status": status,
        "ingest_error": doc.ingest_error,
        "source_url": doc.source_url,
        "storage_path": doc.storage_path,
        "has_stored_pdf": stored,
        "text_source": text_source,
        "pages": pages,
        "full_text": full_text,
        "chunk_count": len(chunk_rows),
        "requires_manual_review": requires_manual_review,
        "review_reason": review_reason,
        "mean_ocr_confidence": mean_ocr_confidence,
        "text_quality_warning": text_quality_warning,
        "text_quality_reasons": text_quality_reasons,
        "tesseract_langs_installed": tess_langs,
        "ocr_langs_configured": os.getenv("OCR_LANGS", "eng+amh"),
        "ocr_langs_resolved": resolve_ocr_langs(),
    }


async def get_document_or_404(db: AsyncSession, doc_id: str) -> Document:
    try:
        uid = uuid.UUID(doc_id)
    except ValueError as e:
        raise ValueError("doc_id must be a valid UUID") from e
    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise LookupError("not_found")
    return doc
