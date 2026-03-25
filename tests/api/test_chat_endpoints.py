"""Integration tests for chat endpoints (require PostgreSQL)."""

import uuid

import pytest

try:
    from tests.conftest import _HAS_DB
except ImportError:
    _HAS_DB = False

pytestmark = [
    pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not available"),
    pytest.mark.asyncio(loop_scope="session"),
]


class TestSendMessage:
    async def test_first_message_creates_session(self, client):
        session_id = str(uuid.uuid4())
        response = await client.post("/v1/chat/send", json={
            "message": "How do I file taxes?",
            "session_id": session_id,
            "language": "en",
        })
        assert response.status_code == 200
        data = response.json()
        assert "response_text" in data
        assert "session_token" in data
        assert data["session_token"] is not None
        assert isinstance(data["confidence_score"], float)
        assert isinstance(data["citations"], list)

    async def test_second_message_with_token_succeeds(self, client):
        session_id = str(uuid.uuid4())

        r1 = await client.post("/v1/chat/send", json={
            "message": "First question",
            "session_id": session_id,
        })
        assert r1.status_code == 200
        token = r1.json()["session_token"]

        r2 = await client.post(
            "/v1/chat/send",
            json={"message": "Follow-up", "session_id": session_id},
            headers={"X-Session-Token": token},
        )
        assert r2.status_code == 200

    async def test_second_message_without_token_fails(self, client):
        session_id = str(uuid.uuid4())

        r1 = await client.post("/v1/chat/send", json={
            "message": "First",
            "session_id": session_id,
        })
        assert r1.status_code == 200

        r2 = await client.post("/v1/chat/send", json={
            "message": "Second without token",
            "session_id": session_id,
        })
        assert r2.status_code == 401

    async def test_invalid_session_id_returns_400(self, client):
        response = await client.post("/v1/chat/send", json={
            "message": "Hello",
            "session_id": "not-a-uuid",
        })
        assert response.status_code == 400

    async def test_missing_message_returns_422(self, client):
        response = await client.post("/v1/chat/send", json={
            "session_id": str(uuid.uuid4()),
        })
        assert response.status_code == 422

    async def test_default_language_is_en(self, client):
        response = await client.post("/v1/chat/send", json={
            "message": "Hello",
            "session_id": str(uuid.uuid4()),
        })
        assert response.status_code == 200


class TestGetHistory:
    async def test_nonexistent_session_returns_404(self, client):
        response = await client.get(f"/v1/chat/history/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_invalid_uuid_returns_400(self, client):
        response = await client.get("/v1/chat/history/not-a-uuid")
        assert response.status_code == 400

    async def test_history_returns_messages(self, client):
        session_id = str(uuid.uuid4())

        r1 = await client.post("/v1/chat/send", json={
            "message": "Test message",
            "session_id": session_id,
        })
        token = r1.json()["session_token"]

        response = await client.get(
            f"/v1/chat/history/{session_id}",
            headers={"X-Session-Token": token},
        )
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"
        assert messages[1]["role"] == "assistant"

    async def test_history_without_token_fails(self, client):
        session_id = str(uuid.uuid4())
        await client.post("/v1/chat/send", json={
            "message": "Hello",
            "session_id": session_id,
        })

        response = await client.get(f"/v1/chat/history/{session_id}")
        assert response.status_code == 401


class TestFeedback:
    async def test_feedback_on_nonexistent_message_returns_404(self, client):
        response = await client.post(
            f"/v1/chat/feedback/{uuid.uuid4()}",
            json={"score": 1},
        )
        assert response.status_code == 404

    async def test_invalid_message_id_returns_400(self, client):
        response = await client.post(
            "/v1/chat/feedback/not-a-uuid",
            json={"score": 1},
        )
        assert response.status_code == 400
