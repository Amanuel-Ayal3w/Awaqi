"""
Integration tests for the Telegram account-linking endpoints:
  - POST /v1/auth/telegram/link-request    (no auth required — bot calls this)
  - POST /v1/auth/telegram/link-confirm    (customer auth required)
  - DELETE /v1/auth/telegram/link          (customer auth required)
  - GET  /v1/auth/telegram/link            (customer auth required)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

try:
    from tests.conftest import _HAS_DB
except ImportError:
    _HAS_DB = False

pytestmark = [
    pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not available"),
    pytest.mark.asyncio(loop_scope="session"),
]


def _customer_auth(session) -> dict:
    return {"Authorization": f"Bearer {session.token}"}


# ---------------------------------------------------------------------------
# link-request (called by the Telegram bot, no user auth)
# ---------------------------------------------------------------------------

class TestLinkRequest:
    async def test_returns_token_and_url(self, client, mock_redis):
        mock_redis.setex = AsyncMock(return_value=True)

        resp = await client.post(
            "/v1/auth/telegram/link-request",
            json={"chat_id": 12345},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "link_url" in data
        assert "expires_in_seconds" in data
        assert data["expires_in_seconds"] == 600

    async def test_link_url_contains_token(self, client, mock_redis):
        mock_redis.setex = AsyncMock(return_value=True)

        resp = await client.post(
            "/v1/auth/telegram/link-request",
            json={"chat_id": 99999},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] in data["link_url"]

    async def test_each_call_returns_different_token(self, client, mock_redis):
        mock_redis.setex = AsyncMock(return_value=True)

        r1 = await client.post("/v1/auth/telegram/link-request", json={"chat_id": 1})
        r2 = await client.post("/v1/auth/telegram/link-request", json={"chat_id": 2})
        assert r1.json()["token"] != r2.json()["token"]

    async def test_missing_chat_id_returns_422(self, client, mock_redis):
        resp = await client.post("/v1/auth/telegram/link-request", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# link-confirm (authenticated customer + valid Redis token)
# ---------------------------------------------------------------------------

class TestLinkConfirm:
    async def test_unauthenticated_returns_401(self, client, mock_redis):
        resp = await client.post(
            "/v1/auth/telegram/link-confirm",
            json={"token": "sometoken"},
        )
        assert resp.status_code == 401

    async def test_invalid_token_returns_400(self, client, mock_redis, customer_session):
        mock_redis.get = AsyncMock(return_value=None)

        resp = await client.post(
            "/v1/auth/telegram/link-confirm",
            json={"token": "bad-token-xyz"},
            headers=_customer_auth(customer_session),
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()

    async def test_valid_token_links_account(self, client, mock_redis, customer_session):
        chat_id = 98765
        mock_redis.get = AsyncMock(return_value=str(chat_id).encode())
        mock_redis.delete = AsyncMock(return_value=1)

        with patch("apps.api.routers.telegram_link._notify_telegram", new=AsyncMock()):
            resp = await client.post(
                "/v1/auth/telegram/link-confirm",
                json={"token": "valid-token-abc"},
                headers=_customer_auth(customer_session),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["telegram_chat_id"] == chat_id


# ---------------------------------------------------------------------------
# unlink
# ---------------------------------------------------------------------------

class TestUnlink:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.delete("/v1/auth/telegram/link")
        assert resp.status_code == 401

    async def test_not_linked_returns_404(self, client, mock_redis, customer_session):
        resp = await client.delete(
            "/v1/auth/telegram/link",
            headers=_customer_auth(customer_session),
        )
        assert resp.status_code == 404
        assert "No Telegram" in resp.json()["detail"]

    async def test_linked_user_can_unlink(self, client, mock_redis, db_session, customer_user, customer_session):
        customer_user.telegram_chat_id = 55555
        db_session.add(customer_user)
        await db_session.commit()

        resp = await client.delete(
            "/v1/auth/telegram/link",
            headers=_customer_auth(customer_session),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# get link status
# ---------------------------------------------------------------------------

class TestGetLinkStatus:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/v1/auth/telegram/link")
        assert resp.status_code == 401

    async def test_not_linked_returns_false(self, client, mock_redis, customer_session):
        resp = await client.get(
            "/v1/auth/telegram/link",
            headers=_customer_auth(customer_session),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is False
        assert data["telegram_chat_id"] is None

    async def test_linked_user_returns_true(self, client, mock_redis, db_session, customer_user, customer_session):
        customer_user.telegram_chat_id = 77777
        db_session.add(customer_user)
        await db_session.commit()

        resp = await client.get(
            "/v1/auth/telegram/link",
            headers=_customer_auth(customer_session),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is True
        assert data["telegram_chat_id"] == 77777
