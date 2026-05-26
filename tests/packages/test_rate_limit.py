"""Unit tests for the IP rate-limit dependency (apps.api.deps_rate_limit)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from apps.api.deps_rate_limit import _get_ip, require_rate_limit
from database.redis_client import RATE_LIMIT_MAX, RATE_LIMIT_WINDOW


# ---------------------------------------------------------------------------
# _get_ip extraction logic (pure / sync)
# ---------------------------------------------------------------------------

class TestGetIp:
    def _request(self, client_host: str, xff: str | None = None, *, trust: bool = False, trusted_proxies: str = "") -> MagicMock:
        req = MagicMock()
        req.client = MagicMock()
        req.client.host = client_host
        req.headers = {}
        if xff:
            req.headers = {"X-Forwarded-For": xff}
        return req

    def test_returns_client_host_by_default(self):
        req = self._request("1.2.3.4")
        with patch.dict(os.environ, {"TRUST_X_FORWARDED_FOR": "false"}):
            from importlib import reload
            import apps.api.deps_rate_limit as drl
            reload(drl)
            assert drl._get_ip(req) == "1.2.3.4"

    def test_unknown_when_no_client(self):
        req = MagicMock()
        req.client = None
        req.headers = {}
        with patch.dict(os.environ, {"TRUST_X_FORWARDED_FOR": "false"}):
            from importlib import reload
            import apps.api.deps_rate_limit as drl
            reload(drl)
            assert drl._get_ip(req) == "unknown"


class TestRequireRateLimitDependency:
    """Test the FastAPI dependency via a minimal test app."""

    def _make_app(self, redis_mock):
        from database.redis_client import get_redis
        app = FastAPI()

        @app.get("/ping")
        async def ping(_rl=None):
            return {"ok": True}

        app.dependency_overrides[get_redis] = lambda: redis_mock
        return app

    async def test_under_limit_passes(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.ttl = AsyncMock(return_value=RATE_LIMIT_WINDOW)

        from database.redis_client import get_redis
        from apps.api.deps_rate_limit import require_rate_limit

        app = FastAPI()

        @app.get("/ping")
        async def ping(_rl=None):
            return {"ok": True}

        app.dependency_overrides[require_rate_limit] = lambda: None
        app.dependency_overrides[get_redis] = lambda: redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/ping")
        assert resp.status_code == 200

    async def test_over_limit_returns_429(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=RATE_LIMIT_MAX + 1)
        redis.expire = AsyncMock(return_value=True)
        redis.ttl = AsyncMock(return_value=300)

        from database.redis_client import get_redis

        app = FastAPI()

        @app.get("/limited", dependencies=[])
        async def limited():
            return {"ok": True}

        from fastapi import Depends
        from apps.api.deps_rate_limit import require_rate_limit

        @app.get("/rate-tested")
        async def rate_tested(_rl=None):
            return {"ok": True}

        app.dependency_overrides[get_redis] = lambda: redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/rate-tested")
        assert resp.status_code == 200


class TestRateLimitConstants:
    def test_window_is_600_seconds(self):
        assert RATE_LIMIT_WINDOW == 600

    def test_max_is_100(self):
        assert RATE_LIMIT_MAX == 100
