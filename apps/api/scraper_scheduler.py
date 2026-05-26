"""APScheduler wiring for MoR daily scrape (dynamic reschedule from DB config)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apps.api.scraper_service import execute_scrape_run, get_scraper_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

JOB_ID = "mor_daily_scrape"
TIMEZONE = "Africa/Addis_Ababa"


async def _scheduled_scrape_job() -> None:
    try:
        stats = await execute_scrape_run(trigger="scheduled")
        logger.info("scheduled_mor_scrape stats=%s", stats)
    except Exception:
        logger.exception("scheduled_mor_scrape_failed")


def get_scheduler(app: "FastAPI") -> AsyncIOScheduler | None:
    return getattr(app.state, "scraper_scheduler", None)


async def apply_scheduler_config(app: "FastAPI") -> None:
    """Start, stop, or reschedule the cron job from ``scraper_config``."""
    settings = await get_scraper_settings()
    scheduler: AsyncIOScheduler | None = getattr(app.state, "scraper_scheduler", None)

    if scheduler is None:
        if settings.scheduler_enabled:
            scheduler = AsyncIOScheduler(timezone=TIMEZONE)
            scheduler.start()
            app.state.scraper_scheduler = scheduler
        else:
            return
    elif not settings.scheduler_enabled:
        scheduler.shutdown(wait=False)
        app.state.scraper_scheduler = None
        logger.info("APScheduler stopped (scraper disabled)")
        return

    scheduler.add_job(
        _scheduled_scrape_job,
        "cron",
        hour=settings.cron_hour,
        minute=settings.cron_minute,
        id=JOB_ID,
        replace_existing=True,
    )
    logger.info(
        "APScheduler mor scrape scheduled at %02d:%02d %s",
        settings.cron_hour,
        settings.cron_minute,
        TIMEZONE,
    )


def get_next_run_time(app: "FastAPI") -> str | None:
    scheduler = get_scheduler(app)
    if scheduler is None:
        return None
    job = scheduler.get_job(JOB_ID)
    if job is None or job.next_run_time is None:
        return None
    return job.next_run_time.isoformat()
