"""
Ingestion pipeline integration test.

Tests the full extract → chunk → embed → store pipeline end-to-end.
Requires: GOOGLE_API_KEY, DATABASE_URL (in .env or env vars).

Usage (from repo root):
    uv run python test_ingest.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid

# Load .env before anything else
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("test_ingest")
SEP = "=" * 60


def fetch_test_pdf() -> bytes:
    """
    Load a test PDF. Uses /tmp/test_doc.pdf if present (pre-downloaded),
    otherwise downloads a small public sample PDF.
    """
    import httpx

    local_path = "/tmp/test_doc.pdf"
    if os.path.exists(local_path):
        with open(local_path, "rb") as f:
            data = f.read()
        logger.info("Using local test PDF (%d bytes): %s", len(data), local_path)
        return data

    logger.info("Downloading sample PDF...")
    url = "https://pdfobject.com/pdf/sample.pdf"
    resp = httpx.get(url, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    pdf_bytes = resp.content
    with open(local_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info("Downloaded %d bytes → %s", len(pdf_bytes), local_path)
    return pdf_bytes


async def test_extract(pdf_bytes: bytes) -> list:
    """Test 1: PDF text extraction via Gemini Flash."""
    logger.info("%s\nTEST 1 — Extract text (Gemini Flash)\n%s", SEP, SEP)
    from ai_engine.extractor import extract_text
    pages = await extract_text(pdf_bytes)
    non_empty = [p for p in pages if p.text.strip()]
    logger.info(
        "Extracted %d/%d pages with text (first 200 chars): %s...",
        len(non_empty), len(pages),
        non_empty[0].text[:200] if non_empty else "(none)",
    )
    assert len(non_empty) > 0, "No text extracted from PDF"
    logger.info("TEST 1 PASSED")
    return pages


async def test_chunk(pages: list) -> list:
    """Test 2: Chunking extracted pages."""
    logger.info("%s\nTEST 2 — Chunk text\n%s", SEP, SEP)
    from ai_engine.chunker import chunk_pages
    non_empty = [p for p in pages if p.text.strip()]
    chunks = chunk_pages(non_empty)
    logger.info(
        "Created %d chunks. First chunk (%d chars): %s...",
        len(chunks),
        len(chunks[0].content) if chunks else 0,
        chunks[0].content[:150] if chunks else "(none)",
    )
    assert len(chunks) > 0, "Chunking produced no chunks"
    logger.info("TEST 2 PASSED")
    return chunks


async def test_embed(chunks: list) -> list:
    """Test 3: Embedding generation via Gemini Embedding API."""
    logger.info("%s\nTEST 3 — Embed chunks (Gemini Embedding)\n%s", SEP, SEP)
    from ai_engine.embedder import embed_texts
    # Only embed first 3 chunks to keep test fast
    sample = chunks[:3]
    texts = [c.content for c in sample]
    embeddings = await embed_texts(texts)
    logger.info(
        "Generated %d embeddings, each %d-dimensional. First 5 values: %s",
        len(embeddings),
        len(embeddings[0]) if embeddings else 0,
        embeddings[0][:5] if embeddings else [],
    )
    assert len(embeddings) == len(sample), "Embedding count mismatch"
    assert len(embeddings[0]) == 1024, f"Expected 1024-dim, got {len(embeddings[0])}"
    logger.info("TEST 3 PASSED")
    return embeddings


async def test_store(pdf_bytes: bytes) -> None:
    """Test 4: Full pipeline via ingest_pdf + DB persistence."""
    logger.info("%s\nTEST 4 — Full ingest_pdf → DB store\n%s", SEP, SEP)
    import hashlib

    from ai_engine.ingest import ingest_pdf
    from database.db import AsyncSessionLocal
    from database.models.document import Document, DocumentStatus
    from sqlalchemy import select

    doc_id = uuid.uuid4()
    content_hash = hashlib.sha256(pdf_bytes).hexdigest()

    async with AsyncSessionLocal() as db:
        # Create a temporary Document row
        doc = Document(
            id=doc_id,
            title="[TEST] Ingestion Test Doc",
            source_url="https://test.example.com/test.pdf",
            content_hash=content_hash + "_test",  # avoid collision with real docs
            status=DocumentStatus.PENDING,
        )
        db.add(doc)
        await db.flush()

        chunk_count = await ingest_pdf(pdf_bytes, doc_id, db)
        doc.status = DocumentStatus.INDEXED
        await db.commit()

    logger.info("Stored %d chunks for document %s", chunk_count, doc_id)
    assert chunk_count > 0, "ingest_pdf stored 0 chunks"

    # Verify chunks are in DB
    async with AsyncSessionLocal() as db:
        from database.models.document import DocumentChunk
        result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
        )
        stored_chunks = result.scalars().all()
        logger.info(
            "Verified %d chunks in DB. First chunk embedding dim: %d",
            len(stored_chunks),
            len(stored_chunks[0].embedding) if stored_chunks and stored_chunks[0].embedding else 0,
        )
        assert len(stored_chunks) == chunk_count, "Chunk count mismatch in DB"

    logger.info("TEST 4 PASSED — %d chunks stored and verified in PostgreSQL", chunk_count)


async def main() -> None:
    logger.info("Starting ingestion pipeline tests")
    logger.info("GOOGLE_API_KEY = %s...", os.getenv("GOOGLE_API_KEY", "MISSING")[:20])
    logger.info("DATABASE_URL   = %s", os.getenv("DATABASE_URL", "(default)"))

    try:
        pdf_bytes = fetch_test_pdf()
        pages = await test_extract(pdf_bytes)
        chunks = await test_chunk(pages)
        await test_embed(chunks)
        await test_store(pdf_bytes)

        logger.info("\n%s\nAll ingestion tests passed!\n%s", SEP, SEP)
    except AssertionError as exc:
        logger.error("TEST FAILED: %s", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
