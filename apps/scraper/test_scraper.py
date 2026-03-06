"""
Scraper integration test.

Requires both PostgreSQL and Redis running locally.

Usage:
    # From repo root:
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/awaqi_db \
    REDIS_URL=redis://localhost:6379/0 \
    uv run --package scraper python apps/scraper/test_scraper.py

What this tests:
  1. Crawler    — discovers PDF links from the MoR API
  2. Download   — fetches one PDF and returns bytes
  3. Processor  — extracts text and chunks it
  4. Pipeline   — runs download → chunk → store on the first 3 PDFs
  5. Lock       — second scrape is blocked while distributed lock is held
  6. Trigger    — writes scraper:trigger to Redis, poller picks it up
  7. Dedup      — same 3 PDFs on second pass add 0 new documents
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from unittest.mock import patch

from database.redis_client import redis_client
from scraper.config import REDIS_TRIGGER_KEY
from scraper.crawler import discover_all_pdfs, download_pdf
from scraper.main import (
    _set_job_status,
    guarded_scrape,
    run_scrape,
)
from scraper.processor import extract_and_chunk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("test_scraper")

SEP = "=" * 60


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _print_job_status(job_id: str) -> dict:
    raw = await redis_client.get(f"scraper:job:{job_id}")
    if raw:
        data = json.loads(raw)
        logger.info("Job status: %s", json.dumps(data, indent=2))
        return data
    logger.warning("No status found for job_id=%s", job_id)
    return {}


# ---------------------------------------------------------------------------
# Test 1: Crawler
# ---------------------------------------------------------------------------

async def test_crawler() -> list:
    logger.info("%s\nTEST 1 — Crawler: discover PDFs\n%s", SEP, SEP)
    import httpx
    from scraper.config import HTTP_TIMEOUT, HTTP_USER_AGENT, VERIFY_SSL

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": HTTP_USER_AGENT},
        verify=VERIFY_SSL,
    ) as client:
        pdfs = await discover_all_pdfs(client)

    logger.info("Found %d PDF links", len(pdfs))
    if pdfs:
        logger.info("First 3 PDFs:")
        for p in pdfs[:3]:
            logger.info("  [%s] %s", p.source_endpoint, p.title[:60] if p.title else "—")
    assert len(pdfs) > 0, "Crawler found zero PDFs — check network / API endpoints"
    return pdfs


# ---------------------------------------------------------------------------
# Test 2: Download + Processor
# ---------------------------------------------------------------------------

async def test_download_and_process(pdfs: list) -> None:
    logger.info("%s\nTEST 2 — Download + Processor\n%s", SEP, SEP)
    import httpx
    from scraper.config import HTTP_TIMEOUT, HTTP_USER_AGENT, VERIFY_SSL

    target = pdfs[0]
    logger.info("Downloading: %s", target.url)

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": HTTP_USER_AGENT},
        verify=VERIFY_SSL,
    ) as client:
        pdf_bytes = await download_pdf(client, target)

    assert pdf_bytes, "Download returned empty bytes"
    logger.info("Downloaded %d bytes", len(pdf_bytes))

    chunks = extract_and_chunk(pdf_bytes)
    first_words = len(chunks[0].content.split()) if chunks else 0
    logger.info("Extracted %d chunks (first chunk: %d words)", len(chunks), first_words)
    assert len(chunks) > 0, "Processor produced zero chunks"


# ---------------------------------------------------------------------------
# Test 3: Partial pipeline — ingests first 3 PDFs (fast, no full crawl)
# ---------------------------------------------------------------------------

async def test_partial_pipeline(pdfs: list) -> None:
    logger.info("%s\nTEST 3 — Partial pipeline (first 3 PDFs)\n%s", SEP, SEP)
    import httpx
    from database.db import AsyncSessionLocal
    from scraper.config import HTTP_TIMEOUT, HTTP_USER_AGENT, VERIFY_SSL
    from scraper.store import ingest_document

    sample = pdfs[:3]
    documents_new = 0

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": HTTP_USER_AGENT},
        verify=VERIFY_SSL,
    ) as client:
        for pdf in sample:
            logger.info("Processing: %s", pdf.url)
            pdf_bytes = await download_pdf(client, pdf)
            if not pdf_bytes:
                logger.warning("Skipping (empty download): %s", pdf.url)
                continue
            chunks = extract_and_chunk(pdf_bytes)
            logger.info("  → %d bytes, %d chunks", len(pdf_bytes), len(chunks))
            async with AsyncSessionLocal() as db:
                doc = await ingest_document(pdf, pdf_bytes, chunks, db)
                await db.commit()
                if doc is not None:
                    documents_new += 1
                    logger.info("  → NEW document stored (id=%s)", doc.id)
                else:
                    logger.info("  → DUPLICATE — already in DB, skipped")

    logger.info("Partial pipeline: %d/%d were new", documents_new, len(sample))


# ---------------------------------------------------------------------------
# Test 4: Distributed lock
# ---------------------------------------------------------------------------

async def test_lock() -> None:
    logger.info("%s\nTEST 4 — Distributed lock\n%s", SEP, SEP)
    from scraper.config import REDIS_LOCK_KEY, REDIS_LOCK_TTL

    await redis_client.set(REDIS_LOCK_KEY, "1", ex=REDIS_LOCK_TTL)
    job_id = str(uuid.uuid4())
    await guarded_scrape(job_id)
    status = await _print_job_status(job_id)
    assert status.get("status") == "already_running", (
        f"Expected already_running, got {status.get('status')}"
    )
    logger.info("Lock correctly blocked duplicate run")
    await redis_client.delete(REDIS_LOCK_KEY)


# ---------------------------------------------------------------------------
# Test 5: Manual trigger via Redis key
# ---------------------------------------------------------------------------

async def test_manual_trigger() -> None:
    logger.info("%s\nTEST 5 — Manual trigger via Redis\n%s", SEP, SEP)
    job_id = str(uuid.uuid4())
    payload = json.dumps({"job_id": job_id, "requested_at": "2026-01-01T06:00:00Z"})

    await redis_client.set(REDIS_TRIGGER_KEY, payload)
    raw = await redis_client.get(REDIS_TRIGGER_KEY)
    assert raw is not None, "Trigger key was not written to Redis"
    await redis_client.delete(REDIS_TRIGGER_KEY)
    data = json.loads(raw)
    picked_job_id = data.get("job_id", "manual")
    logger.info("Poller picked up trigger for job_id=%s", picked_job_id)

    async def _stub_run(jid: str) -> None:
        await _set_job_status(jid, status="completed", documents_found=3, documents_new=0)

    with patch("scraper.main.run_scrape", _stub_run):
        await guarded_scrape(picked_job_id)

    status = await _print_job_status(picked_job_id)
    assert status.get("status") == "completed", (
        f"Expected completed, got {status.get('status')}"
    )
    logger.info("Manual trigger test passed")


# ---------------------------------------------------------------------------
# Test 6: Deduplication
# ---------------------------------------------------------------------------

async def test_deduplication(pdfs: list) -> None:
    logger.info("%s\nTEST 6 — Deduplication (second pass on same 3 PDFs)\n%s", SEP, SEP)
    import httpx
    from database.db import AsyncSessionLocal
    from scraper.config import HTTP_TIMEOUT, HTTP_USER_AGENT, VERIFY_SSL
    from scraper.store import ingest_document

    sample = pdfs[:3]
    documents_new = 0

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": HTTP_USER_AGENT},
        verify=VERIFY_SSL,
    ) as client:
        for pdf in sample:
            pdf_bytes = await download_pdf(client, pdf)
            if not pdf_bytes:
                continue
            chunks = extract_and_chunk(pdf_bytes)
            async with AsyncSessionLocal() as db:
                doc = await ingest_document(pdf, pdf_bytes, chunks, db)
                await db.commit()
                if doc is not None:
                    documents_new += 1

    logger.info("Second pass added %d new documents (must be 0)", documents_new)
    assert documents_new == 0, (
        f"Expected 0 new documents on second pass, got {documents_new}"
    )
    logger.info("Deduplication test passed")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("Starting scraper integration tests")
    logger.info("DATABASE_URL = %s", os.getenv("DATABASE_URL", "(default)"))
    logger.info("REDIS_URL    = %s", os.getenv("REDIS_URL", "(default)"))

    try:
        pdfs = await test_crawler()
        await test_download_and_process(pdfs)
        await test_partial_pipeline(pdfs)
        await test_lock()
        await test_manual_trigger()
        await test_deduplication(pdfs)

        logger.info("\n%s\nAll tests passed!\n%s", SEP, SEP)
    except AssertionError as exc:
        logger.error("TEST FAILED: %s", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error during tests")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
