# Awaqi — Database Configuration Reference

> **Generated:** 2026-03-02  
> **Package:** `packages/database`  
> **DB Engine:** PostgreSQL 16+ with `pgvector` extension  
> **Cache:** Redis 7+

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Environment Variables](#environment-variables)
3. [PostgreSQL — Engine & Session](#postgresql--engine--session)
4. [Redis Client](#redis-client)
5. [ORM Models](#orm-models)
   - [BaUser](#bauser)
   - [BaSession](#basession)
   - [AdminUser (legacy)](#adminuser-legacy)
   - [Document](#document)
   - [DocumentChunk](#documentchunk)
   - [ChatSession](#chatsession)
   - [Message](#message)
   - [Feedback](#feedback)
6. [PostgreSQL Extensions](#postgresql-extensions)
7. [Indexes](#indexes)
8. [Enum Types](#enum-types)
9. [Migration History](#migration-history)
10. [Public API (`__init__.py`)](#public-api)
11. [Known Issues & Notes](#known-issues--notes)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    packages/database                                    │
│                                                                         │
│  src/database/                                                          │
│  ├── __init__.py          ← Public re-exports (single import surface)   │
│  ├── base.py              ← Shared DeclarativeBase                      │
│  ├── db.py                ← Async SQLAlchemy engine + session factory   │
│  ├── redis_client.py      ← Async Redis connection pool                 │
│  └── models/                                                            │
│      ├── __init__.py      ← Model re-exports                            │
│      ├── auth.py          ← BaUser, BaSession (Better Auth)             │
│      ├── user.py          ← AdminUser (legacy, kept for ref)            │
│      ├── document.py      ← Document, DocumentChunk (+pgvector)         │
│      └── session.py       ← ChatSession, Message, Feedback              │
│                                                                         │
│  migrations/                                                            │
│  ├── env.py               ← Alembic env (async migrations)              │
│  ├── alembic.ini          ← Alembic config                              │
│  └── versions/                                                          │
│      ├── 0001_initial_schema.py                                         │
│      └── 0002_better_auth_tables.py                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

Two databases back the application:

| Database | Technology | Purpose |
|---|---|---|
| **Primary DB** | PostgreSQL + pgvector | Persistent storage: users, documents, RAG chunks, chat history |
| **Cache / Rate-limit** | Redis | Guest session TTL, IP rate-limiting counters |

---

## Environment Variables

| Variable | Default (fallback) | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/awaqi` | Full async DSN for PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `DB_ECHO` | `false` | Set to `"true"` to log all SQL queries (dev only) |

> **Note:** Both `db.py` and `redis_client.py` call `load_dotenv()` on import, so a `.env` file in any parent directory will be picked up automatically.

### URL Normalisation (db.py)

`db.py` automatically upgrades legacy DSN formats to the `asyncpg` driver:

| Input format | Normalised to |
|---|---|
| `postgresql://...` | `postgresql+asyncpg://...` |
| `postgres://...` (Heroku-style) | `postgresql+asyncpg://...` |
| `postgresql+asyncpg://...` | unchanged |

---

## PostgreSQL — Engine & Session

**File:** [`src/database/db.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/db.py)

### Engine Configuration

```python
engine = create_async_engine(
    DATABASE_URL,
    echo=False,           # toggle via DB_ECHO env var
    pool_pre_ping=True,   # validates connections before checkout
    pool_size=10,         # persistent connections in pool
    max_overflow=20,      # extra connections allowed under load
)
```

| Parameter | Value | Rationale |
|---|---|---|
| `pool_pre_ping` | `True` | Survives DB restarts without restarting the app |
| `pool_size` | `10` | Baseline concurrent connections |
| `max_overflow` | `20` | Burst headroom; total max = 30 connections |
| `echo` | env-driven | Only enabled in dev via `DB_ECHO=true` |

### Session Factory

```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)
```

`expire_on_commit=False` means ORM objects remain accessible after a commit without issuing new SELECT queries — important for async code where lazy loading is not available.

### `get_session()` — FastAPI Dependency

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

- Auto-commits on success, auto-rolls back on any exception.
- Always closes the session in `finally`.

### `init_db()` — Dev / Test Utility

```python
async def init_db() -> None:
    """⚠️ Dev/test only. Use `alembic upgrade head` in production."""
```

Creates all tables directly from ORM metadata, enabling the `pgvector` extension first.

---

## Redis Client

**File:** [`src/database/redis_client.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/redis_client.py)

### Connection Pool

```python
_pool = aioredis.ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,   # all values returned as str, not bytes
    max_connections=50,
)
redis_client = aioredis.Redis(connection_pool=_pool)
```

A single shared pool is created at module import time and reused across all requests. Max 50 connections.

### TTL Constants

| Constant | Value | Purpose |
|---|---|---|
| `GUEST_SESSION_TTL` | 600 s (10 min) | Guest chat history auto-expiry |
| `RATE_LIMIT_WINDOW` | 600 s (10 min) | Rolling window for rate limiting |
| `RATE_LIMIT_MAX` | 15 requests | Max requests per IP per window |

### Key Patterns

| Usage | Key format | Example |
|---|---|---|
| Guest chat history | `session:<uuid>` | `session:abc123-...` |
| IP rate-limit counter | `rate:<ip>` | `rate:192.168.1.1` |

### FastAPI Dependency

```python
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield redis_client  # yields the shared pool, no new connection
```

### Health Check

```python
async def ping_redis() -> bool:
    try:
        return await redis_client.ping()
    except Exception:
        return False
```

---

## ORM Models

All models inherit from the shared `Base` (`DeclarativeBase`) defined in [`base.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/base.py).

### Model Relationship Diagram

```
ba_user ─┬─────────────────────────────────── ba_session (1:N)
         │                                    ba_account (1:N)
         │                                    ba_verification (1:N)
         └── chat_sessions (1:N) ──── messages (1:N) ──── feedback (1:1)

documents ──── document_chunks (1:N)
```

---

### BaUser

**Table:** `ba_user` | **File:** [`models/auth.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/auth.py)

The live admin user model, managed by **Better Auth** (Next.js side). Python/FastAPI uses this table to validate session tokens.

| Column | DB Name | Type | Constraints | Notes |
|---|---|---|---|---|
| `id` | `id` | UUID | PK | auto-generated |
| `name` | `name` | VARCHAR(255) | nullable | Display name |
| `email` | `email` | VARCHAR(255) | NOT NULL, UNIQUE, indexed | |
| `email_verified` | `emailVerified` | BOOLEAN | NOT NULL, default `false` | Better Auth standard |
| `image` | `image` | TEXT | nullable | Avatar URL |
| `role` | `role` | ENUM(`admin_role`) | NOT NULL, default `editor` | Awaqi custom field |
| `is_active` | `is_active` | BOOLEAN | NOT NULL, default `true` | Awaqi custom field |
| `created_at` | `createdAt` | TIMESTAMPTZ | NOT NULL | camelCase in DB |
| `updated_at` | `updatedAt` | TIMESTAMPTZ | NOT NULL | camelCase in DB |

**Relationships:** `chat_sessions` (1:N, cascade delete-orphan)

---

### BaSession

**Table:** `ba_session` | **File:** [`models/auth.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/auth.py)

One row per active browser session. FastAPI's `get_current_admin` dependency validates Bearer tokens by querying this table.

| Column | DB Name | Type | Constraints |
|---|---|---|---|
| `id` | `id` | TEXT | PK (generated by Better Auth) |
| `user_id` | `userId` | UUID | NOT NULL, FK → `ba_user.id` (CASCADE), indexed |
| `token` | `token` | TEXT | NOT NULL, UNIQUE |
| `expires_at` | `expiresAt` | TIMESTAMPTZ | NOT NULL |
| `ip_address` | `ipAddress` | TEXT | nullable |
| `user_agent` | `userAgent` | TEXT | nullable |
| `created_at` | `createdAt` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | `updatedAt` | TIMESTAMPTZ | NOT NULL |

---

### AdminUser (legacy)

**Table:** `admin_users` | **File:** [`models/user.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/user.py)

> ⚠️ **This table was dropped in migration `0002`** when Better Auth replaced the homegrown auth system. The ORM model is retained in the codebase for reference but the table no longer exists in a migrated database.

---

### Document

**Table:** `documents` | **File:** [`models/document.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/document.py)

Represents an ingested regulatory PDF sourced from `mor.gov.et` or manually uploaded.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | auto-generated |
| `title` | VARCHAR(512) | NOT NULL | |
| `source_url` | VARCHAR(2048) | nullable | Origin URL |
| `file_hash` | VARCHAR(64) | NOT NULL, UNIQUE | SHA-256 of raw file bytes; deduplication key |
| `language` | VARCHAR(8) | NOT NULL, default `"am"` | ISO language code |
| `status` | ENUM(`document_status`) | NOT NULL, default `pending` | Indexing lifecycle state |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | auto-updated via `onupdate` |

**Relationships:** `chunks` (1:N to `DocumentChunk`, cascade delete-orphan)

**Unique constraints:** `uq_documents_file_hash` on `file_hash`

---

### DocumentChunk

**Table:** `document_chunks` | **File:** [`models/document.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/document.py)

Fixed-size text chunks + dense embeddings used for RAG retrieval.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | auto-generated |
| `document_id` | UUID | NOT NULL, FK → `documents.id` (CASCADE), indexed | |
| `chunk_index` | INTEGER | NOT NULL | Position within document |
| `content` | TEXT | NOT NULL | 1 024-token text window |
| `embedding` | `vector(1024)` | nullable | `multilingual-e5-large` output |
| `chunk_metadata` | JSONB | nullable | page_number, section_title, etc. |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**Chunking strategy:** 1 024 tokens, 100-token overlap  
**Embedding model:** `multilingual-e5-large` → 1 024-dimensional vectors  
**Embedding dimension:** `EMBEDDING_DIM = 1024`

---

### ChatSession

**Table:** `chat_sessions` | **File:** [`models/session.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/session.py)

One multi-turn conversation thread. Guest sessions (`user_id = NULL`) are also kept alive in Redis until their TTL expires.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | auto-generated |
| `channel` | ENUM(`channel`) | NOT NULL, default `web` | `web` or `telegram` |
| `user_id` | UUID | nullable, FK → `ba_user.id` (SET NULL), indexed | `NULL` = anonymous guest |
| `language` | VARCHAR(8) | NOT NULL, default `"am"` | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | auto-updated |

**Relationships:** `user` (N:1 BaUser), `messages` (1:N ordered by `created_at`)

---

### Message

**Table:** `messages` | **File:** [`models/session.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/session.py)

One turn in a `ChatSession`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | auto-generated |
| `session_id` | UUID | NOT NULL, FK → `chat_sessions.id` (CASCADE), indexed | |
| `role` | ENUM(`message_role`) | NOT NULL | `user` or `assistant` |
| `content` | TEXT | NOT NULL | |
| `cited_chunks` | JSONB | nullable | `[{chunk_id, score, excerpt}]` from RAG |
| `confidence_score` | FLOAT | nullable | RAG confidence in [0, 1]; `NULL` for user messages |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**Relationships:** `session` (N:1 ChatSession), `feedback` (1:0..1 Feedback)

---

### Feedback

**Table:** `feedback` | **File:** [`models/session.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/models/session.py)

Thumbs-up / thumbs-down rating on a single assistant message. Max one per message.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | auto-generated |
| `message_id` | UUID | NOT NULL, UNIQUE, FK → `messages.id` (CASCADE) | Enforces one rating per message |
| `rating` | ENUM(`feedback_rating`) | NOT NULL | `thumbs_up` or `thumbs_down` |
| `comment` | VARCHAR(1024) | nullable | Optional text |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

## PostgreSQL Extensions

| Extension | Enabled in migration | Purpose |
|---|---|---|
| `vector` (pgvector) | `0001` + `env.py` | Stores 1 024-dim embedding vectors, enables ANN search |
| `pg_trgm` | `0001` | Trigram-based fuzzy full-text search on `document_chunks.content` |

Both extensions are created with `CREATE EXTENSION IF NOT EXISTS ...` so re-running migrations is idempotent.

---

## Indexes

### `documents`

| Index | Columns | Type | Note |
|---|---|---|---|
| `uq_documents_file_hash` | `file_hash` | UNIQUE | Deduplication |

### `document_chunks`

| Index | Columns | Type | Note |
|---|---|---|---|
| `ix_document_chunks_document_id` | `document_id` | B-tree | Fast chunk lookup by parent doc |
| `ix_document_chunks_embedding_ivfflat` | `embedding` | **IVFFlat** (pgvector, cosine) | ANN similarity search; `lists=100` |
| `ix_document_chunks_content_trgm` | `content` | **GIN** (`gin_trgm_ops`) | Trigram full-text search |

> ⚠️ The IVFFlat index should be created **after** the initial bulk data load for optimal performance. Creating it on an empty table results in poor cluster quality.

### `ba_user` / auth tables

| Index | Columns | Type |
|---|---|---|
| `ix_ba_user_email` | `email` | UNIQUE B-tree |
| `ix_ba_session_token` | `token` | UNIQUE B-tree |
| `ix_ba_session_userId` | `userId` | B-tree |
| `ix_ba_account_userId` | `userId` | B-tree |

### Chat tables

| Index | Columns | Type |
|---|---|---|
| `ix_chat_sessions_user_id` | `user_id` | B-tree |
| `ix_messages_session_id` | `session_id` | B-tree |
| `ix_feedback_message_id` | `message_id` | B-tree |

---

## Enum Types

| PostgreSQL Enum | Values | Used by |
|---|---|---|
| `document_status` | `pending`, `indexed`, `failed` | `documents.status` |
| `admin_role` | `superadmin`, `editor` | `ba_user.role` |
| `channel` | `web`, `telegram` | `chat_sessions.channel` |
| `message_role` | `user`, `assistant` | `messages.role` |
| `feedback_rating` | `thumbs_up`, `thumbs_down` | `feedback.rating` |

All enums are created explicitly in migration `0001` so Alembic autogenerate can detect changes.

---

## Migration History

### `0001` — Initial Schema
**Date:** 2026-02-24 | **Revises:** _(none — initial)_

Creates all base tables and extensions:
- `documents`, `document_chunks` (with pgvector + GIN indexes)
- `admin_users` (original homegrown auth — see 0002)
- `chat_sessions`, `messages`, `feedback`
- All 5 PostgreSQL enum types
- Both PostgreSQL extensions (`vector`, `pg_trgm`)

### `0002` — Better Auth Migration
**Date:** 2026-02-24 | **Revises:** `0001`

Replaces the homegrown `admin_users` table with the Better Auth table set:

| Action | Table |
|---|---|
| ✅ Created | `ba_user` (reuses `admin_role` enum, adds `emailVerified`, `image`, camelCase timestamps) |
| ✅ Created | `ba_session` (token-based sessions) |
| ✅ Created | `ba_account` (OAuth provider accounts, bcrypt hash) |
| ✅ Created | `ba_verification` (email verification tokens) |
| 🔄 Updated | `chat_sessions.user_id` FK: `admin_users.id` → `ba_user.id` |
| ❌ Dropped | `admin_users` |

### Running Migrations

```bash
# Apply all pending migrations
cd packages/database
alembic upgrade head

# Check current revision
alembic current

# Generate a new migration (autogenerate from model diff)
alembic revision --autogenerate -m "description_of_change"

# Rollback last migration
alembic downgrade -1
```

> `DATABASE_URL` must be set in the environment (or `.env` file) before running any `alembic` command.

---

## Public API

**File:** [`src/database/__init__.py`](file:///home/amanuel/Desktop/Awaqi/packages/database/src/database/__init__.py)

All consumer packages should import from the top-level `database` package:

```python
# PostgreSQL
from database import engine, AsyncSessionLocal, get_session, init_db

# Redis
from database import redis_client, get_redis, ping_redis

# ORM Models
from database import BaUser, BaSession, Document, DocumentChunk
from database import ChatSession, Message, Feedback
```

---

## Known Issues & Notes

### ⚠️ `AdminUser` model vs. DB state mismatch

The `user.py` ORM model (`AdminUser` / table `admin_users`) is still present in the codebase, but **migration `0002` dropped this table**. If the ORM model is accidentally included in a schema diff (e.g., via `alembic revision --autogenerate`), Alembic will try to recreate `admin_users`. The model should either be deleted or excluded from autogenerate.

### ⚠️ IVFFlat index quality

The `ix_document_chunks_embedding_ivfflat` index uses `lists=100`, which is suitable for ~1M vectors. If the initial bulk load has not yet been performed, the index should be dropped and recreated post-load.

### ⚠️ `chat_sessions` references `BaSession` in ORM but `AdminUser` still in migration `0001`

Migration `0001` creates `chat_sessions.user_id` referencing `admin_users.id`. Migration `0002` re-points this FK to `ba_user.id`. Both the ORM model (`session.py`) and migration `0002` reflect the final state correctly.

### ℹ️ camelCase DB columns in `ba_*` tables

Better Auth (running on the Next.js side) expects camelCase column names (`emailVerified`, `createdAt`, etc.). The Python ORM uses `mapped_column(name="camelCase")` to bridge this without affecting Python attribute names.

### ℹ️ `alembic.ini` contains a placeholder DSN

The `sqlalchemy.url` in `alembic.ini` is a placeholder. `env.py` always overrides it at runtime with the value from `DATABASE_URL` env var. **Do not put real credentials in `alembic.ini`.**
