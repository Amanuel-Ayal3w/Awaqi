"""
Scraper entry point.

Runs two scheduled jobs (06:00 and 12:00 EAT) and polls Redis for manual
triggers from the admin panel. A Redis-based distributed lock prevents
overlapping runs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.db import AsyncSessionLocal
from database.redis_client import redis_client
from scraper.config import (
    HTTP_TIMEOUT,
    HTTP_USER_AGENT,
    REDIS_JOB_PREFIX,
    REDIS_JOB_TTL,
    REDIS_LOCK_KEY,
    REDIS_LOCK_TTL,
    REDIS_TRIGGER_KEY,
    SCHEDULE_HOURS,
    SCHEDULE_TIMEZONE,
    TRIGGER_POLL_INTERVAL,
    VERIFY_SSL,
)
from scraper.crawler import PdfInfo, discover_all_pdfs, download_pdf
from scraper.processor import extract_and_chunk
from scraper.store import ingest_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("scraper")


# ---------------------------------------------------------------------------
# Job-status helpers (written to Redis so the API can read them)
# ---------------------------------------------------------------------------

async def _set_job_status(
    job_id: str,
    *,
    status: str,
    documents_found: int = 0,
    documents_new: int = 0,
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> None:
    payload = {
        "job_id": job_id,
        "status": status,
        "documents_found": documents_found,
        "documents_new": documents_new,
        "started_at": started_at,
        "finished_at": finished_at,
        "error": error,
    }
    await redis_client.set(
        f"{REDIS_JOB_PREFIX}{job_id}",
        json.dumps(payload),
        ex=REDIS_JOB_TTL,
    )


# ---------------------------------------------------------------------------
# Core scrape job
# ---------------------------------------------------------------------------

async def run_scrape(job_id: str) -> None:
    """Execute one full scrape cycle for all target pages."""
    started_at = datetime.now(timezone.utc).isoformat()
    await _set_job_status(job_id, status="running", started_at=started_at)
    logger.info("Scrape job %s started", job_id)

    documents_found = 0
    documents_new = 0

    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": HTTP_USER_AGENT},
            verify=VERIFY_SSL,
        ) as client:
            pdfs: list[PdfInfo] = await discover_all_pdfs(client)
            documents_found = len(pdfs)

            for pdf in pdfs:
                try:
                    pdf_bytes = await download_pdf(client, pdf)
                    if pdf_bytes is None:
                        continue

                    chunks = extract_and_chunk(pdf_bytes)

                    async with AsyncSessionLocal() as db:
                        doc = await ingest_document(pdf, pdf_bytes, chunks, db)
                        await db.commit()
                        if doc is not None:
                            documents_new += 1
                except Exception:
                    logger.exception("Error processing %s", pdf.url)

        finished_at = datetime.now(timezone.utc).isoformat()
        await _set_job_status(
            job_id,
            status="completed",
            documents_found=documents_found,
            documents_new=documents_new,
            started_at=started_at,
            finished_at=finished_at,
        )
        logger.info(
            "Scrape job %s completed — found=%d new=%d",
            job_id,
            documents_found,
            documents_new,
        )

    except Exception as exc:
        finished_at = datetime.now(timezone.utc).isoformat()
        await _set_job_status(
            job_id,
            status="failed",
            documents_found=documents_found,
            documents_new=documents_new,
            started_at=started_at,
            finished_at=finished_at,
            error=str(exc),
        )
        logger.exception("Scrape job %s failed: %s", job_id, exc)


# ---------------------------------------------------------------------------
# Distributed lock
# ---------------------------------------------------------------------------

async def _acquire_lock() -> bool:
    """Try to acquire the Redis lock. Returns True on success."""
    acquired = await redis_client.set(
        REDIS_LOCK_KEY, "1", nx=True, ex=REDIS_LOCK_TTL
    )
    return acquired is not None and acquired is not False


async def _release_lock() -> None:
    await redis_client.delete(REDIS_LOCK_KEY)


async def guarded_scrape(job_id: str) -> None:
    """Run a scrape job only if the lock is free."""
    if not await _acquire_lock():
        logger.info("Scrape already running — skipping job %s", job_id)
        await _set_job_status(job_id, status="already_running")
        return
    try:
        await run_scrape(job_id)
    finally:
        await _release_lock()


# ---------------------------------------------------------------------------
# Scheduled entry-point
# ---------------------------------------------------------------------------

async def scheduled_scrape() -> None:
    """Called by APScheduler at the configured cron times."""
    import uuid
    job_id = str(uuid.uuid4())
    logger.info("Scheduled scrape triggered — job_id=%s", job_id)
    await guarded_scrape(job_id)


# ---------------------------------------------------------------------------
# Manual-trigger poller
# ---------------------------------------------------------------------------

async def poll_trigger_loop() -> None:
    """
    Continuously poll Redis for a manual trigger from the admin API.
    When found, run a scrape immediately (respecting the lock).
    """
    logger.info("Trigger poller started (interval=%ds)", TRIGGER_POLL_INTERVAL)
    while True:
        try:
            raw = await redis_client.get(REDIS_TRIGGER_KEY)
            if raw:
                await redis_client.delete(REDIS_TRIGGER_KEY)
                try:
                    data = json.loads(raw)
                    job_id = data.get("job_id", "manual")
                except (json.JSONDecodeError, TypeError):
                    job_id = "manual"
                logger.info("Manual trigger received — job_id=%s", job_id)
                await guarded_scrape(job_id)
        except aioredis.RedisError as exc:
            logger.warning("Redis error in trigger poller: %s", exc)
        await asyncio.sleep(TRIGGER_POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def async_main() -> None:
    scheduler = AsyncIOScheduler(timezone=SCHEDULE_TIMEZONE)
    for hour in SCHEDULE_HOURS:
        scheduler.add_job(
            scheduled_scrape,
            CronTrigger(hour=hour, minute=0, timezone=SCHEDULE_TIMEZONE),
            id=f"scrape_{hour:02d}00",
            replace_existing=True,
        )
    scheduler.start()
    logger.info(
        "Scheduler started — jobs at %s EAT",
        ", ".join(f"{h:02d}:00" for h in SCHEDULE_HOURS),
    )

    await poll_trigger_loop()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
