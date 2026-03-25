"""
Shared test fixtures for the Awaqi backend test suite.

Unit tests: no DB needed, always fast.
Integration tests: need PostgreSQL, auto-skip when unavailable.
"""

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from dotenv import load_dotenv

load_dotenv()

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/awaqi_db_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SESSION_TOKEN_SECRET", "test-secret")


def _db_is_available() -> bool:
    try:
        import psycopg2
        url = os.environ.get("DATABASE_URL", "")
        sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg2.connect(sync_url, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


_HAS_DB = _db_is_available()

if _HAS_DB:
    import database.models  # noqa: F401
    from database.base import Base
    from database.models.auth import BaSession, BaUser
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    _TABLES_CREATED = False
    _engine = None
    _SessionLocal = None

    def _get_engine():
        global _engine, _SessionLocal
        if _engine is None:
            _engine = create_async_engine(
                os.environ["DATABASE_URL"],
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
            )
            _SessionLocal = async_sessionmaker(
                _engine, expire_on_commit=False, class_=AsyncSession
            )
        return _engine, _SessionLocal

    @pytest.fixture(autouse=True)
    async def _setup_db(request):
        uses_db = (
            "client" in request.fixturenames
            or "db_session" in request.fixturenames
        )
        if not uses_db:
            yield
            return

        global _TABLES_CREATED
        engine, _ = _get_engine()

        if not _TABLES_CREATED:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                await conn.run_sync(Base.metadata.create_all)
            _TABLES_CREATED = True

        yield

        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))

    @pytest.fixture
    async def db_session() -> AsyncGenerator[AsyncSession, None]:
        _, factory = _get_engine()
        async with factory() as session:
            yield session
            await session.rollback()

    @pytest.fixture
    def mock_redis():
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.ttl = AsyncMock(return_value=600)
        return redis

    @pytest.fixture
    async def client(mock_redis) -> AsyncGenerator[AsyncClient, None]:
        from database import get_session
        from database.redis_client import get_redis

        from apps.api.main import app

        _, factory = _get_engine()

        async def _override() -> AsyncGenerator[AsyncSession, None]:
            async with factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_session] = _override
        app.dependency_overrides[get_redis] = lambda: mock_redis

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()

    @pytest.fixture
    async def admin_user(db_session: AsyncSession) -> BaUser:
        user = BaUser(
            id=uuid.uuid4(), name="Test Admin", email="admin@test.com",
            email_verified=False, role="superadmin", is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def admin_session(db_session: AsyncSession, admin_user: BaUser) -> BaSession:
        s = BaSession(
            id=str(uuid.uuid4()), user_id=admin_user.id,
            token="test-admin-token-123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(s)
        await db_session.commit()
        return s

    @pytest.fixture
    async def editor_user(db_session: AsyncSession) -> BaUser:
        user = BaUser(
            id=uuid.uuid4(), name="Test Editor", email="editor@test.com",
            email_verified=False, role="editor", is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def editor_session(db_session: AsyncSession, editor_user: BaUser) -> BaSession:
        s = BaSession(
            id=str(uuid.uuid4()), user_id=editor_user.id,
            token="test-editor-token-456",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(s)
        await db_session.commit()
        return s

else:
    @pytest.fixture(autouse=True)
    def _setup_db():
        yield
