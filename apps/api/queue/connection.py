"""Synchronous Redis connection for RQ workers and progress publishing.

RQ uses the synchronous redis-py client. We keep a module-level connection pool
so job enqueueing (in the FastAPI process) and job execution (in the RQ worker
process) both share the same URL.
"""

from __future__ import annotations

import os

import redis

_REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Synchronous connection pool — used by RQ and progress helpers.
sync_redis: redis.Redis = redis.from_url(_REDIS_URL, decode_responses=True)
