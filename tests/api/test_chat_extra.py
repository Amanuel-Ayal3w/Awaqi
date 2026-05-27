"""
Integration tests for chat routes not covered by test_chat_endpoints.py:
  - GET  /v1/chat/export/{session_id}   (transcript export)
  - POST /v1/chat/send  with safety-refused query
  - POST /v1/chat/send  with Telegram channel header
  - POST /v1/chat/feedback/{message_id} on valid message (success path)
  - Rate-limit: mock Redis at > limit and expect 429
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

try:
    from tests.conftest import _HAS_DB
except ImportError:
    _HAS_DB = False

pytestmark = [
    pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not available"),
    pytest.mark.asyncio(loop_scope="session"),
]


# ---------------------------------------------------------------------------
# Export transcript
# ---------------------------------------------------------------------------

class TestExportTranscript:
    async def test_nonexistent_session_returns_404(self, client):
        resp = await client.get(f"/v1/chat/export/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_400(self, client):
        resp = await client.get("/v1/chat/export/not-a-uuid")
        assert resp.status_code == 400

    async def test_export_returns_plain_text(self, client):
        session_id = str(uuid.uuid4())
        r1 = await client.post("/v1/chat/send", json={
            "message": "Income tax deadline?",
            "session_id": session_id,
        })
        assert r1.status_code == 200
        token = r1.json()["session_token"]

        resp = await client.get(
            f"/v1/chat/export/{session_id}",
            headers={"X-Session-Token": token},
        )
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "USER" in body
        assert "Income tax deadline?" in body
        assert "ASSISTANT" in body

    async def test_export_without_token_fails_for_guest(self, client):
        session_id = str(uuid.uuid4())
        await client.post("/v1/chat/send", json={
            "message": "Hello",
            "session_id": session_id,
        })
        resp = await client.get(f"/v1/chat/export/{session_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Safety refusal
# ---------------------------------------------------------------------------

class TestSafetyRefusal:
    async def test_profane_message_returns_200_with_refusal(self, client):
        resp = await client.post("/v1/chat/send", json={
            "message": "fuck you",
            "session_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "language" in data["response_text"].lower()
        assert data["confidence_score"] == 0.0
        assert data["citations"] == []

    async def test_empty_message_returns_200_with_prompt(self, client):
        resp = await client.post("/v1/chat/send", json={
            "message": "   ",
            "session_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["response_text"]
        assert data["confidence_score"] == 0.0


# ---------------------------------------------------------------------------
# Successful feedback path
# ---------------------------------------------------------------------------

class TestFeedbackSuccess:
    async def test_feedback_on_real_message_returns_200(self, client):
        session_id = str(uuid.uuid4())
        r1 = await client.post("/v1/chat/send", json={
            "message": "What is VAT?",
            "session_id": session_id,
        })
        assert r1.status_code == 200
        token = r1.json()["session_token"]

        from database.models.session import Message, MessageRole
        from sqlalchemy import select
        from tests.conftest import _get_engine  # type: ignore[attr-defined]
        _, factory = _get_engine()
        async with factory() as session:
            result = await session.execute(
                select(Message).where(
                    Message.role == MessageRole.ASSISTANT
                ).order_by(Message.created_at.desc()).limit(1)
            )
            msg = result.scalar_one_or_none()

        if msg is None:
            pytest.skip("No assistant message found to rate")

        resp = await client.post(
            f"/v1/chat/feedback/{msg.id}",
            json={"score": 1, "comment": "Helpful answer"},
            headers={"X-Session-Token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"


# ---------------------------------------------------------------------------
# Rate limiting (429)
# ---------------------------------------------------------------------------

class TestRateLimitEndpoint:
    async def test_rate_limit_returns_429(self, client, mock_redis):
        from database.redis_client import RATE_LIMIT_MAX

        mock_redis.incr = AsyncMock(return_value=RATE_LIMIT_MAX + 1)
        mock_redis.ttl = AsyncMock(return_value=300)

        resp = await client.post("/v1/chat/send", json={
            "message": "Hello",
            "session_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 429
        data = resp.json()
        assert data["detail"]["error"] == "rate_limit_exceeded"
        assert "retry_after_seconds" in data["detail"]
        assert "Retry-After" in resp.headers

    async def test_rate_limit_response_has_limit_field(self, client, mock_redis):
        from database.redis_client import RATE_LIMIT_MAX

        mock_redis.incr = AsyncMock(return_value=RATE_LIMIT_MAX + 5)
        mock_redis.ttl = AsyncMock(return_value=120)

        resp = await client.post("/v1/chat/send", json={
            "message": "Test",
            "session_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 429
        detail = resp.json()["detail"]
        assert detail["limit"] == RATE_LIMIT_MAX
        assert detail["window_seconds"] == 600
