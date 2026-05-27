"""APScheduler wiring for Telegram daily scrape (dynamic reschedule from DB config)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apps.api.telegram_service import execute_telegram_scrape_run, get_telegram_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

JOB_ID = "telegram_daily_scrape"
TIMEZONE = "Africa/Addis_Ababa"


async def _scheduled_telegram_job() -> None:
    try:
        stats = await execute_telegram_scrape_run(trigger="scheduled")
        logger.info("scheduled_telegram_scrape stats=%s", stats)
    except Exception:
        logger.exception("scheduled_telegram_scrape_failed")


def get_telegram_scheduler(app: "FastAPI") -> AsyncIOScheduler | None:
    return getattr(app.state, "telegram_scheduler", None)


async def apply_telegram_scheduler_config(app: "FastAPI") -> None:
    """Start, stop, or reschedule the Telegram cron job from ``telegram_scraper_config``."""
    settings = await get_telegram_settings()
    scheduler: AsyncIOScheduler | None = getattr(app.state, "telegram_scheduler", None)

    if scheduler is None:
        if settings.scheduler_enabled:
            scheduler = AsyncIOScheduler(timezone=TIMEZONE)
            scheduler.start()
            app.state.telegram_scheduler = scheduler
        else:
            return
    elif not settings.scheduler_enabled:
        scheduler.shutdown(wait=False)
        app.state.telegram_scheduler = None
        logger.info("Telegram APScheduler stopped (scheduler disabled)")
        return

    scheduler.add_job(
        _scheduled_telegram_job,
        "cron",
        hour=settings.cron_hour,
        minute=settings.cron_minute,
        id=JOB_ID,
        replace_existing=True,
    )
    logger.info(
        "APScheduler telegram scrape scheduled at %02d:%02d %s",
        settings.cron_hour,
        settings.cron_minute,
        TIMEZONE,
    )


def get_telegram_next_run_time(app: "FastAPI") -> str | None:
    scheduler = get_telegram_scheduler(app)
    if scheduler is None:
        return None
    job = scheduler.get_job(JOB_ID)
    if job is None or job.next_run_time is None:
        return None
    return job.next_run_time.isoformat()
