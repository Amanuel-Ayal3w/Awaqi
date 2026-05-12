"""Tests for HTTP retry helper."""

from __future__ import annotations

import httpx
import pytest
from ai_engine.scraper.http_retry import fetch_with_retry


@pytest.mark.asyncio
async def test_fetch_with_retry_succeeds_after_503() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, content=b"ok", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await fetch_with_retry(client, "https://example.com/doc", max_retries=3)
    assert resp.status_code == 200
    assert resp.content == b"ok"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_fetch_with_retry_no_retry_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, "https://example.com/missing.pdf", max_retries=3)
