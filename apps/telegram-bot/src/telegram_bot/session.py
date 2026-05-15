"""
Telegram chat_id → Awaqi session mapping backed by Redis.

Each Telegram user gets:
  - A stable session_id (UUID) that maps to a ChatSession row in PostgreSQL
  - A session_token (HMAC) returned by the API, stored alongside the session_id
  - A preferred language ("en" or "am")

Keys in Redis:
  tg:session:{chat_id}         → JSON { session_id, session_token, language }

The TTL defaults to 24 hours and is reset on every interaction (sliding window),
matching the guest zero-footprint model in the SRS.
"""

import json
import os
import uuid
from typing import Optional

import redis.asyncio as aioredis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL = int(os.environ.get("TELEGRAM_SESSION_TTL", "86400"))  # 24 h default

_redis_pool: Optional[aioredis.Redis] = None


def _key(chat_id: int) -> str:
    return f"tg:session:{chat_id}"


async def _get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_pool


async def get_or_create(chat_id: int) -> tuple[str, Optional[str], str]:
    """
    Return (session_id, session_token, language) for a Telegram chat_id.
    Creates a new session entry if none exists.
    Refreshes the TTL on every call (sliding expiry).
    """
    redis = await _get_redis()
    raw = await redis.get(_key(chat_id))

    if raw:
        data = json.loads(raw)
        await redis.expire(_key(chat_id), SESSION_TTL)
        return data["session_id"], data.get("session_token"), data.get("language", "en")

    session_id = str(uuid.uuid4())
    data = {"session_id": session_id, "session_token": None, "language": "en"}
    await redis.setex(_key(chat_id), SESSION_TTL, json.dumps(data))
    return session_id, None, "en"


async def update_token(chat_id: int, session_token: str) -> None:
    """Persist the latest session_token returned by the API."""
    redis = await _get_redis()
    raw = await redis.get(_key(chat_id))
    if raw:
        data = json.loads(raw)
        data["session_token"] = session_token
        await redis.setex(_key(chat_id), SESSION_TTL, json.dumps(data))


async def set_language(chat_id: int, language: str) -> None:
    """Update the stored language preference ('en' or 'am')."""
    redis = await _get_redis()
    raw = await redis.get(_key(chat_id))
    if raw:
        data = json.loads(raw)
        data["language"] = language
        await redis.setex(_key(chat_id), SESSION_TTL, json.dumps(data))
    else:
        session_id = str(uuid.uuid4())
        data = {"session_id": session_id, "session_token": None, "language": language}
        await redis.setex(_key(chat_id), SESSION_TTL, json.dumps(data))


async def reset(chat_id: int) -> str:
    """
    Issue a new session_id for the user, preserving their language preference.
    Clears the conversation history on the API side (new session_id = new row).
    """
    redis = await _get_redis()
    # Preserve the user's chosen language so /newchat doesn't reset it
    raw = await redis.get(_key(chat_id))
    language = json.loads(raw).get("language", "en") if raw else "en"
    session_id = str(uuid.uuid4())
    data = {"session_id": session_id, "session_token": None, "language": language}
    await redis.setex(_key(chat_id), SESSION_TTL, json.dumps(data))
    return session_id


async def close() -> None:
    """Close the Redis connection pool on shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
