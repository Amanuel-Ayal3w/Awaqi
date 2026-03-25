"""Tests for guest session HMAC token generation and validation."""

import hashlib
import hmac
import os
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SESSION_TOKEN_SECRET", "test-secret")

from apps.api.routers.chat import (
    _build_guest_session_token,
    _validate_guest_session_token,
)


class TestBuildGuestSessionToken:
    def test_returns_hex_string(self):
        sid = uuid.uuid4()
        token = _build_guest_session_token(sid)
        assert isinstance(token, str)
        assert len(token) == 64  # SHA-256 hex digest

    def test_deterministic(self):
        sid = uuid.uuid4()
        t1 = _build_guest_session_token(sid)
        t2 = _build_guest_session_token(sid)
        assert t1 == t2

    def test_different_sessions_different_tokens(self):
        t1 = _build_guest_session_token(uuid.uuid4())
        t2 = _build_guest_session_token(uuid.uuid4())
        assert t1 != t2

    def test_matches_manual_hmac(self):
        sid = uuid.uuid4()
        secret = os.getenv("SESSION_TOKEN_SECRET", "test-secret")
        expected = hmac.new(
            secret.encode("utf-8"),
            str(sid).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert _build_guest_session_token(sid) == expected


class TestValidateGuestSessionToken:
    def _make_session(self, sid: uuid.UUID) -> MagicMock:
        session = MagicMock()
        session.id = sid
        return session

    def test_valid_token_passes(self):
        sid = uuid.uuid4()
        token = _build_guest_session_token(sid)
        session = self._make_session(sid)
        _validate_guest_session_token(session, token)

    def test_none_token_raises_401(self):
        sid = uuid.uuid4()
        session = self._make_session(sid)
        with pytest.raises(HTTPException) as exc_info:
            _validate_guest_session_token(session, None)
        assert exc_info.value.status_code == 401

    def test_wrong_token_raises_401(self):
        sid = uuid.uuid4()
        session = self._make_session(sid)
        with pytest.raises(HTTPException) as exc_info:
            _validate_guest_session_token(session, "wrong-token")
        assert exc_info.value.status_code == 401

    def test_empty_token_raises_401(self):
        sid = uuid.uuid4()
        session = self._make_session(sid)
        with pytest.raises(HTTPException) as exc_info:
            _validate_guest_session_token(session, "")
        assert exc_info.value.status_code == 401
