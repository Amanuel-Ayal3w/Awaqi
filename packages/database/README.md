# Database Package

Shared PostgreSQL + pgvector models, async session management, Redis client, and Alembic migrations for the Awaqi monorepo.

## Architecture

```
packages/database/
├── alembic.ini                    # Alembic configuration
├── migrations/
│   ├── env.py                     # Async migration runner
│   └── versions/
│       ├── 0001_initial_schema.py # Core tables
│       └── 0002_better_auth_tables.py # Auth tables (replaces admin_users)
├── src/database/
│   ├── __init__.py                # Public API exports
│   ├── base.py                    # SQLAlchemy DeclarativeBase
│   ├── db.py                      # Async engine, session factory, get_session()
│   ├── redis_client.py            # Redis client, TTL constants, get_redis()
│   └── models/
│       ├── __init__.py
│       ├── auth.py                # BaUser, BaSession (Better Auth)
│       ├── document.py            # Document, DocumentChunk (pgvector)
│       └── session.py             # ChatSession, Message, Feedback
└── pyproject.toml
```

## Tables

### Auth (managed by Better Auth via Next.js)

| Table | Purpose |
|---|---|
| `ba_user` | Admin users — email, name, role (`superadmin`/`editor`), `is_active` |
| `ba_session` | Active login sessions — token, expiry, IP, user agent |
| `ba_account` | Credentials — bcrypt password hash for email/password auth |
| `ba_verification` | Email verification tokens |

### Core (managed by FastAPI + Alembic)

| Table | Purpose |
|---|---|
| `documents` | Regulatory PDFs ingested from mor.gov.et or uploaded by admins |
| `document_chunks` | 1024-token text chunks with pgvector embeddings (1024-dim) |
| `chat_sessions` | Conversation threads (web or Telegram, guest or admin) |
| `messages` | Individual turns — user queries and assistant responses |
| `feedback` | Thumbs up/down ratings on assistant messages |

### Relationships

```
ba_user (1) ──< (N) chat_sessions ──< (N) messages ──< (1) feedback
ba_user (1) ──< (N) ba_session
ba_user (1) ──< (N) ba_account
documents (1) ──< (N) document_chunks
```

## Prerequisites

- **PostgreSQL 16+** with the [pgvector](https://github.com/pgvector/pgvector) extension
- **Redis 7+**
- **Python 3.12+**
- **uv** package manager (the monorepo uses `uv` workspaces)

## Setup

### 1. Start PostgreSQL and Redis

The fastest way is Docker Compose from the repo root:

```bash
docker compose -f docker/docker-compose.yml up -d db redis
```

This starts:
- PostgreSQL (pgvector) on `localhost:5432` — user: `user`, password: `password`, database: `awaqi_db`
- Redis on `localhost:6379`

If you prefer a local PostgreSQL installation, make sure pgvector is installed:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 2. Set environment variables

Create a `.env` file in the repo root (or export these):

```bash
# Async driver URL — used by FastAPI and Alembic
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/awaqi_db

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 3. Install dependencies

From the monorepo root:

```bash
uv sync
```

This installs the `database` package and all its dependencies (`sqlalchemy`, `pgvector`, `alembic`, `asyncpg`, `redis`, etc.) into the workspace virtual environment.

### 4. Run migrations

```bash
cd packages/database
uv run alembic upgrade head
```

This creates all tables in order:
1. `0001_initial_schema` — documents, document_chunks, chat_sessions, messages, feedback, and the pgvector/pg_trgm extensions
2. `0002_better_auth_tables` — ba_user, ba_session, ba_account, ba_verification; migrates the `chat_sessions` FK from the old `admin_users` table to `ba_user`

### 5. Verify

```bash
uv run python -c "
import asyncio
from database.db import init_db, engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(__import__('sqlalchemy').text('SELECT tablename FROM pg_tables WHERE schemaname = \'public\''))
        tables = [row[0] for row in result]
        print('Tables:', tables)

asyncio.run(check())
"
```

Expected output should list: `ba_user`, `ba_session`, `ba_account`, `ba_verification`, `documents`, `document_chunks`, `chat_sessions`, `messages`, `feedback`.

## Usage in other packages

### Importing models

```python
from database import get_session, BaUser, ChatSession, Message, Document
from database.models.auth import BaSession
```

### FastAPI dependency injection

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session

@app.get("/example")
async def example(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Document).limit(10))
    return result.scalars().all()
```

The `get_session` dependency yields an `AsyncSession` scoped to the request. It auto-commits on success and rolls back on exception.

### Redis

```python
from database import get_redis
import redis.asyncio as aioredis

@app.get("/example")
async def example(redis: aioredis.Redis = Depends(get_redis)):
    await redis.set("key", "value", ex=60)
    return await redis.get("key")
```

Constants available:
- `GUEST_SESSION_TTL` — 10 minutes
- `RATE_LIMIT_WINDOW` — 10 minutes
- `RATE_LIMIT_MAX` — 15 requests per window per IP

## Creating new migrations

After modifying a model in `models/`, generate a new migration:

```bash
cd packages/database
uv run alembic revision --autogenerate -m "describe_your_change"
```

Review the generated file in `migrations/versions/`, then apply:

```bash
uv run alembic upgrade head
```

To rollback one step:

```bash
uv run alembic downgrade -1
```

## Auth flow (how ba_* tables are used)

Better Auth (running inside the Next.js app) owns the `ba_*` tables. It handles:
- User registration and login (writes to `ba_user` + `ba_account`)
- Session creation (writes to `ba_session` with a unique token and expiry)
- Session cookies (httpOnly cookie set in the browser)

FastAPI **reads** the `ba_session` and `ba_user` tables to validate admin requests — one JOIN query per request, no JWT or shared secrets:

```sql
SELECT ba_user.*
FROM ba_session
JOIN ba_user ON ba_session."userId" = ba_user.id
WHERE ba_session.token = :token
AND ba_session."expiresAt" > NOW()
```

## Connection settings

| Setting | Value | Notes |
|---|---|---|
| Pool size | 10 | Concurrent connections |
| Max overflow | 20 | Burst capacity above pool size |
| Pool pre-ping | true | Validates connections before use |
| Echo SQL | false | Set `DB_ECHO=true` to enable query logging |

## Troubleshooting

**"relation does not exist"** — Migrations haven't been run. Run `uv run alembic upgrade head`.

**"password authentication failed"** — Check that `DATABASE_URL` matches the credentials in `docker-compose.yml` (default: `user`/`password`).

**"could not translate host name 'db' to address"** — You're using the Docker-internal hostname outside of Docker. Use `localhost` instead of `db` for local development.

**"extension 'vector' is not available"** — You need the pgvector extension. Use the `pgvector/pgvector:pg16` Docker image, or install pgvector manually on your PostgreSQL server.
