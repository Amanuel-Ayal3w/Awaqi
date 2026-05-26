"""
Shared test fixtures for the Awaqi backend test suite.

Unit tests: no DB needed, always fast.
Integration tests: need PostgreSQL, auto-skip when unavailable.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

load_dotenv()

TEST_DB_NAME = "awaqi_db_test"
DEFAULT_TEST_DATABASE_URL = (
    f"postgresql+asyncpg://postgres:postgres@localhost:5432/{TEST_DB_NAME}"
)
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    DEFAULT_TEST_DATABASE_URL,
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SESSION_TOKEN_SECRET", "test-secret")


def _assert_safe_test_database_url() -> None:
    raw = os.environ.get("DATABASE_URL", "")
    parsed = urlparse(raw.replace("postgresql+asyncpg://", "postgresql://", 1))
    db_name = (parsed.path or "/").lstrip("/").lower()
    if db_name != TEST_DB_NAME:
        raise RuntimeError(
            f"Refusing to run DB tests against '{db_name or '<missing>'}'. "
            f"Expected database name: '{TEST_DB_NAME}'. "
            "Set TEST_DATABASE_URL accordingly."
        )


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
    _REPO_ROOT = Path(__file__).resolve().parents[1]

    def _upgrade_test_db_to_head() -> None:
        """Ensure DB schema matches current models before integration tests run."""
        cfg = Config(str(_REPO_ROOT / "packages/database/alembic.ini"))
        cfg.set_main_option(
            "script_location",
            str(_REPO_ROOT / "packages/database/migrations"),
        )
        command.upgrade(cfg, "head")

    async def _ensure_migration_baseline(engine) -> None:
        """
        If alembic_version is missing but schema artifacts exist, reset public schema.
        This avoids duplicate-type errors when upgrading a previously hand-created DB.
        """
        async with engine.begin() as conn:
            has_version = await conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'alembic_version'
                    )
                    """
                )
            )
            if has_version.scalar():
                return

            has_artifacts = await conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public'
                    ) OR EXISTS (
                        SELECT 1 FROM pg_type t
                        JOIN pg_namespace n ON n.oid = t.typnamespace
                        WHERE n.nspname = 'public'
                    )
                    """
                )
            )
            if has_artifacts.scalar():
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))

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

        _assert_safe_test_database_url()

        global _TABLES_CREATED
        engine, _ = _get_engine()

        if not _TABLES_CREATED:
            await _ensure_migration_baseline(engine)
            await asyncio.to_thread(_upgrade_test_db_to_head)
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
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

    @pytest.fixture
    async def customer_user(db_session: AsyncSession):
        from database.models.customer import CuUser
        user = CuUser(
            id=uuid.uuid4(),
            name="Test Customer",
            email="customer@test.com",
            email_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def customer_session(db_session: AsyncSession, customer_user):
        from database.models.customer import CuSession
        s = CuSession(
            id=str(uuid.uuid4()),
            user_id=customer_user.id,
            token="test-customer-token-789",
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
