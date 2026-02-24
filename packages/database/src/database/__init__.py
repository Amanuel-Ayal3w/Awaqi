"""
database package — public API.

Import from here in other packages:
    from database import get_session, get_redis, redis_client
    from database.models import BaUser, BaSession, Document, ChatSession, Message, Feedback
"""

from database.db import AsyncSessionLocal, engine, get_session, init_db
from database.models import (
    BaSession,
    BaUser,
    ChatSession,
    Document,
    DocumentChunk,
    Feedback,
    Message,
)
from database.redis_client import get_redis, ping_redis, redis_client

__all__ = [
    # Engine / session
    "engine",
    "AsyncSessionLocal",
    "get_session",
    "init_db",
    # Redis
    "redis_client",
    "get_redis",
    "ping_redis",
    # ORM models
    "BaUser",
    "BaSession",
    "Document",
    "DocumentChunk",
    "ChatSession",
    "Message",
    "Feedback",
]
