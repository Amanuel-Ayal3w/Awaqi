"""RQ job: Telegram channel scraper with Redis progress reporting."""

from __future__ import annotations

import asyncio
import logging

from apps.api.queue.progress import publish_progress

logger = logging.getLogger(__name__)


def run_telegram_scrape_job(
    job_id: str,
    trigger: str = "manual",
    channel_username: str | None = None,
    scrape_since: str | None = None,
    max_messages: int | None = None,
    message_ids: "list[int] | None" = None,
) -> dict[str, int]:
    """RQ job function: run one Telegram scrape cycle with progress updates.

    Args:
        message_ids: When set, only process these specific message IDs (selective mode).
    """

    publish_progress(job_id, 2, "Initializing Telegram scraper", "running")

    def _progress_cb(current: int, total: int, step: str) -> None:
        if total <= 0:
            pct = 5
        else:
            pct = 5 + int((current / total) * 85)
        publish_progress(job_id, pct, step, "running")

    async def _run() -> dict[str, int]:
        from apps.api.telegram_service import _execute_telegram_run_with_progress

        return await _execute_telegram_run_with_progress(
            trigger=trigger,
            channel_username=channel_username,
            scrape_since=scrape_since,
            max_messages=max_messages,
            on_progress=_progress_cb,
            message_ids=message_ids,
        )

    try:
        publish_progress(job_id, 5, "Connecting to Telegram", "running")
        stats = asyncio.run(_run())
        publish_progress(job_id, 100, "Done", "done")
        return stats
    except Exception as exc:
        logger.exception("telegram_scrape_job_failed job_id=%s", job_id)
        publish_progress(job_id, 0, f"Failed: {exc!s:.120}", "failed")
        raise
