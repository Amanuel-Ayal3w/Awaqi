"""RQ job: MoR web scraper with Redis progress reporting.

This module is imported by the RQ worker process. It uses asyncio.run() to
execute the async scraping pipeline from a synchronous RQ job context.
"""

from __future__ import annotations

import asyncio
import logging

from apps.api.queue.progress import publish_progress

logger = logging.getLogger(__name__)


def run_mor_scrape_job(
    job_id: str,
    trigger: str = "manual",
    seed_urls: list[str] | None = None,
    max_links: int | None = None,
    sources: list[str] | None = None,
) -> dict[str, int]:
    """RQ job function: run one MoR scrape cycle with progress updates."""

    publish_progress(job_id, 2, "Initializing", "running")

    def _progress_cb(current: int, total: int, step: str) -> None:
        if total <= 0:
            pct = 5
        else:
            # Reserve 5–90% for item processing; 90–100 for DB finalization
            pct = 5 + int((current / total) * 85)
        publish_progress(job_id, pct, step, "running")

    async def _run() -> dict[str, int]:
        from apps.api.scraper_service import (
            _execute_scrape_run_with_progress,
        )

        return await _execute_scrape_run_with_progress(
            trigger=trigger,
            seed_urls=seed_urls,
            max_links=max_links,
            on_progress=_progress_cb,
            sources=sources,
        )

    try:
        publish_progress(job_id, 5, "Discovering documents", "running")
        stats = asyncio.run(_run())
        publish_progress(job_id, 100, "Done", "done")
        return stats
    except Exception as exc:
        logger.exception("mor_scrape_job_failed job_id=%s", job_id)
        publish_progress(job_id, 0, f"Failed: {exc!s:.120}", "failed")
        raise
