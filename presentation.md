# Awaqi - System Architecture & Technical Deep Dive

## Team Presentation | March 2026

---

## Table of Contents

1. [What is Awaqi?](#1-what-is-awaqi)
2. [Technology Stack](#2-technology-stack)
3. [Monorepo Structure](#3-monorepo-structure)
4. [Directory & File Map](#4-directory--file-map)
5. [Backend Deep Dive (FastAPI)](#5-backend-deep-dive-fastapi)
6. [Frontend Deep Dive (Next.js)](#6-frontend-deep-dive-nextjs)
7. [Shared Packages](#7-shared-packages)
8. [Database Layer](#8-database-layer)
9. [Authentication System](#9-authentication-system)
10. [Document Ingestion Pipeline](#10-document-ingestion-pipeline)
11. [Chat Flow (Current State)](#11-chat-flow-current-state)
12. [Infrastructure & Deployment](#12-infrastructure--deployment)
13. [Data Flow Diagrams](#13-data-flow-diagrams)
14. [Current Status & Known Gaps](#14-current-status--known-gaps)
15. [What's Next](#15-whats-next)

---

## 1. What is Awaqi?

Awaqi is an **AI-powered tax support chatbot** built for the **Ethiopian Revenue Authority (ERA)**. It helps taxpayers and business owners get accurate, cited answers to tax-related questions by using **Retrieval Augmented Generation (RAG)** over official regulatory documents.

**Key capabilities:**
- Bilingual support (Amharic and English)
- PDF document ingestion with AI-powered text extraction
- Vector similarity search over regulatory documents (pgvector)
- Admin dashboard for document management, user management, and system logs
- Guest chat (no login required) and authenticated sessions
- Rate limiting to prevent abuse

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15 (App Router) | Web UI with SSR, i18n, auth |
| **UI Components** | shadcn/ui + Radix UI | Accessible, composable components |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **i18n** | next-intl | Amharic (`am`) and English (`en`) |
| **Frontend Auth** | Better Auth | Session-based auth for admin & customer |
| **Backend** | FastAPI (Python 3.12+) | REST API with async support |
| **Python Pkg Manager** | uv | Fast dependency resolution |
| **LLM** | Google Gemini 2.0 Flash | PDF text extraction |
| **Embeddings** | Gemini embedding-001 | 1024-dim document embeddings |
| **Database** | PostgreSQL 16 + pgvector | Relational + vector storage |
| **Cache / Rate Limit** | Redis 7 | IP-based rate limiting |
| **Containers** | Docker & Docker Compose | Local dev & deployment |
| **Migrations** | Alembic | Async database migrations |
| **ORM** | SQLAlchemy 2.0 (async) | Async ORM with `asyncpg` driver |

---

## 3. Monorepo Structure

```
Awaqi/
├── apps/                          # Standalone applications
│   ├── api/                       # FastAPI backend (Python)
│   ├── web/                       # Next.js frontend (TypeScript)
│   └── telegram-bot/              # Telegram bot (placeholder)
│
├── packages/                      # Shared internal Python libraries
│   ├── ai-engine/                 # Document ingestion pipeline
│   ├── database/                  # ORM models, migrations, Redis
│   ├── nlu/                       # NLU (placeholder)
│   └── utils/                     # Shared utilities (placeholder)
│
├── docker/                        # Docker Compose + Dockerfiles
│
├── .github/workflows/             # CI pipeline
│
├── pyproject.toml                 # uv workspace root config
├── Makefile                       # Build shortcuts
├── .env.example                   # Environment variable template
├── ARCHITECTURE.md                # Architecture documentation
└── AGENTS.md                      # Developer runbook
```

**Why a monorepo?** All apps share the same database models, AI engine, and configuration. A single `uv` workspace manages all Python dependencies, and workspace packages (`packages/*`) are importable across apps without publishing.

---

## 4. Directory & File Map

### 4.1 `apps/api/` — FastAPI Backend

```
apps/api/
├── __init__.py
├── main.py                  # App factory: FastAPI instance, CORS, router mounts
├── deps.py                  # Auth dependencies: get_current_admin, get_current_customer
├── deps_rate_limit.py       # Redis rate-limiting dependency
├── schemas.py               # Pydantic request/response models
└── routers/
    ├── __init__.py
    ├── chat.py              # POST /v1/chat/send, GET /history, POST /feedback
    └── admin.py             # GET /admin/documents, /users, /logs; POST /upload; DELETE /users
```

| File | Responsibility |
|------|---------------|
| `main.py` | Creates the `FastAPI` app, adds CORS middleware (origins from `ALLOWED_ORIGINS` env), mounts chat router at `/v1/chat` and admin router at `/v1`. Exposes `GET /health`. |
| `deps.py` | Extracts Bearer tokens from `Authorization` header or cookies. `get_current_admin` looks up `ba_session` + `ba_user`. `get_current_customer` looks up `cu_session` + `cu_user`. Validates session expiry and active status. |
| `deps_rate_limit.py` | Uses Redis `INCR` + `EXPIRE` to enforce 15 requests per 10 minutes per IP. Respects `X-Forwarded-For` when `TRUST_X_FORWARDED_FOR=true`. Returns HTTP 429 with `Retry-After` header. |
| `schemas.py` | Pydantic v2 models: `ChatRequest`, `ChatResponse`, `Citation`, `ChatMessage`, `FeedbackRequest`, `AdminDocumentList`, `AdminUserList`, `DocumentStatus`, `LogEntryList`. |
| `routers/chat.py` | Guest session management with HMAC tokens. Creates `ChatSession` + `Message` records. Currently returns a **placeholder** response (no RAG). |
| `routers/admin.py` | All admin operations. PDF upload triggers `ingest_pdf()` from `ai-engine`. Superadmin role required for upload and user deletion. Logs endpoint returns last 100 user messages. |

### 4.2 `apps/web/` — Next.js Frontend

```
apps/web/
├── app/
│   ├── [locale]/                  # i18n-aware routing (en, am)
│   │   ├── page.tsx               # Landing page
│   │   ├── layout.tsx             # Root layout with providers
│   │   ├── chat/
│   │   │   ├── page.tsx           # Chat interface
│   │   │   ├── layout.tsx         # Chat layout (sidebar + header)
│   │   │   ├── login/page.tsx     # Customer login
│   │   │   └── signup/page.tsx    # Customer signup
│   │   ├── login/page.tsx         # General login
│   │   ├── signup/page.tsx        # General signup
│   │   ├── (admin)/admin/         # Admin section (route group)
│   │   │   ├── page.tsx           # Admin dashboard
│   │   │   ├── users/page.tsx     # User management
│   │   │   ├── knowledge-base/    # Document management
│   │   │   └── settings/          # Settings + logs
│   │   └── admin/login/page.tsx   # Admin login
│   └── api/
│       ├── auth/[...all]/route.ts          # Better Auth (admin) handler
│       └── customer-auth/[...all]/route.ts # Better Auth (customer) handler
├── components/
│   ├── chat/                      # ChatInterface, MessageBubble, etc.
│   ├── admin/                     # Admin dashboard components
│   ├── landing/                   # Landing page sections
│   └── ui/                        # shadcn/ui primitives (button, card, etc.)
├── lib/
│   ├── auth.ts                    # Admin Better Auth server config
│   ├── customer-auth.ts           # Customer Better Auth server config
│   ├── auth-client.ts             # Admin auth browser client
│   ├── customer-auth-client.ts    # Customer auth browser client
│   ├── auth-secret.ts             # Secret validation utility
│   ├── api.ts                     # Axios client + interceptors (chatApi, adminApi)
│   └── chat-session.ts            # Client-side session management (localStorage)
├── types/
│   └── api.ts                     # TypeScript types matching FastAPI schemas
├── messages/
│   ├── en.json                    # English translations
│   └── am.json                    # Amharic translations
├── i18n/
│   └── request.ts                 # next-intl locale loader
├── middleware.ts                   # i18n routing + admin route protection
└── next.config.ts                 # Next.js configuration
```

| File | Responsibility |
|------|---------------|
| `lib/api.ts` | Central Axios client. Request interceptor attaches the correct Bearer token (admin vs customer). Response interceptor redirects to login on 401. Exports `chatApi` and `adminApi` objects. |
| `lib/auth.ts` | Configures Better Auth for **admin** users: maps to `ba_*` DB tables, adds `role` and `isActive` fields, uses `pg` Pool with `DATABASE_URL_SYNC`. |
| `lib/customer-auth.ts` | Same pattern for **customers**: maps to `cu_*` tables, different cookie prefix (`awaqi-customer`), base path `/api/customer-auth`. |
| `lib/chat-session.ts` | Manages chat sessions client-side: `sessionStorage` for active tab session, `localStorage` for sidebar session list, custom DOM event for cross-component sync. |
| `middleware.ts` | Two jobs: (1) `next-intl` locale routing, (2) admin route guard that checks for the `better-auth.session_token` cookie before allowing access to `/admin/*`. |

### 4.3 `packages/database/` — Data Layer

```
packages/database/
├── src/database/
│   ├── __init__.py          # Re-exports: engine, get_session, get_redis, models
│   ├── base.py              # SQLAlchemy DeclarativeBase
│   ├── db.py                # Async engine, session factory, get_session dependency
│   ├── redis_client.py      # Redis connection pool, rate-limit config
│   └── models/
│       ├── __init__.py      # Imports all models (for Alembic auto-detection)
│       ├── auth.py          # BaUser, BaSession (admin auth)
│       ├── customer.py      # CuUser, CuSession (customer auth)
│       ├── document.py      # Document, DocumentChunk (+ pgvector)
│       └── session.py       # ChatSession, Message, Feedback
├── migrations/
│   ├── env.py               # Async Alembic configuration
│   └── versions/
│       ├── 0001_initial_schema.py       # Core tables + pgvector + indexes
│       ├── 0003_cu_auth_tables.py       # Customer auth tables (cu_*)
│       └── 0004_data_quality_constraints.py  # Dedupe + confidence checks
├── alembic.ini
└── pyproject.toml
```

### 4.4 `packages/ai-engine/` — Document Ingestion

```
packages/ai-engine/
├── src/ai_engine/
│   ├── __init__.py          # Exports ingest_pdf
│   ├── ingest.py            # Orchestrator: extract → chunk → embed → store
│   ├── extractor.py         # PDF → per-page text via Gemini 2.0 Flash OCR
│   ├── chunker.py           # Pages → fixed-size text chunks (1024 tokens, 100 overlap)
│   └── embedder.py          # Chunks → 1024-dim vectors via gemini-embedding-001
└── pyproject.toml
```

### 4.5 `packages/nlu/` & `packages/utils/`

Both are **scaffolded but empty** — `__init__.py` files only. Reserved for:
- `nlu`: Language detection (fastText), intent classification (XLM-RoBERTa)
- `utils`: Shared helpers, constants, text preprocessing

### 4.6 `docker/` — Infrastructure

```
docker/
├── docker-compose.yml       # Full stack: db, redis, api, web, telegram_bot
├── api.Dockerfile           # Python: uv sync → alembic migrate → uvicorn
├── web.Dockerfile           # Node: npm ci → next build (standalone) → node server.js
└── bot.Dockerfile           # Telegram bot (not functional yet)
```

---

## 5. Backend Deep Dive (FastAPI)

### 5.1 Application Bootstrap (`main.py`)

```python
app = FastAPI(title="Awaqi API", version="1.0.0")

# CORS - origins from ALLOWED_ORIGINS env var (comma-separated)
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, ...)

# Mount routers
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api"}
```

### 5.2 API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check |
| `POST` | `/v1/chat/send` | Rate limit | Send message, get response |
| `GET` | `/v1/chat/history/{session_id}` | Rate limit + HMAC | Get conversation history |
| `POST` | `/v1/chat/feedback/{message_id}` | None | Submit thumbs up/down feedback |
| `GET` | `/v1/admin/documents` | Admin Bearer | List uploaded documents |
| `GET` | `/v1/admin/users` | Admin Bearer | List admin users |
| `DELETE` | `/v1/admin/users/{user_id}` | Superadmin Bearer | Delete an admin user |
| `POST` | `/v1/admin/upload` | Superadmin Bearer | Upload & ingest a PDF |
| `GET` | `/v1/admin/logs` | Admin Bearer | Last 100 user messages |

### 5.3 Dependency Injection Chain

```
Request
  │
  ├─ require_rate_limit
  │   └─ get_redis() → Redis INCR on "rate:{ip}" → 429 if exceeded
  │
  ├─ get_current_admin
  │   └─ _extract_bearer_or_cookie_token()
  │       └─ SELECT ba_session JOIN ba_user WHERE token = ? AND expires_at > now()
  │
  ├─ get_current_customer
  │   └─ _extract_bearer_or_cookie_token()
  │       └─ SELECT cu_session JOIN cu_user WHERE token = ?
  │
  └─ get_session()
      └─ AsyncSession (commit on success, rollback on error)
```

### 5.4 Guest Session Security

The chat system uses **HMAC-based session tokens** for guest users:

1. Client generates a UUID for the session
2. First message creates a `ChatSession` row in the DB
3. API returns `session_token = HMAC-SHA256(SESSION_TOKEN_SECRET, session_id)`
4. Subsequent requests must include `X-Session-Token` header
5. API validates the HMAC before allowing access to existing sessions

---

## 6. Frontend Deep Dive (Next.js)

### 6.1 Routing Architecture

The frontend uses Next.js App Router with locale-based routing:

```
/[locale]/                    → Landing page
/[locale]/chat                → Chat interface (main product)
/[locale]/chat/login          → Customer login
/[locale]/chat/signup         → Customer registration
/[locale]/login               → General login
/[locale]/admin/login         → Admin login
/[locale]/admin               → Admin dashboard
/[locale]/admin/users         → User management
/[locale]/admin/knowledge-base → Document management
/[locale]/admin/settings      → Settings
/[locale]/admin/settings/logs → System logs
```

### 6.2 Client-Server Communication (`lib/api.ts`)

```
┌──────────────────────────────────────────────────────────┐
│                    Axios Client                           │
│                                                          │
│  Request Interceptor:                                    │
│  ┌───────────────────────────────────────────┐           │
│  │ URL starts with /v1/admin ?               │           │
│  │   YES → attach admin session Bearer token │           │
│  │   NO  → attach customer session Bearer    │           │
│  └───────────────────────────────────────────┘           │
│                                                          │
│  Response Interceptor:                                   │
│  ┌───────────────────────────────────────────┐           │
│  │ Got 401?                                  │           │
│  │   Admin API → redirect to /admin/login    │           │
│  │   Other     → redirect to /login          │           │
│  └───────────────────────────────────────────┘           │
│                                                          │
│  Exports:                                                │
│  ├─ chatApi.send(payload)                                │
│  ├─ chatApi.getHistory(sessionId)                        │
│  ├─ chatApi.submitFeedback(messageId, payload)           │
│  ├─ adminApi.uploadDocument(file)                        │
│  ├─ adminApi.listDocuments(limit)                        │
│  ├─ adminApi.listUsers()                                 │
│  ├─ adminApi.deleteUser(userId)                          │
│  └─ adminApi.getLogs()                                   │
└──────────────────────────────────────────────────────────┘
```

### 6.3 Chat Session Management

Sessions are tracked in two layers for a responsive experience:

| Storage | Key | Data | Lifetime |
|---------|-----|------|----------|
| `sessionStorage` | `awaqi_active_session` | Active session UUID (current tab) | Tab close |
| `localStorage` | `awaqi_sessions` | Array of `{id, title, createdAt}` for sidebar | Permanent |
| PostgreSQL | `chat_sessions` + `messages` | Full conversation data | Permanent |

**New Chat Flow:**
1. User clicks **+ New Chat** → `createNewSession()` generates UUID
2. Sidebar navigates to `/chat?session=<uuid>`
3. `ChatInterface` reads the query param, clears messages
4. First user message → `updateSessionTitle(id, content)` saves to `localStorage`
5. Custom DOM event `awaqi-sessions-updated` → sidebar re-renders

**Resume Flow:**
1. User clicks session in sidebar → navigates to `/chat?session=<uuid>`
2. `ChatInterface` calls `GET /v1/chat/history/<uuid>`
3. Messages loaded from server, displayed in UI

### 6.4 Internationalization

- **Supported locales:** English (`en`), Amharic (`am`)
- **Library:** `next-intl`
- **Translation files:** `messages/en.json`, `messages/am.json`
- **Middleware:** Auto-detects locale from URL path (`/en/...` or `/am/...`)

---

## 7. Shared Packages

### How Packages Connect

```
┌─────────────────────────────────────────────────────┐
│                  apps/api (FastAPI)                  │
│                                                     │
│  imports: database, ai_engine                       │
│  ├─ routers/chat.py   → database (sessions, msgs)  │
│  ├─ routers/admin.py  → database + ai_engine        │
│  ├─ deps.py           → database (auth tables)      │
│  └─ deps_rate_limit   → database (redis_client)     │
└─────────────────────────────────────────────────────┘
          │                        │
          ▼                        ▼
┌─────────────────┐    ┌──────────────────────┐
│ packages/database│    │ packages/ai-engine    │
│                 │    │                      │
│ SQLAlchemy ORM  │◄───│ ingest.py imports    │
│ Alembic         │    │ DocumentChunk model  │
│ Redis client    │    │                      │
│ All models      │    │ extractor.py         │
└─────────────────┘    │ chunker.py           │
                       │ embedder.py          │
                       └──────────────────────┘
```

**Resolution:** Running `uv run` from the repo root adds all workspace packages to `PYTHONPATH`, so `from database import get_session` and `from ai_engine import ingest_pdf` work without installation.

---

## 8. Database Layer

### 8.1 Entity-Relationship Overview

```
┌──────────────────────────────┐
│         ba_user              │
│  (Admin users)               │
│──────────────────────────────│
│  id (UUID PK)                │
│  name, email                 │
│  role (superadmin/editor)    │
│  is_active (boolean)         │
│  created_at, updated_at      │
└──────┬───────────────────────┘
       │ 1:N
       ▼
┌──────────────────────────────┐       ┌──────────────────────────────┐
│       ba_session             │       │         cu_user              │
│  (Admin sessions)            │       │  (Customer users)            │
│──────────────────────────────│       │──────────────────────────────│
│  id, token, expires_at       │       │  id, name, email             │
│  user_id → ba_user           │       │  created_at, updated_at      │
└──────────────────────────────┘       └──────┬───────────────────────┘
                                              │ 1:N
                                              ▼
                                       ┌──────────────────────────────┐
                                       │       cu_session             │
                                       │  (Customer sessions)         │
                                       └──────────────────────────────┘

┌──────────────────────────────┐
│       chat_sessions          │
│──────────────────────────────│
│  id (UUID PK)                │
│  channel (web/telegram)      │
│  user_id → ba_user (nullable)│
│  language (am/en)            │
│  created_at, updated_at      │
└──────┬───────────────────────┘
       │ 1:N
       ▼
┌──────────────────────────────┐
│         messages             │
│──────────────────────────────│
│  id (UUID PK)                │
│  session_id → chat_sessions  │
│  role (user/assistant)       │
│  content (text)              │
│  cited_chunks (JSONB)        │
│  confidence_score (0.0-1.0)  │
│  created_at                  │
└──────┬───────────────────────┘
       │ 1:1
       ▼
┌──────────────────────────────┐
│         feedback             │
│──────────────────────────────│
│  id (UUID PK)                │
│  message_id → messages (UQ)  │
│  rating (thumbs_up/down)     │
│  comment (max 1024 chars)    │
│  created_at                  │
└──────────────────────────────┘

┌──────────────────────────────┐
│         documents            │
│──────────────────────────────│
│  id (UUID PK)                │
│  title, source_url           │
│  file_hash (SHA-256, unique) │
│  language, status            │
│  created_at, updated_at      │
└──────┬───────────────────────┘
       │ 1:N
       ▼
┌──────────────────────────────┐
│     document_chunks          │
│──────────────────────────────│
│  id (UUID PK)                │
│  document_id → documents     │
│  chunk_index (int)           │
│  content (text)              │
│  embedding (Vector 1024-dim) │
│  chunk_metadata (JSONB)      │
│  created_at                  │
│                              │
│  INDEXES:                    │
│  ├─ IVFFlat on embedding     │
│  ├─ GIN trigram on content   │
│  └─ UNIQUE (doc_id, idx)     │
└──────────────────────────────┘
```

### 8.2 Database Connection

```python
# packages/database/src/database/db.py

engine = create_async_engine(
    DATABASE_URL,                  # postgresql+asyncpg://...
    pool_pre_ping=True,            # Auto-reconnect on DB restart
    pool_size=10,                  # Base pool connections
    max_overflow=20,               # Extra connections under load
)

async def get_session():           # FastAPI Depends() target
    async with AsyncSessionLocal() as session:
        yield session              # Auto-commit on success
                                   # Auto-rollback on exception
```

### 8.3 Alembic Migration Chain

```
0001_initial_schema
    │  Creates: pgvector extension, pg_trgm extension
    │  Tables:  documents, document_chunks, ba_user, ba_session,
    │           ba_account, ba_verification, chat_sessions, messages, feedback
    │  Indexes: IVFFlat on embeddings, GIN trigram on content
    │
    ▼
0003_cu_auth_tables
    │  Creates: cu_user, cu_session, cu_account, cu_verification
    │
    ▼
0004_data_quality_constraints
       Adds: chunk dedup constraint, confidence_score range check [0,1],
             unique (document_id, chunk_index) constraint
```

---

## 9. Authentication System

### 9.1 Dual Auth Architecture

Awaqi has **two separate auth systems** running on the same database:

```
┌──────────────────────────────────────────────────────────────┐
│                     Better Auth (Next.js)                     │
│                                                              │
│  ┌────────────────────┐    ┌─────────────────────────────┐   │
│  │   Admin Auth        │    │   Customer Auth              │   │
│  │   /api/auth/[...all]│    │   /api/customer-auth/[...all]│   │
│  │                    │    │                             │   │
│  │   Tables: ba_*      │    │   Tables: cu_*               │   │
│  │   Cookie:           │    │   Cookie:                   │   │
│  │   better-auth.*     │    │   awaqi-customer.*          │   │
│  │                    │    │                             │   │
│  │   Roles:            │    │   No roles (just users)     │   │
│  │   superadmin/editor │    │                             │   │
│  └────────────────────┘    └─────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                         │
              session tokens stored in cookies
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Validation                        │
│                                                              │
│   deps.py reads token from Authorization header or cookies   │
│   Joins ba_session → ba_user (for admin)                     │
│   Joins cu_session → cu_user (for customer)                  │
│   Checks: token exists, not expired, user is_active          │
│   No JWT. No shared secret. Pure database lookup.            │
└──────────────────────────────────────────────────────────────┘
```

### 9.2 Auth Flow Step-by-Step

**Admin Login:**
1. Admin visits `/admin/login`, enters email + password
2. Better Auth validates credentials, creates `ba_session` row with a random token
3. Session token set as HTTP-only cookie (`better-auth.session_token`)
4. Frontend Axios interceptor reads token via `authClient.getSession()`
5. Attaches it as `Authorization: Bearer <token>` on admin API requests
6. FastAPI `get_current_admin` dependency JOINs `ba_session` + `ba_user` to validate

**Guest Chat (no login):**
1. User visits `/chat`, frontend generates a UUID session ID
2. First `POST /v1/chat/send` creates a `ChatSession` row
3. API returns HMAC-based `session_token` in the response
4. Subsequent requests should include `X-Session-Token` header

### 9.3 Access Control Matrix

| Role | Chat | Chat History | Feedback | View Docs | Upload Docs | Manage Users | View Logs |
|------|------|-------------|----------|-----------|-------------|-------------|-----------|
| **Guest** | Yes | Own session | Yes | No | No | No | No |
| **Customer** | Yes | Own sessions | Yes | No | No | No | No |
| **Admin (editor)** | Yes | All | Yes | Yes | No | No | Yes |
| **Admin (superadmin)** | Yes | All | Yes | Yes | Yes | Yes | Yes |

---

## 10. Document Ingestion Pipeline

This is the **only AI pipeline currently implemented**. It processes uploaded PDFs into searchable vector embeddings.

### 10.1 Pipeline Stages

```
PDF Upload (admin)
      │
      ▼
┌─────────────────────────────────────────┐
│  Stage 1: EXTRACTION (extractor.py)      │
│                                         │
│  Input:  Raw PDF bytes                  │
│  Process: Split PDF per page            │
│           Send each page to             │
│           Gemini 2.0 Flash for OCR      │
│  Output: List[PageText] with page text  │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Stage 2: CHUNKING (chunker.py)          │
│                                         │
│  Input:  List of page texts             │
│  Process: Split into fixed-size chunks  │
│           1024 tokens with 100 overlap  │
│  Output: List[Chunk] with metadata      │
│          (page numbers, char ranges)    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Stage 3: EMBEDDING (embedder.py)        │
│                                         │
│  Input:  List of chunk texts            │
│  Process: Send to gemini-embedding-001  │
│           Get 1024-dimensional vectors  │
│           L2-normalize each vector      │
│  Output: List[List[float]] embeddings   │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Stage 4: STORAGE (ingest.py)            │
│                                         │
│  Input:  Chunks + embeddings            │
│  Process: Create DocumentChunk rows     │
│           Store in PostgreSQL + pgvector │
│  Output: Number of chunks stored        │
│                                         │
│  DB Indexes:                            │
│  ├─ IVFFlat for vector similarity       │
│  └─ GIN trigram for text search         │
└─────────────────────────────────────────┘
```

### 10.2 Safeguards

- **Deduplication:** SHA-256 hash of file bytes; duplicate uploads return existing doc
- **Size limit:** Configurable `MAX_UPLOAD_BYTES` (default 10MB)
- **MIME validation:** Only `application/pdf` accepted
- **Status tracking:** Document marked as `PENDING` → `INDEXED` or `FAILED`
- **Unique constraint:** `(document_id, chunk_index)` prevents duplicate chunks

---

## 11. Chat Flow (Current State)

### What Actually Happens Today

```
User types message
      │
      ▼
Frontend: chatApi.send({ message, session_id, language })
      │
      ▼
POST /v1/chat/send
      │
      ├─ Rate limit check (Redis: 15 req / 10 min per IP)
      │
      ├─ Get or create ChatSession (UUID-based)
      │
      ├─ Persist user Message to PostgreSQL
      │
      ├─ Generate response:
      │   ⚠️ PLACEHOLDER: "This is a placeholder response..."
      │   confidence_score = 0.0
      │   citations = []
      │
      ├─ Persist assistant Message to PostgreSQL
      │
      └─ Return ChatResponse with session_token (HMAC)
```

### What Will Happen (Planned)

```
User types message
      │
      ▼
POST /v1/chat/send
      │
      ├─ NLU: Detect language (fastText), classify intent (XLM-RoBERTa)
      │
      ├─ AI Engine RAG Pipeline:
      │   ├─ BM25 sparse retrieval (keyword matching)
      │   ├─ Dense vector search (pgvector cosine similarity)
      │   ├─ Reciprocal Rank Fusion (RRF) to merge results
      │   └─ Gemini 2.5 Flash generates answer with citations
      │
      ├─ Confidence scoring
      │   └─ Low confidence → "Please contact an ERA officer"
      │
      └─ Return response with citations and confidence score
```

---

## 12. Infrastructure & Deployment

### 12.1 Docker Compose Services

```
┌────────────────────────────────────────────────────────────┐
│                    Docker Compose                          │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │    db     │  │  redis   │  │   api    │  │   web    │  │
│  │          │  │          │  │          │  │          │  │
│  │ pgvector │  │ redis:7  │  │ FastAPI  │  │ Next.js  │  │
│  │ pg16     │  │ alpine   │  │ uvicorn  │  │standalone│  │
│  │          │  │          │  │          │  │          │  │
│  │ :5432    │  │ :6379    │  │ :8000    │  │ :3000    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│       ▲              ▲            │  │          │          │
│       │              │            │  │          │          │
│       └──────────────┴────────────┘  │          │          │
│           api depends on db+redis    │          │          │
│                                      │          │          │
│              web depends on api ─────┘──────────┘          │
└────────────────────────────────────────────────────────────┘
```

### 12.2 Local Development Setup

```bash
# 1. Start infrastructure
sudo docker compose -f docker/docker-compose.yml up -d db redis

# 2. Run database migrations
cd packages/database && uv run alembic upgrade head && cd ../..

# 3. Start backend (from repo root)
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Start frontend (separate terminal)
export BETTER_AUTH_SECRET="$(openssl rand -base64 32)"
export DATABASE_URL_SYNC="postgresql://user:password@localhost:5432/awaqi_db"
export NEXT_PUBLIC_APP_URL="http://localhost:3000"
export NEXT_PUBLIC_API_URL="http://localhost:8000"
cd apps/web && npm run dev
```

### 12.3 Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | Backend, Alembic | Async PostgreSQL connection (`postgresql+asyncpg://`) |
| `DATABASE_URL_SYNC` | Frontend | Better Auth DB connection (`postgresql://`) |
| `REDIS_URL` | Backend | Rate limiting and session cache |
| `GOOGLE_API_KEY` | ai-engine | Gemini API for extraction & embeddings |
| `BETTER_AUTH_SECRET` | Frontend | Signs auth cookies |
| `NEXT_PUBLIC_APP_URL` | Frontend | Base URL for auth callbacks |
| `NEXT_PUBLIC_API_URL` | Frontend | FastAPI backend URL |
| `ALLOWED_ORIGINS` | Backend | CORS allowed origins |
| `SESSION_TOKEN_SECRET` | Backend | HMAC key for guest session tokens |
| `MAX_UPLOAD_BYTES` | Backend | Max PDF upload size (default 10MB) |
| `TRUST_X_FORWARDED_FOR` | Backend | Trust proxy headers for rate limiting |

---

## 13. Data Flow Diagrams

### 13.1 Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER                                       │
│                                                                     │
│     Web Browser (/en/chat)           Admin Panel (/en/admin)        │
│     ┌───────────────────┐           ┌───────────────────┐           │
│     │  Chat Interface   │           │  Admin Dashboard  │           │
│     │  ├─ Send message  │           │  ├─ Upload PDF    │           │
│     │  ├─ View history  │           │  ├─ View docs     │           │
│     │  └─ Give feedback │           │  ├─ Manage users  │           │
│     └────────┬──────────┘           │  └─ View logs     │           │
│              │                      └────────┬──────────┘           │
└──────────────┼──────────────────────────────┼───────────────────────┘
               │ HTTP (Axios)                  │ HTTP (Axios + Bearer)
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Next.js (apps/web)                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ lib/api.ts   │  │ lib/auth.ts      │  │ lib/customer-auth.ts  │  │
│  │ Axios client │  │ Admin Better Auth│  │ Customer Better Auth  │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────────┬───────────┘  │
│         │                   │                         │              │
│         │ HTTP              │ SQL (pg Pool)            │ SQL          │
└─────────┼───────────────────┼─────────────────────────┼──────────────┘
          │                   │                         │
          ▼                   ▼                         ▼
┌─────────────────┐  ┌──────────────────────────────────────────────┐
│ FastAPI (api)   │  │           PostgreSQL 16 + pgvector           │
│                 │  │                                              │
│ /v1/chat/*      │──│  ba_user, ba_session   (admin auth)         │
│ /v1/admin/*     │  │  cu_user, cu_session   (customer auth)      │
│ /health         │  │  chat_sessions, messages, feedback          │
│                 │  │  documents, document_chunks (+ embeddings)  │
└────────┬────────┘  └──────────────────────────────────────────────┘
         │                              ▲
         │                              │
    ┌────┴────┐                    ┌────┴────┐
    │  Redis  │                    │ai-engine│
    │ :6379   │                    │(ingest) │
    │         │                    │         │
    │rate:*   │                    │Gemini   │
    └─────────┘                    └─────────┘
```

### 13.2 Request Lifecycle (Chat Message)

```
1. User types "How do I file taxes?"
2. ChatInterface calls chatApi.send({ message: "...", session_id: "uuid", language: "en" })
3. Axios interceptor checks URL → not /v1/admin → attaches customer token (if logged in)
4. POST /v1/chat/send hits FastAPI
5. require_rate_limit: Redis INCR "rate:192.168.1.1" → count < 15 → proceed
6. _get_or_create_session: SELECT chat_sessions WHERE id = uuid → not found → INSERT
7. Persist user Message: INSERT INTO messages (session_id, role='user', content='...')
8. Generate response: ⚠️ PLACEHOLDER (returns stub text)
9. Persist assistant Message: INSERT INTO messages (session_id, role='assistant', ...)
10. Return JSON: { response_text, citations: [], confidence_score: 0.0, session_token }
11. ChatInterface displays the response in a message bubble
```

---

## 14. Current Status & Known Gaps

### What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| FastAPI backend with CORS | Working | All endpoints functional |
| Chat session creation & history | Working | UUID-based with HMAC security |
| Message persistence | Working | User + assistant messages stored |
| Feedback collection | Working | Thumbs up/down with comments |
| Admin authentication | Working | Better Auth with role-based access |
| Customer authentication | Working | Separate Better Auth instance |
| PDF upload & ingestion | Working | Gemini Flash extraction + embedding |
| Rate limiting | Working | Redis-based, 15 req/10 min |
| Admin dashboard | Working | Documents, users, logs views |
| i18n (en/am) | Working | Full translation support |
| Database migrations | Working | 3 Alembic revisions applied |
| Docker Compose setup | Working | DB + Redis containers |

### Known Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| **No RAG pipeline in chat** | Chat returns placeholder responses | **Critical** |
| **NLU package is empty** | No language detection or intent classification | High |
| **Utils package is empty** | No shared utilities | Low |
| **Guest session token not sent by frontend** | Second+ messages to same session may fail | High |
| **Telegram bot not implemented** | Only `pyproject.toml` scaffold exists | Medium |
| **No automated tests** | Zero test coverage | High |
| **No ESLint config** | `npm run lint` triggers interactive setup | Low |
| **CI only builds frontend** | No backend CI pipeline | Medium |

---

## 15. What's Next

### Phase 1: Wire RAG into Chat (Critical Path)

1. Implement vector retrieval in `ai-engine` (cosine similarity search over `document_chunks`)
2. Add BM25 sparse retrieval for keyword matching
3. Implement Reciprocal Rank Fusion (RRF) to merge retrieval results
4. Connect Gemini 2.5 Flash for answer generation with retrieved context
5. Replace the placeholder in `chat.py` with the real pipeline
6. Calculate and return meaningful confidence scores

### Phase 2: NLU Integration

1. Add fastText language detection to `packages/nlu`
2. Add XLM-RoBERTa intent classification
3. Route intents to appropriate handlers (FAQ, document lookup, human handoff)

### Phase 3: Production Readiness

1. Fix guest session token propagation in the frontend
2. Add comprehensive test suites (pytest for backend, Jest/Playwright for frontend)
3. Set up ESLint for the frontend
4. Expand CI to include backend linting, type-checking, and tests
5. Add logging and monitoring (structured logs, health metrics)

### Phase 4: Feature Expansion

1. Implement Telegram bot (`apps/telegram-bot`)
2. Add multi-turn conversation context (pass prior messages to LLM)
3. Add confidence-based fallback ("Contact an ERA officer")
4. Implement document scraping from mor.gov.et
5. Customer session tracking (link chat sessions to logged-in customers)

---

*Document generated: March 2026 | Awaqi v1.0.0*
