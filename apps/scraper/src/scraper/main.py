"""
Scraper entry point.

Runs two scheduled jobs (06:00 and 12:00 EAT) and polls Redis for manual
triggers from the admin panel. A Redis-based distributed lock prevents
overlapping runs.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
import uuid
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

_LOCK_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""

_LOCK_REFRESH_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
end
return 0
"""


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

async def _acquire_lock() -> str | None:
    """Try to acquire the Redis lock. Returns owner token on success."""
    token = str(uuid.uuid4())
    acquired = await redis_client.set(
        REDIS_LOCK_KEY, token, nx=True, ex=REDIS_LOCK_TTL
    )
    if acquired is not None and acquired is not False:
        return token
    return None


async def _refresh_lock(lock_token: str) -> bool:
    """Extend lock TTL only when this worker is still the owner."""
    refreshed = await redis_client.eval(
        _LOCK_REFRESH_SCRIPT,
        1,
        REDIS_LOCK_KEY,
        lock_token,
        str(REDIS_LOCK_TTL),
    )
    return bool(refreshed)


async def _release_lock(lock_token: str) -> None:
    """Release the lock only when this worker still owns it."""
    await redis_client.eval(
        _LOCK_RELEASE_SCRIPT,
        1,
        REDIS_LOCK_KEY,
        lock_token,
    )


async def _lock_heartbeat(lock_token: str, stop_event: asyncio.Event) -> None:
    """
    Keep refreshing the lock while the scrape runs.

    Without heartbeats, long scrape jobs can outlive REDIS_LOCK_TTL and allow
    a second worker to start; this keeps ownership alive until completion.
    """
    refresh_interval = max(5, REDIS_LOCK_TTL // 3)
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=refresh_interval)
            break
        except asyncio.TimeoutError:
            pass

        if not await _refresh_lock(lock_token):
            logger.warning("Lost lock ownership while scrape is still running")
            break


async def guarded_scrape(job_id: str) -> None:
    """Run a scrape job only if the lock is free."""
    lock_token = await _acquire_lock()
    if lock_token is None:
        logger.info("Scrape already running — skipping job %s", job_id)
        await _set_job_status(job_id, status="already_running")
        return

    heartbeat_stop = asyncio.Event()
    heartbeat_task = asyncio.create_task(_lock_heartbeat(lock_token, heartbeat_stop))
    try:
        await run_scrape(job_id)
    finally:
        heartbeat_stop.set()
        if not heartbeat_task.done():
            heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
        await _release_lock(lock_token)


# ---------------------------------------------------------------------------
# Scheduled entry-point
# ---------------------------------------------------------------------------

async def scheduled_scrape() -> None:
    """Called by APScheduler at the configured cron times."""
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
