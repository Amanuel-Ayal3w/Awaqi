"""
Alembic env.py for Awaqi database migrations.

Reads DATABASE_URL from the environment so credentials are never
hardcoded.  Supports async migrations via run_async_migrations().
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

# ── Alembic Config object (gives access to alembic.ini values) ───────────────
config = context.config

# ── Logging setup ────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)  # type: ignore[arg-type]

# ── Pull DATABASE_URL from env (overrides alembic.ini placeholder) ───────────
database_url: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/awaqi",
)
config.set_main_option("sqlalchemy.url", database_url)

# ── Import all models so Alembic can detect schema changes ───────────────────
#    The imports must happen BEFORE target_metadata is set.
from database.base import Base  # noqa: E402
import database.models  # noqa: E402, F401 — registers all tables on Base.metadata

target_metadata = Base.metadata


# ── Offline migrations ────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no live DB)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online (async) migrations ─────────────────────────────────────────────────
def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through it."""
    connectable = create_async_engine(database_url, echo=False)

    async with connectable.connect() as connection:
        # Enable pgvector before running any migration
        await connection.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
