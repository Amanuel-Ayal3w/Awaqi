"""
IP-based rate limiting using Redis.

Applied to public-facing chat endpoints. Each IP is limited to
RATE_LIMIT_MAX requests per RATE_LIMIT_WINDOW seconds (rolling window).

Redis key format: rate:{ip}
TTL is set to RATE_LIMIT_WINDOW on first request, then reused until expiry.
"""

from fastapi import Depends, HTTPException, Request, status

from database.redis_client import (
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    get_redis,
    rate_limit_key,
)


async def require_rate_limit(
    request: Request,
    redis=Depends(get_redis),
) -> None:
    """
    FastAPI dependency — raises HTTP 429 if the caller has exceeded the
    rate limit. Attach to any endpoint with:

        @router.post("/send")
        async def send_message(..., _rl=Depends(require_rate_limit)):
    """
    ip = _get_ip(request)
    key = rate_limit_key(ip)

    current = await redis.incr(key)

    if current == 1:
        # First request in this window — set the expiry
        await redis.expire(key, RATE_LIMIT_WINDOW)

    if current > RATE_LIMIT_MAX:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "limit": RATE_LIMIT_MAX,
                "window_seconds": RATE_LIMIT_WINDOW,
                "retry_after_seconds": max(ttl, 1),
            },
            headers={"Retry-After": str(max(ttl, 1))},
        )


def _get_ip(request: Request) -> str:
    """
    Extract the real client IP, respecting X-Forwarded-For from a reverse
    proxy (nginx/traefik). Falls back to the direct connection IP.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
