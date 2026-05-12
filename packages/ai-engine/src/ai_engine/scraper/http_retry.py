"""HTTP GET with retries and exponential backoff (SRS UC-02 A2)."""

from __future__ import annotations

import asyncio
import logging
import random

import httpx

logger = logging.getLogger(__name__)


def _trim_url(url: str, max_len: int = 160) -> str:
    u = url.strip()
    return u if len(u) <= max_len else u[: max_len - 3] + "..."


def _should_retry_status(code: int) -> bool:
    return code == 429 or code >= 500


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> httpx.Response:
    """
    GET ``url`` with retries on transient failures.

    Retries: transport errors (timeout, connection reset, etc.), HTTP 429, and HTTP 5xx.
    Does **not** retry 404 or other 4xx (those fail after ``raise_for_status``).
    """
    transport_errors = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.RemoteProtocolError,
        httpx.WriteError,
        httpx.PoolTimeout,
    )

    for attempt in range(max_retries):
        try:
            resp = await client.get(url)
            if _should_retry_status(resp.status_code):
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt) + random.uniform(0, 0.25)
                    logger.warning(
                        "http_retry transient url=%s attempt=%d/%d status=%d delay=%.2fs",
                        _trim_url(url),
                        attempt + 1,
                        max_retries,
                        resp.status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
            resp.raise_for_status()
            return resp
        except transport_errors as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt) + random.uniform(0, 0.25)
                logger.warning(
                    "http_retry transport url=%s attempt=%d/%d delay=%.2fs err=%s",
                    _trim_url(url),
                    attempt + 1,
                    max_retries,
                    delay,
                    type(e).__name__,
                )
                await asyncio.sleep(delay)
                continue
            raise

    raise RuntimeError("fetch_with_retry: exhausted retries")
