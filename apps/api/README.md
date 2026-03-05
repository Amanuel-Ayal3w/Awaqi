# Awaqi API

FastAPI backend for the Awaqi regulatory-assistant platform. Provides chat, document management, admin, and scraper endpoints.

## Architecture

```
apps/api/
├── main.py          # FastAPI app, CORS, router mounts
├── deps.py          # Auth dependencies (get_current_admin, get_current_customer)
├── schemas.py       # Pydantic request/response models
└── routers/
    ├── chat.py      # /v1/chat/* — send messages, history, feedback
    └── admin.py     # /v1/admin/* — users, uploads, logs, scraper (protected)
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL + Redis running (see below)

## Setup & Run

### 1. Start infrastructure

From the repo root:

```bash
docker compose -f docker/docker-compose.yml up -d db redis
```

This gives you PostgreSQL (`awaqi_db`) on `:5432` and Redis on `:6379`.

### 2. Install dependencies

```bash
# From repo root — installs all workspace packages
uv sync
```

### 3. Run migrations

```bash
cd packages/database
uv run alembic upgrade head
```

### 4. Start the server

**From the repo root** (not from `apps/api/`):

```bash
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

The module path is `apps.api.main:app` because `uv` resolves imports from the workspace root.

The API will be available at `http://localhost:8000`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/awaqi_db` | Async PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated CORS origins |

## Endpoints

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Returns `{"status": "ok", "service": "api"}` |

### Chat (`/v1/chat`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/v1/chat/send` | None | Send a message and get an AI response |
| `GET` | `/v1/chat/history/{session_id}` | None | Retrieve message history for a session |
| `POST` | `/v1/chat/feedback/{message_id}` | None | Submit thumbs-up/down feedback on a message |

### Admin (`/v1/admin`) — all routes require a valid session token

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/v1/admin/users` | Admin | List all admin users |
| `DELETE` | `/v1/admin/users/{user_id}` | Admin | Delete an admin user |
| `POST` | `/v1/admin/upload` | Admin | Upload a document (PDF) for ingestion |
| `GET` | `/v1/admin/logs` | Admin | Fetch recent user query logs |
| `POST` | `/v1/admin/scrape` | Admin | Trigger a scraper job |

## Authentication

Admin endpoints are protected by the `get_current_admin` dependency in `deps.py`. It validates a Better Auth session token by querying `ba_session` + `ba_user` in PostgreSQL — no JWT or shared secret needed.

The token can be provided as:
- `Authorization: Bearer <token>` header
- `better-auth.session_token` cookie (set automatically by the Next.js frontend)

### Request/Response Schemas

Defined in `schemas.py`:

| Schema | Used by |
|---|---|
| `ChatRequest` | `POST /v1/chat/send` — `{message, session_id, language?}` |
| `ChatResponse` | Response — `{response_text, citations[], confidence_score}` |
| `ChatMessage` | `GET /v1/chat/history/*` — `{role, content, timestamp}` |
| `FeedbackRequest` | `POST /v1/chat/feedback/*` — `{score, comment?}` |
| `DocumentStatus` | `POST /v1/admin/upload` — `{doc_id, status}` |
| `LogEntryList` | `GET /v1/admin/logs` — `{logs: [{timestamp, level, message}]}` |
| `ScraperStatus` | `POST /v1/admin/scrape` — `{job_id, status}` |
| `AdminUserList` | `GET /v1/admin/users` — `{users: [{id, name, email, role, is_active, created_at}]}` |

## Interactive Docs

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
