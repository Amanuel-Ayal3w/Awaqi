"""
database package — public API.

Import from here in other packages:
    from database import get_session, get_redis, redis_client
    from database.models import BaUser, BaSession, Document, ChatSession, Message, Feedback
"""

try:
    # Importing `database.db` eagerly creates the SQLAlchemy engine, which in turn
    # requires the configured DB driver (e.g. `asyncpg`). For lightweight scripts
    # that only need ORM models (or run in offline mode), keep this import
    # best-effort.
    from database.db import AsyncSessionLocal, engine, get_session, init_db
except Exception:  # pragma: no cover
    AsyncSessionLocal = None  # type: ignore[assignment]
    engine = None  # type: ignore[assignment]

    async def get_session():  # type: ignore[no-redef]
        raise RuntimeError(
            "database.get_session() unavailable (DB driver not installed/configured)"
        )

    def init_db():  # type: ignore[no-redef]
        raise RuntimeError("database.init_db() unavailable (DB driver not installed)")
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
