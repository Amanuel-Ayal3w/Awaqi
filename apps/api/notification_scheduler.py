"""APScheduler wiring for the proactive notification check.

Runs on a configurable interval (default: every hour). The interval can be
changed via the admin PATCH /v1/admin/notifications/config endpoint which
calls ``apply_notification_scheduler_config`` to reschedule live.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apps.api.notification_service import (
    check_and_send_notifications,
    get_notification_settings,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

JOB_ID = "notification_check"
TIMEZONE = "Africa/Addis_Ababa"


async def _scheduled_notification_job() -> None:
    try:
        stats = await check_and_send_notifications(trigger="scheduled")
        logger.info("scheduled_notification_check stats=%s", stats)
    except Exception:
        logger.exception("scheduled_notification_check_failed")


def get_notification_scheduler(app: "FastAPI") -> AsyncIOScheduler | None:
    return getattr(app.state, "notification_scheduler", None)


async def apply_notification_scheduler_config(app: "FastAPI") -> None:
    """Start, stop, or reschedule the interval job from ``notification_config``."""
    settings = await get_notification_settings()
    scheduler: AsyncIOScheduler | None = getattr(app.state, "notification_scheduler", None)

    if scheduler is None:
        if settings.scheduler_enabled:
            scheduler = AsyncIOScheduler(timezone=TIMEZONE)
            scheduler.start()
            app.state.notification_scheduler = scheduler
        else:
            return
    elif not settings.scheduler_enabled:
        scheduler.shutdown(wait=False)
        app.state.notification_scheduler = None
        logger.info("APScheduler stopped (notification disabled)")
        return

    scheduler.add_job(
        _scheduled_notification_job,
        "interval",
        hours=settings.interval_hours,
        id=JOB_ID,
        replace_existing=True,
    )
    logger.info(
        "APScheduler notification check scheduled every %dh",
        settings.interval_hours,
    )


def get_notification_next_run_time(app: "FastAPI") -> str | None:
    scheduler = get_notification_scheduler(app)
    if scheduler is None:
        return None
    job = scheduler.get_job(JOB_ID)
    if job is None or job.next_run_time is None:
        return None
    return job.next_run_time.isoformat()
