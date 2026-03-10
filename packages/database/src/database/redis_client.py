"""
Async Redis client for session storage and rate-limiting.

Two use cases:
  1. IP rate-limit counters — keyed by "rate:{ip}"
  2. Scraper coordination keys — keyed by "scraper:*"

Environment variables:
    REDIS_URL  — Redis connection URL (default: redis://localhost:6379/0)

Usage:
    from database.redis_client import redis_client, get_redis

    # Direct use
    await redis_client.set("key", "value", ex=60)

    # In FastAPI as a dependency
    @app.get("/example")
    async def example(redis = Depends(get_redis)):
        await redis.set("key", "value")
"""

import os
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

_REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Connection pool — created once at module import time
# ---------------------------------------------------------------------------
_pool = aioredis.ConnectionPool.from_url(
    _REDIS_URL,
    decode_responses=True,
    max_connections=50,
)

redis_client: aioredis.Redis = aioredis.Redis(connection_pool=_pool)

# ---------------------------------------------------------------------------
# TTL constants
# ---------------------------------------------------------------------------
RATE_LIMIT_WINDOW: int = 60 * 10   # 10-minute rolling window
RATE_LIMIT_MAX: int = 15           # max requests per window per IP


def rate_limit_key(ip: str) -> str:
    """Redis key for IP-based rate-limit counter."""
    return f"rate:{ip}"


# ---------------------------------------------------------------------------
# FastAPI / dependency-injection helper
# ---------------------------------------------------------------------------
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """
    Yield the shared Redis client. Does NOT create a new connection per
    request — the connection pool handles multiplexing.

    Example (FastAPI):
        @app.get("/example")
        async def example(redis: aioredis.Redis = Depends(get_redis)):
            await redis.get("key")
    """
    yield redis_client


# ---------------------------------------------------------------------------
# Health check helper
# ---------------------------------------------------------------------------
async def ping_redis() -> bool:
    """Return True if Redis is reachable, False otherwise."""
    try:
        return await redis_client.ping()
    except Exception:
        return False
