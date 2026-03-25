"""Tests for Pydantic request/response schemas."""

import pytest
from pydantic import ValidationError

from apps.api.schemas import (
    AdminUserItem,
    ChatRequest,
    ChatResponse,
    Citation,
    FeedbackRequest,
)


class TestChatRequest:
    def test_valid_request(self):
        req = ChatRequest(message="Hello", session_id="abc-123")
        assert req.message == "Hello"
        assert req.session_id == "abc-123"
        assert req.language == "en"

    def test_custom_language(self):
        req = ChatRequest(message="Hello", session_id="abc", language="am")
        assert req.language == "am"

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(session_id="abc")

    def test_missing_session_id_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Hello")


class TestChatResponse:
    def test_minimal_response(self):
        resp = ChatResponse(
            response_text="Answer",
            citations=[],
            confidence_score=0.85,
        )
        assert resp.session_token is None

    def test_response_with_token(self):
        resp = ChatResponse(
            response_text="Answer",
            citations=[],
            confidence_score=0.5,
            session_token="abc123",
        )
        assert resp.session_token == "abc123"

    def test_response_with_citations(self):
        resp = ChatResponse(
            response_text="Tax rate is 15%",
            citations=[Citation(source="tax_law.pdf", page=3, text="...15%...")],
            confidence_score=0.9,
        )
        assert len(resp.citations) == 1
        assert resp.citations[0].source == "tax_law.pdf"


class TestFeedbackRequest:
    def test_positive_feedback(self):
        fb = FeedbackRequest(score=1)
        assert fb.score == 1
        assert fb.comment is None

    def test_feedback_with_comment(self):
        fb = FeedbackRequest(score=-1, comment="Not helpful")
        assert fb.comment == "Not helpful"


class TestAdminUserItem:
    def test_full_user(self):
        user = AdminUserItem(
            id="uuid-1",
            name="Abebe",
            email="abebe@test.com",
            role="superadmin",
            is_active=True,
            created_at="2026-01-01T00:00:00Z",
        )
        assert user.is_active is True

    def test_user_without_name(self):
        user = AdminUserItem(
            id="uuid-1",
            email="test@test.com",
            role="editor",
            is_active=False,
            created_at="2026-01-01T00:00:00Z",
        )
        assert user.name is None
