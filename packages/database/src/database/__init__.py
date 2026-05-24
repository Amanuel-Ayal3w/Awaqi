"""
database package — public API.

Import from here in other packages:
    from database import get_session, get_redis, redis_client
    from database.models import BaUser, BaSession, Document, ChatSession, Message, Feedback
"""

from database.db import AsyncSessionLocal, engine, get_session, init_db
from database.fts import bm25_search_chunk_ids, fts_search_chunk_ids
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
from database.vector_search import vector_search_chunk_ids

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
    "fts_search_chunk_ids",
    "bm25_search_chunk_ids",
    "vector_search_chunk_ids",
    # ORM models
    "BaUser",
    "BaSession",
    "Document",
    "DocumentChunk",
    "ChatSession",
    "Message",
    "Feedback",
]
