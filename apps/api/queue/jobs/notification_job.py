"""RQ job: proactive notification check with Redis progress reporting.

Queries newly-indexed documents, evaluates relevance via LLM, and sends
email (Mailtrap) and SMS (GeezSMS) to configured recipients.
"""

from __future__ import annotations

import asyncio
import logging

from apps.api.queue.progress import publish_progress

logger = logging.getLogger(__name__)


def run_notification_job(
    job_id: str,
    trigger: str = "manual",
) -> dict[str, int]:
    """RQ job function: run one notification check cycle with progress updates."""

    publish_progress(job_id, 5, "Initializing", "running")

    async def _run() -> dict[str, int]:
        from apps.api.notification_service import check_and_send_notifications

        return await check_and_send_notifications(trigger=trigger)

    try:
        publish_progress(job_id, 20, "Checking for new documents", "running")
        stats = asyncio.run(_run())
        publish_progress(job_id, 100, "Done", "done")
        logger.info("notification_job_done job_id=%s stats=%s", job_id, stats)
        return stats
    except Exception as exc:
        logger.exception("notification_job_failed job_id=%s", job_id)
        publish_progress(job_id, 0, f"Failed: {exc!s:.120}", "failed")
        raise
