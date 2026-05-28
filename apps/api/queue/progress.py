"""Progress tracking helpers for RQ jobs.

Workers call ``publish_progress`` to update a Redis hash (for late subscribers)
and publish to a pub/sub channel (for live SSE streams).

Key schema:
  Hash  → ``job:{job_id}``          fields: pct, step, status, job_id
  PubSub channel → ``progress:{job_id}``  payload: JSON of same fields
"""

from __future__ import annotations

import json
import logging

from apps.api.queue.connection import sync_redis

logger = logging.getLogger(__name__)

JOB_TTL = 3600  # seconds — keep state for 1 h after completion


def publish_progress(
    job_id: str,
    pct: int,
    step: str,
    status: str = "running",
) -> None:
    """Store progress in Redis hash + publish to pub/sub channel."""
    pct = max(0, min(100, pct))
    data = {"pct": str(pct), "step": step, "status": status, "job_id": job_id}
    try:
        sync_redis.hset(f"job:{job_id}", mapping=data)
        sync_redis.expire(f"job:{job_id}", JOB_TTL)
        sync_redis.publish(f"progress:{job_id}", json.dumps({**data, "pct": pct}))
    except Exception:
        logger.warning("progress_publish_failed job_id=%s", job_id, exc_info=False)


def get_job_progress(job_id: str) -> dict | None:
    """Return current progress dict or None if job_id is unknown."""
    try:
        data = sync_redis.hgetall(f"job:{job_id}")
    except Exception:
        return None
    if not data:
        return None
    return {
        "pct": int(data.get("pct", 0)),
        "step": data.get("step", ""),
        "status": data.get("status", "unknown"),
        "job_id": job_id,
    }
