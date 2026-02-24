"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.

Usage in FastAPI:
    from database.db import get_session
    from sqlalchemy.ext.asyncio import AsyncSession

    @app.get("/example")
    async def example(session: AsyncSession = Depends(get_session)):
        ...

Environment variables:
    DATABASE_URL  — full async DSN, e.g.
                    postgresql+asyncpg://user:password@localhost:5432/awaqi
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

_DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/awaqi",
)

# Normalise the URL to always use the asyncpg async driver.
# Handles cases where DATABASE_URL is set as plain "postgresql://" or
# "postgresql+psycopg2://" which would break create_async_engine.
if _DATABASE_URL.startswith("postgresql://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _DATABASE_URL.startswith("postgres://"):
    # Heroku-style shorthand also needs normalising
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# pool_pre_ping=True: validates connections before checkout (resilient to DB
# restarts without restarting the app).
engine = create_async_engine(
    _DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# ---------------------------------------------------------------------------
# FastAPI / dependency-injection helper
# ---------------------------------------------------------------------------
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession per request; rolls back on exception, closes always.

    Example:
        from database.db import get_session
        session: AsyncSession = Depends(get_session)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Dev / test utility: create all tables without Alembic
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """
    Create all database tables based on the ORM metadata.

    ⚠️  For development / test environments only.
    In production, use `alembic upgrade head` instead.
    """
    # Import all models so their metadata is registered on Base
    from database.base import Base  # noqa: F401 — must be imported for side effects
    import database.models  # noqa: F401

    async with engine.begin() as conn:
        # Enable the pgvector extension before creating tables
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.run_sync(Base.metadata.create_all)
