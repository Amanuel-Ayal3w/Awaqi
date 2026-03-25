"""Tests for the health endpoint — the simplest integration test."""

import pytest

try:
    from tests.conftest import _HAS_DB
except ImportError:
    _HAS_DB = False

pytestmark = [
    pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not available"),
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "api"
